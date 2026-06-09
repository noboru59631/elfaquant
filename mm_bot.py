import asyncio
import pathlib
import time
import httpx
from decimal import Decimal

from elfa_grvt_bot.grvt_client import GrvtClient

# ─── 設定 ───────────────────────────────────────────────
SYMBOL         = "BTC_USDT_Perp"
ORDER_SIZE     = Decimal("0.01")
REFRESH_SEC    = 2.0
MAX_POSITION   = Decimal("0.03")
STOP_BALANCE   = 900.0
MAX_DAILY_LOSS = 60.0
MAKER_REBATE   = 0.00001
TAKER_FEE      = 0.00037
LONELY_SEC     = 30          # 片側約定後の待機秒数
MAKER_CLOSE_TIMEOUT = 60     # Maker指値クローズの待機秒数
SPREAD_MIN     = 0.0002      # 最小スプレッド 2bps
SPREAD_ALPHA   = 0.3         # ATR感度係数
RSI_LONG_THR   = 55          # RSI 1h > 55 → BIDのみ
RSI_SHORT_THR  = 45          # RSI 1h < 45 → ASKのみ
EMA_DEV_THR    = 0.002       # EMA乖離率 0.2% 超でトレンド確定
ADX_THR        = 25          # ADX > 25 でトレンド相場

MARKET_URL  = "https://market-data.grvt.io/full/v1/mini"
ACCT_URL    = "https://trades.grvt.io/full/v1/account_summary"
CANCEL_URL  = "https://trades.grvt.io/full/v1/cancel_all_orders"
BINANCE_URL = "https://api.binance.com/api/v3/klines"

env = {k.strip(): v.strip()
       for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines()
       if "=" in line and not line.startswith("#")
       for k, v in [line.split("=", 1)]}

# ─── 市場指標計算 ─────────────────────────────────────
async def get_market_indicators() -> dict:
    """RSI(1h), EMA乖離率, ATR, ADXを計算"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(BINANCE_URL, params={
                "symbol": "BTCUSDT", "interval": "1h", "limit": 50
            })
        klines = r.json()
        closes = [float(k[4]) for k in klines]
        highs  = [float(k[2]) for k in klines]
        lows   = [float(k[3]) for k in klines]

        # RSI(14)
        gains, losses = [], []
        for i in range(1, 15):
            d = closes[-i] - closes[-i-1]
            (gains if d > 0 else losses).append(abs(d))
        avg_gain = sum(gains) / 14 if gains else 0.001
        avg_loss = sum(losses) / 14 if losses else 0.001
        rs  = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # EMA(20) 乖離率
        ema = closes[-20]
        for p in closes[-19:]:
            ema = p * (2/21) + ema * (19/21)
        ema_dev = (closes[-1] - ema) / ema

        # ATR(14)
        trs = []
        for i in range(1, 15):
            tr = max(
                highs[-i] - lows[-i],
                abs(highs[-i] - closes[-i-1]),
                abs(lows[-i]  - closes[-i-1])
            )
            trs.append(tr)
        atr = sum(trs) / 14

        # ADX(14) 簡易計算
        plus_dms, minus_dms, atr14s = [], [], []
        for i in range(1, 15):
            up   = highs[-i] - highs[-i-1]
            down = lows[-i-1] - lows[-i]
            plus_dms.append(up   if up > down and up > 0   else 0)
            minus_dms.append(down if down > up and down > 0 else 0)
            tr = max(highs[-i]-lows[-i],
                     abs(highs[-i]-closes[-i-1]),
                     abs(lows[-i]-closes[-i-1]))
            atr14s.append(tr)
        atr14 = sum(atr14s) / 14 or 0.001
        plus_di  = (sum(plus_dms)  / 14) / atr14 * 100
        minus_di = (sum(minus_dms) / 14) / atr14 * 100
        dx  = abs(plus_di - minus_di) / (plus_di + minus_di + 0.001) * 100
        adx = dx  # 簡易版（本来は平滑化が必要）

        return {
            "rsi": rsi, "ema_dev": ema_dev,
            "atr": atr, "adx": adx, "price": closes[-1]
        }
    except Exception as e:
        print(f"  [指標エラー] {e}")
        return {"rsi": 50, "ema_dev": 0, "atr": 200, "adx": 0, "price": 0}

def determine_mode(rsi: float, ema_dev: float, adx: float) -> str:
    """トレンド判定: BID_ONLY / ASK_ONLY / BOTH"""
    # ADX > 25 かつ EMA乖離が大きい → 強トレンド
    strong_up   = adx > ADX_THR and ema_dev >  EMA_DEV_THR
    strong_down = adx > ADX_THR and ema_dev < -EMA_DEV_THR

    if strong_up   or rsi > RSI_LONG_THR:  return "BID_ONLY"
    if strong_down or rsi < RSI_SHORT_THR: return "ASK_ONLY"
    return "BOTH"

def calc_spread(atr: float, price: float) -> float:
    """ATR連動型スプレッド計算"""
    if price <= 0:
        return SPREAD_MIN
    vol_spread = SPREAD_ALPHA * (atr / price)
    return max(SPREAD_MIN, min(vol_spread, 0.0003))  # 最大0.03%

# ─── API関数 ──────────────────────────────────────────
async def get_bid_ask() -> tuple[float, float]:
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.post(MARKET_URL, json={"instrument": SYMBOL})
        d = r.json()["result"]
        return float(d["best_bid_price"]), float(d["best_ask_price"])

async def get_account_data(grvt: GrvtClient) -> dict:
    try:
        r = await grvt.client.post(
            ACCT_URL,
            json={"sub_account_id": str(grvt.account_id)},
            cookies={"gravity": grvt.cookie},
        )
        if r.status_code == 200:
            return r.json().get("result", {})
    except Exception as e:
        print(f"  [アカウントエラー] {e}")
    return {}

async def cancel_all(grvt: GrvtClient):
    try:
        await grvt.client.post(
            CANCEL_URL,
            json={"sub_account_id": str(grvt.account_id)},
            cookies={"gravity": grvt.cookie},
        )
    except Exception:
        pass

async def place_limit(grvt, is_buying, price, size, post_only=True) -> dict:
    try:
        result = await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buying,
            amount=size, is_market=False,
            limit_price=Decimal(str(price)),
            time_in_force="GTT",
            reduce_only=False, post_only=post_only,
        )
        return result or {}
    except Exception as e:
        print(f"  [注文エラー] {'BUY' if is_buying else 'SELL'} @ {price}: {e}")
        return {}

async def place_market_close(grvt, position: Decimal) -> dict:
    """段階的クローズ: 指値(5s待機) → 失敗なら成行"""
    if position == 0:
        return {}
    is_buying = position < 0  # ショートならBUY、ロングならSELL
    size = abs(position)

    # Step1: 指値で試みる (5秒待機)
    try:
        best_bid, best_ask = await get_bid_ask()
        mid = (best_bid + best_ask) / 2
        # 有利な指値: ロングクローズ=BID+0.1上, ショートクローズ=ASK-0.1下
        lp = round(best_ask - 0.1, 1) if is_buying else round(best_bid + 0.1, 1)
        r = await place_limit(grvt, is_buying, lp, size, post_only=False)
        if r.get("client_order_id"):
            print(f"  [段階クローズ] 指値 @ ${lp:,.1f} で試行中...")
            await asyncio.sleep(5)
            # ポジション確認
            data = await get_account_data(grvt)
            pos_now = Decimal("0")
            for pos in data.get("positions", []):
                if pos.get("instrument") == SYMBOL:
                    pos_now = Decimal(str(pos["size"]))
            if abs(pos_now) < abs(position) * Decimal("0.5"):
                print(f"  [段階クローズ] 指値約定成功 ✅")
                return r
    except Exception:
        pass

    # Step2: 成行でクローズ
    print(f"  [段階クローズ] 成行でクローズ")
    await cancel_all(grvt)
    try:
        return await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buying,
            amount=size, is_market=True,
            limit_price=None, time_in_force="IOC",
            reduce_only=True, post_only=False,
        )
    except Exception as e:
        print(f"  [成行クローズエラー] {e}")
        return {}

# ─── メインループ ────────────────────────────────────
async def main():
    print("=" * 65)
    print("  GRVT アダプティブMMボット v5")
    print(f"  RSI閾値: BID>{RSI_LONG_THR} / ASK<{RSI_SHORT_THR} / BOTH:その間")
    print(f"  ADX閾値: {ADX_THR}超 + EMA乖離{EMA_DEV_THR*100}%超 → 強制片側")
    print(f"  スプレッド: ATR連動 (最小{SPREAD_MIN*100:.2f}%)")
    print(f"  片側約定タイムアウト: {LONELY_SEC}秒 → 段階クローズ")
    print("=" * 65)

    grvt = GrvtClient(
        env.get("GRVT_TRADING_API_KEY", ""),
        env.get("GRVT_TRADING_PRIVATE_KEY", ""),
    )
    await grvt.login()

    data = await get_account_data(grvt)
    start_balance = float(data.get("total_equity", 0))
    print(f"✅ ログイン成功  残高: ${start_balance:,.2f}\n")

    await cancel_all(grvt)

    daily_pnl      = 0.0
    total_volume   = 0.0
    total_fills    = 0
    bid_fills      = 0
    ask_fills      = 0
    market_closes  = 0
    last_pos       = Decimal("0")
    lonely_since   = None   # 片側約定の検出時刻
    lonely_side    = None   # "BID" or "ASK"
    ind_cache      = {"rsi": 50, "ema_dev": 0, "atr": 200, "adx": 0, "price": 0}
    ind_last_update = 0
    iteration      = 0

    try:
        while True:
            iteration += 1

            # ── 指標更新 (60秒毎) ────────────────────────
            if time.time() - ind_last_update > 60:
                ind_cache = await get_market_indicators()
                ind_last_update = time.time()

            rsi     = ind_cache["rsi"]
            ema_dev = ind_cache["ema_dev"]
            atr     = ind_cache["atr"]
            adx     = ind_cache["adx"]
            mode    = determine_mode(rsi, ema_dev, adx)
            spread  = calc_spread(atr, ind_cache["price"])

            # ── アカウント取得 ────────────────────────────
            data    = await get_account_data(grvt)
            balance = float(data.get("total_equity", 9999))
            position = Decimal("0")
            for pos in data.get("positions", []):
                if pos.get("instrument") == SYMBOL:
                    position = Decimal(str(pos["size"]))

            # ── 安全チェック ──────────────────────────────
            if balance < STOP_BALANCE:
                print(f"\n🛑 残高下限 ${balance:.2f} → 停止")
                break
            if daily_pnl < -MAX_DAILY_LOSS:
                print(f"\n🛑 日次損失上限 → 停止")
                break

            # ── 市場価格取得 ──────────────────────────────
            try:
                best_bid, best_ask = await get_bid_ask()
            except Exception as e:
                print(f"  [価格エラー] {e}")
                await asyncio.sleep(REFRESH_SEC)
                continue

            mid = (best_bid + best_ask) / 2
            half = mid * spread / 2

            # ── 在庫スキュー適用 ──────────────────────────
            pos_ratio = float(position) / float(MAX_POSITION)
            skew = mid * 0.0003 * pos_ratio

            # 常にベスト板の内側1tickに配置 (スプレッド保証付き)
            my_bid = round(best_bid + 0.1 - skew, 1)
            my_ask = round(best_ask - 0.1 - skew, 1)
            # スプレッドが潰れた場合のみフォールバック
            min_gap = round(mid * 0.0002, 1)  # 最小0.02%
            if my_ask - my_bid < min_gap:
                my_bid = round(mid - min_gap / 2, 1)
                my_ask = round(mid + min_gap / 2, 1)

            # ── フィル検出 ────────────────────────────────
            pos_change = position - last_pos
            if abs(pos_change) >= Decimal("0.01"):
                vol = float(abs(pos_change)) * mid
                total_volume += vol * 2
                total_fills  += 1
                rebate = vol * MAKER_REBATE
                daily_pnl += rebate

                if pos_change > 0:
                    bid_fills += 1
                    lonely_since = time.time()
                    lonely_side  = "BID"
                    print(f"\n  💰 [BIDフィル] +{float(pos_change):.3f}BTC @ ${my_bid:,.1f}"
                          f"  リベート:+${rebate:.3f}  ポジ:{float(position):+.3f}BTC")
                else:
                    ask_fills += 1
                    lonely_since = time.time()
                    lonely_side  = "ASK"
                    print(f"\n  💰 [ASKフィル] {float(pos_change):.3f}BTC @ ${my_ask:,.1f}"
                          f"  リベート:+${rebate:.3f}  ポジ:{float(position):+.3f}BTC")

                # 両方フィルされたらlonelyリセット
                if abs(position) < Decimal("0.01"):
                    lonely_since = None
                    lonely_side  = None

                last_pos = position

            # ── Lonelyタイムアウト処理 ────────────────────
            if lonely_since and time.time() - lonely_since > LONELY_SEC:
                if abs(position) >= Decimal("0.01"):
                    elapsed = int(time.time() - lonely_since)
                    print(f"\n  [MAKER_CLOSE] [{lonely_side}のみ約定 {elapsed}秒経過] "
                          f"ポジ:{float(position):+.3f}BTC → Maker指値クローズ試行")
                    await cancel_all(grvt)
                    # Maker指値でクローズ (post_only=True)
                    is_closing_buy = position < 0
                    # ショートクローズ(Buy): best_bid+0.1 / ロングクローズ(Sell): best_ask-0.1
                    close_price = round(best_bid + 0.1 if is_closing_buy else best_ask - 0.1, 1)
                    close_result = await grvt._place_single_order(
                        symbol=SYMBOL,
                        is_buying=is_closing_buy,
                        amount=abs(position),
                        is_market=False,
                        limit_price=Decimal(str(close_price)),
                        time_in_force="GTT",
                        reduce_only=True,
                        post_only=True,
                    )
                    maker_close_id = close_result.get("client_order_id", "")
                    print(f"  Maker指値クローズ注文: {'OK' if maker_close_id else 'NG'} @ ${close_price:,.1f}")
                    # MAKER_TIMEOUT秒待機してフィル確認
                    await asyncio.sleep(MAKER_CLOSE_TIMEOUT)
                    # ポジション再取得
                    acct2 = await get_account_data(grvt)
                    pos_list2 = acct2.get("open_positions", [])
                    pos2 = Decimal(str(pos_list2[0]["size"])) if pos_list2 else Decimal("0")
                    if abs(pos2) >= Decimal("0.01"):
                        # まだ残っていればTakerで強制クローズ
                        print(f"  Maker未フィル → Takerで強制クローズ (残:{float(pos2):+.3f}BTC)")
                        await cancel_all(grvt)
                        await place_market_close(grvt, pos2)
                        market_closes += 1
                        taker_cost = float(abs(pos2)) * mid * TAKER_FEE
                        daily_pnl -= taker_cost
                        print(f"  Taker手数料: -${taker_cost:.3f}")
                    else:
                        print(f"  Makerクローズ成功! リベート獲得")
                        maker_rebate = float(abs(position)) * mid * MAKER_REBATE
                        daily_pnl += maker_rebate
                lonely_since = None
                lonely_side  = None
                await asyncio.sleep(1)
                continue

            # ── 注文更新 ──────────────────────────────────
            await cancel_all(grvt)
            await asyncio.sleep(0.1)

            bid_ok = ask_ok = False

            if mode in ("BID_ONLY", "BOTH") and position < MAX_POSITION:
                r = await place_limit(grvt, True, my_bid, ORDER_SIZE)
                bid_ok = bool(r.get("client_order_id"))

            await asyncio.sleep(0.1)

            if mode in ("ASK_ONLY", "BOTH") and position > -MAX_POSITION:
                r = await place_limit(grvt, False, my_ask, ORDER_SIZE)
                ask_ok = bool(r.get("client_order_id"))

            # ── ログ ──────────────────────────────────────
            mode_icon = {"BID_ONLY": "📈", "ASK_ONLY": "📉", "BOTH": "↔️"}[mode]
            bid_icon  = "✅" if bid_ok else ("🚫" if mode == "ASK_ONLY" else "⚠️")
            ask_icon  = "✅" if ask_ok else ("🚫" if mode == "BID_ONLY" else "⚠️")

            print(f"[{time.strftime('%H:%M:%S')}] {mode_icon}{mode:<9} "
                  f"RSI:{rsi:.1f} ADX:{adx:.1f} Sprd:{spread*100:.3f}% "
                  f"BID:{bid_icon}${my_bid:,.1f} ASK:{ask_icon}${my_ask:,.1f} "
                  f"Pos:{float(position):+.3f} 日次:${daily_pnl:+.3f} "
                  f"Vol:${total_volume:,.0f} F:{total_fills}(B{bid_fills}/A{ask_fills}/M{market_closes})")

            await asyncio.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        print("\n⏹ 手動停止 — 注文キャンセル＆ポジションクローズ中...")

    finally:
        # 🛡️ 正常停止・強制停止どちらでも必ず実行
        await cancel_all(grvt)
        print("  ✅ 全注文キャンセル完了")

        # ポジションが残っていれば成行クローズ
        acct_end = await get_account_data(grvt)
        pos_list_end = acct_end.get("open_positions", [])
        if pos_list_end:
            final_pos = Decimal(str(pos_list_end[0]["size"]))
            if abs(final_pos) >= Decimal("0.01"):
                print(f"  ⚠️ ポジション残存: {float(final_pos):+.3f} BTC → 成行クローズ実行")
                is_closing_buy = final_pos < 0
                await place_market_close(grvt, is_closing_buy, abs(final_pos))
                print("  ✅ ポジション成行クローズ完了")
        else:
            print("  ✅ ポジションなし — 安全に停止")

        data = await get_account_data(grvt)
        end_balance = float(data.get("total_equity", 0))

        print("\n" + "=" * 65)
        print(f"  開始残高: ${start_balance:,.2f} → 終了残高: ${end_balance:,.2f}")
        print(f"  純損益  : ${end_balance - start_balance:+,.4f}")
        print(f"  累計出来高: ${total_volume:,.0f}")
        print(f"  フィル: {total_fills}回 (BID:{bid_fills} ASK:{ask_fills} 成行クローズ:{market_closes})")
        print("=" * 65)
        await grvt.close()

asyncio.run(main())
