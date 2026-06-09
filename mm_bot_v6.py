import asyncio
import pathlib
import time
import httpx
from decimal import Decimal
from collections import deque

from elfa_grvt_bot.grvt_client import GrvtClient

# ── FIXME: 設定 ───────────────────────────────────────────────
SYMBOL           = "BTC_USDT_Perp"
ORDER_SIZE       = Decimal("0.01")   # FIXME: 注文サイズ BTC
MAX_INV          = Decimal("0.03")   # FIXME: 在庫上限 BTC
STOP_LOSS_PCT    = Decimal("0.0025") # FIXME: 0.25% で強制クローズ
DAILY_LOSS_LIMIT = Decimal("-50")    # FIXME: 日次損失上限 USDT
REFRESH_SEC      = 3
RISK_ADJUST_SEC  = 30
ATR_WINDOW       = 10
MAKER_REBATE     = Decimal("0.00001")
TAKER_FEE        = Decimal("0.00037")

MARKET_URL = "https://market-data.grvt.io/full/v1/mini"
ACCT_URL   = "https://trades.grvt.io/full/v1/account_summary"
CANCEL_URL = "https://trades.grvt.io/full/v1/cancel_all_orders"
ORDER_URL  = "https://trades.grvt.io/full/v1/create_order"
# ─────────────────────────────────────────────────────────────

env = {k.strip(): v.strip()
       for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines()
       if "=" in line and not line.startswith("#")
       for k, v in [line.split("=", 1)]}

# ── ランタイム状態 ────────────────────────────────────────────
position      = Decimal("0")
entry_price   = Decimal("0")
daily_pnl     = Decimal("0")
total_volume  = Decimal("0")
risk_mult     = Decimal("1.0")
last_risk_adj = time.time()
price_history = deque(maxlen=ATR_WINDOW + 1)
bid_fills     = 0
ask_fills     = 0
market_closes = 0
start_balance = Decimal("0")
# ─────────────────────────────────────────────────────────────


async def get_mid_price(grvt: GrvtClient) -> Decimal:
    """Get mid price from GRVT market data."""
    try:
        r = await grvt.client.post(
            MARKET_URL,
            json={"instrument": {"instrument_type": "PERP",
                                 "base": "BTC", "quote": "USDT"}},
            cookies={"gravity": grvt.cookie},
        )
        if r.status_code == 200:
            d = r.json().get("result", {})
            best_bid = Decimal(str(d.get("best_bid_price", "0")))
            best_ask = Decimal(str(d.get("best_ask_price", "0")))
            if best_bid > 0 and best_ask > 0:
                return (best_bid + best_ask) / 2
    except Exception as e:
        print(f"  [mid_price error] {e}")
    return Decimal("0")


async def get_account_data(grvt: GrvtClient) -> dict:
    """Get account balance and positions."""
    try:
        r = await grvt.client.post(
            ACCT_URL,
            json={"sub_account_id": str(grvt.account_id)},
            cookies={"gravity": grvt.cookie},
        )
        if r.status_code == 200:
            return r.json().get("result", {})
    except Exception as e:
        print(f"  [account error] {e}")
    return {}


async def cancel_all(grvt: GrvtClient):
    """Cancel all open orders."""
    try:
        await grvt.client.post(
            CANCEL_URL,
            json={"sub_account_id": str(grvt.account_id)},
            cookies={"gravity": grvt.cookie},
        )
    except Exception:
        pass


async def place_limit(grvt: GrvtClient, is_buying: bool,
                      price: Decimal, size: Decimal) -> bool:
    """Place post-only limit order."""
    try:
        result = await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buying,
            amount=size, is_market=False,
            limit_price=price,
            time_in_force="GTT",
            post_only=True,
        )
        return result is not None
    except Exception as e:
        print(f"  [limit error] {'BUY' if is_buying else 'SELL'}"
              f" @{price}: {e}")
        return False


async def place_market_close(grvt: GrvtClient,
                              is_buying: bool, size: Decimal,
                              mid: Decimal = Decimal("0")):
    """Place market order to close position.
    limit_price is required by _place_single_order even for market orders.
    Use mid price with 2% slippage buffer as limit_price.
    """
    try:
        # 2% slippage buffer to ensure fill
        if mid == Decimal("0"):
            mid = Decimal("99999") if is_buying else Decimal("1")
        slippage = Decimal("1.02") if is_buying else Decimal("0.98")
        lp = (mid * slippage).quantize(Decimal("0.1"))
        await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buying,
            amount=size, is_market=True,
            limit_price=lp,
            time_in_force="IOC",
            reduce_only=True,
        )
    except Exception as e:
        print(f"  [market close error] {e}")


def calc_spread(prices: deque) -> Decimal:
    """
    Dynamic spread in USD.
    spread = max(ATR * 0.35, 2.0)
    """
    if len(prices) < 2:
        return Decimal("2.0")
    ranges = [abs(prices[i] - prices[i-1])
              for i in range(1, len(prices))]
    atr = Decimal(str(sum(ranges) / len(ranges)))
    return max(atr * Decimal("0.35"), Decimal("2.0"))


def adjust_risk(pnl: Decimal) -> None:
    """
    Auto-adjust risk_mult every RISK_ADJUST_SEC.
    PnL > 0  -> risk_mult -= 0.05 (floor 0.8)
    PnL < 0  -> risk_mult += 0.10 (ceil  2.0)
    PnL == 0 -> no change (waiting for first fill)
    """
    global risk_mult
    if pnl > 0:
        risk_mult = max(Decimal("0.8"),
                        risk_mult - Decimal("0.05"))
    elif pnl < 0:
        risk_mult = min(Decimal("2.0"),
                        risk_mult + Decimal("0.1"))
    # pnl == 0: no adjustment yet


async def market_close_all(grvt: GrvtClient, reason: str = "",
                            mid: Decimal = Decimal("0")):
    """Flatten entire position with market order."""
    global position, daily_pnl, market_closes, entry_price
    if abs(position) < Decimal("0.001"):
        return
    is_buy = position < 0
    size   = abs(position)
    fee    = size * entry_price * TAKER_FEE
    daily_pnl     -= fee
    market_closes  += 1
    await cancel_all(grvt)
    await place_market_close(grvt, is_buy, size, mid)
    print(f"  🛑 CLOSE [{reason}]"
          f" size={float(size):.3f} fee=-${float(fee):.4f}")
    position    = Decimal("0")
    entry_price = Decimal("0")


async def on_fill(side: str, price: Decimal, size: Decimal,
                  is_maker: bool):
    """Update state on fill."""
    global position, entry_price, daily_pnl
    global total_volume, bid_fills, ask_fills

    notional      = price * size
    total_volume += notional

    if is_maker:
        daily_pnl += notional * MAKER_REBATE
    else:
        daily_pnl -= notional * TAKER_FEE

    if side == "BID":
        bid_fills += 1
        if position >= 0:
            total_cost  = entry_price * position + price * size
            position   += size
            entry_price = (total_cost / position
                           if position else Decimal("0"))
        else:
            position += size
            if position >= 0:
                entry_price = price
    else:
        ask_fills += 1
        if position <= 0:
            total_cost  = entry_price * abs(position) + price * size
            position   -= size
            entry_price = (total_cost / abs(position)
                           if position else Decimal("0"))
        else:
            position -= size
            if position <= 0:
                entry_price = price


async def place_quotes(grvt: GrvtClient,
                       mid: Decimal, spread: Decimal):
    """Place symmetric BID/ASK around mid."""
    half   = (spread / 2).quantize(Decimal("0.1"))
    my_bid = (mid - half).quantize(Decimal("0.1"))
    my_ask = (mid + half).quantize(Decimal("0.1"))
    size   = (ORDER_SIZE * risk_mult).quantize(Decimal("0.001"))

    await cancel_all(grvt)

    b_icon = "🚫"
    a_icon = "🚫"

    if position < MAX_INV:
        ok     = await place_limit(grvt, True, my_bid, size)
        b_icon = "✅" if ok else "❌"

    if position > -MAX_INV:
        ok     = await place_limit(grvt, False, my_ask, size)
        a_icon = "✅" if ok else "❌"

    return my_bid, my_ask, b_icon, a_icon


async def on_market_tick(grvt: GrvtClient, mid: Decimal) -> str:
    """Main loop handler."""
    global last_risk_adj

    # 1. Price history / spread
    price_history.append(mid)
    spread = calc_spread(price_history) * risk_mult

    # 2. Daily loss limit
    if daily_pnl < DAILY_LOSS_LIMIT:
        print(f"\n🛑 日次損失上限到達: ${float(daily_pnl):.2f}")
        await market_close_all(grvt, "DAILY_LIMIT", mid)
        return "STOP"

    # 3. Stop-loss
    if abs(position) >= Decimal("0.001") and entry_price > 0:
        unreal    = (mid - entry_price) * position
        threshold = -STOP_LOSS_PCT * entry_price * abs(position)
        if unreal < threshold:
            print(f"  ⚠️ SL発動: unreal=${float(unreal):.2f}"
                  f" / limit=${float(threshold):.2f}")
            await market_close_all(grvt, "STOP_LOSS", mid)

    # 4. Inventory limit
    if abs(position) >= MAX_INV:
        await market_close_all(grvt, "MAX_INV", mid)

    # 5. Risk adjustment
    if time.time() - last_risk_adj >= RISK_ADJUST_SEC:
        adjust_risk(daily_pnl)
        last_risk_adj = time.time()

    # 6. Place quotes
    my_bid, my_ask, b_icon, a_icon = \
        await place_quotes(grvt, mid, spread)

    # 7. Unrealized PnL
    unreal_str = ""
    if abs(position) >= Decimal("0.001") and entry_price > 0:
        unreal     = (mid - entry_price) * position
        unreal_str = f" UPnL:${float(unreal):+.2f}"

    # 8. Log
    print(f"[{time.strftime('%H:%M:%S')}] "
          f"mid=${float(mid):,.1f} "
          f"sprd=${float(spread):.1f} "
          f"BID:{b_icon}${float(my_bid):,.1f} "
          f"ASK:{a_icon}${float(my_ask):,.1f} "
          f"Pos:{float(position):+.3f} "
          f"日次:${float(daily_pnl):+.3f}{unreal_str} "
          f"Vol:${float(total_volume):,.0f} "
          f"RM:{float(risk_mult):.2f} "
          f"F:{bid_fills+ask_fills}"
          f"(B{bid_fills}/A{ask_fills}/M{market_closes})")

    return "OK"


async def main():
    global start_balance

    grvt = GrvtClient(
        api_key=env["GRVT_TRADING_API_KEY"],
        private_key=env["GRVT_TRADING_PRIVATE_KEY"],
    )
    await grvt.login()

    data          = await get_account_data(grvt)
    start_balance = Decimal(str(data.get("total_equity", 0)))

    print("=" * 65)
    print("  GRVT MM Bot v6 — 両建てクオート + リスク管理")
    print(f"  MAX_INV={MAX_INV} BTC | "
          f"SL={float(STOP_LOSS_PCT)*100}% | "
          f"日次上限=${DAILY_LOSS_LIMIT}")
    print("=" * 65)
    print(f"✅ ログイン成功  残高: ${float(start_balance):,.2f}")

    try:
        while True:
            mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))
            if mid == 0:
                print("  [WARN] mid price取得失敗 — スキップ")
                await asyncio.sleep(REFRESH_SEC)
                continue

            result = await on_market_tick(grvt, mid)
            if result == "STOP":
                break

            # Fill detection
            acct     = await get_account_data(grvt)
            pos_list = acct.get("positions", [])

            # Find BTC_USDT_Perp position
            new_pos = Decimal("0")
            for p in pos_list:
                if p.get("instrument") == SYMBOL:
                    raw = Decimal(str(p["size"]))
                    # Positive = long, negative = short
                    new_pos = raw
                    break

            if new_pos != position:
                diff = new_pos - position
                side = "BID" if diff > 0 else "ASK"
                fill_price = mid
                print(f"  💰 [{'BID' if diff>0 else 'ASK'}フィル] "
                      f"{'+'if diff>0 else ''}{float(diff):.3f}BTC"
                      f" @ ${float(fill_price):,.1f}"
                      f"  Pos:{float(new_pos):+.3f}BTC")
                await on_fill(side, fill_price, abs(diff), True)

            await asyncio.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        print("\n⏹ 手動停止 — クリーンアップ中...")
    finally:
        await market_close_all(grvt, "SHUTDOWN")
        data    = await get_account_data(grvt)
        end_bal = float(data.get("total_equity", 0))
        print("=" * 65)
        print(f"  開始: ${float(start_balance):,.2f}"
              f" → 終了: ${end_bal:,.2f}")
        print(f"  純損益: ${end_bal-float(start_balance):+.4f}")
        print(f"  出来高: ${float(total_volume):,.0f}")
        print("=" * 65)
        await grvt.close()


if __name__ == "__main__":
    asyncio.run(main())
