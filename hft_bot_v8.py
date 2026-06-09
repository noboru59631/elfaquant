import asyncio, time, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

SYMBOL           = "BTC_USDT_Perp"
BASE_SIZE        = Decimal("0.08")
MAX_POSITION     = Decimal("0.08")
SPREAD_OFFSET    = Decimal("0.5")
REORDER_THRESH   = Decimal("0.3")
REFRESH_SEC      = 0.15
DAILY_LOSS_LIMIT = Decimal("-100.0")
MAKER_REBATE     = Decimal("0.00001")

position      = Decimal("0")
daily_pnl     = Decimal("0")
total_vol     = Decimal("0")
total_rebate  = Decimal("0")
fill_count    = 0
start_balance = Decimal("0")
last_bid_px   = Decimal("0")
last_ask_px   = Decimal("0")

async def main():
    global position, daily_pnl, total_vol, total_rebate
    global fill_count, start_balance, last_bid_px, last_ask_px

    env = {k.strip(): v.strip()
           for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines()
           if "=" in line and not line.startswith("#")
           for k, v in [line.split("=", 1)]}

    grvt = GrvtClient(
        api_key=env["GRVT_TRADING_API_KEY"],
        private_key=env["GRVT_TRADING_PRIVATE_KEY"])
    await grvt.login()

    from mm_bot_v6 import get_account_data, cancel_all as ca
    acct = await get_account_data(grvt)
    start_balance = Decimal(str(
        acct.get("total_equity", 0) or acct.get("totalEquity", 0) or 0))

    print("=" * 62)
    print("  GRVT HFT Volume Bot v8.1")
    print("  SIZE=" + str(BASE_SIZE) + " MAX=" + str(MAX_POSITION) + " DailyLimit=" + str(DAILY_LOSS_LIMIT))
    print("  SPREAD=" + str(SPREAD_OFFSET) + " REFRESH=" + str(REFRESH_SEC) + "s  [LIVE]")
    print("=" * 62)
    print("  Login OK  Balance: " + str(float(start_balance)))

    last_snap  = time.time()
    loop_count = 0
    mid        = Decimal("0")

    try:
        while True:
            mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))

            if loop_count % 3 == 0:
                acct = await get_account_data(grvt)
                equity = Decimal(str(
                    acct.get("total_equity", 0) or
                    acct.get("totalEquity", 0) or start_balance))
                daily_pnl = equity - start_balance

                new_pos = Decimal("0")
                for p in acct.get("positions", []):
                    if p.get("instrument") == SYMBOL:
                        new_pos = Decimal(str(p["size"]))
                        break
                if new_pos != position:
                    diff = new_pos - position
                    side = "BIDfill" if diff > 0 else "ASKfill"
                    vol  = abs(diff) * mid
                    total_vol    += vol
                    total_rebate += vol * MAKER_REBATE
                    fill_count   += 1
                    sign = "+" if diff > 0 else ""
                    print("  [" + side + "] " + sign + str(round(float(diff),3)) + "BTC @ " + str(round(float(mid),1)) + "  Pos:" + str(round(float(new_pos),3)) + "BTC")
                    position = new_pos

            # 損失上限チェック ($100)
            if daily_pnl < DAILY_LOSS_LIMIT:
                print("  [LOSS LIMIT] $" + str(round(float(daily_pnl),2)) + " → 損失上限 $100 到達、停止します")
                break

            new_bid = mid - SPREAD_OFFSET
            new_ask = mid + SPREAD_OFFSET

            if abs(new_bid - last_bid_px) > REORDER_THRESH or abs(new_ask - last_ask_px) > REORDER_THRESH:
                try:
                    await ca(grvt)
                    last_bid_px = Decimal("0")
                    last_ask_px = Decimal("0")
                except Exception as e:
                    print("  [cancel] " + str(e))

                # BID注文: ロング偏りすぎていない場合のみ
                if position < MAX_POSITION and position <= Decimal("0.04"):
                    bid_size = min(BASE_SIZE, MAX_POSITION - position)
                    bid_size = (bid_size / Decimal("0.001")).to_integral_value() * Decimal("0.001")
                    if bid_size >= Decimal("0.001"):
                        try:
                            await grvt._place_single_order(
                                symbol=SYMBOL, is_buying=True,
                                amount=bid_size, is_market=False,
                                limit_price=new_bid.quantize(Decimal("0.1")),
                                time_in_force="GTT",
                                post_only=True, reduce_only=False)
                            last_bid_px = new_bid
                        except Exception as e:
                            print("  [bid] " + str(e))

                # ASK注文: ショート偏りすぎていない場合のみ
                if position > -MAX_POSITION and position >= Decimal("-0.04"):
                    ask_size = min(BASE_SIZE, MAX_POSITION + position)
                    ask_size = (ask_size / Decimal("0.001")).to_integral_value() * Decimal("0.001")
                    if ask_size >= Decimal("0.001"):
                        try:
                            await grvt._place_single_order(
                                symbol=SYMBOL, is_buying=False,
                                amount=ask_size, is_market=False,
                                limit_price=new_ask.quantize(Decimal("0.1")),
                                time_in_force="GTT",
                                post_only=True, reduce_only=False)
                            last_ask_px = new_ask
                        except Exception as e:
                            print("  [ask] " + str(e))

            now = time.time()
            if now - last_snap >= 5.0:
                sprd = last_ask_px - last_bid_px if last_ask_px > 0 else Decimal("0")
                ts = time.strftime("%H:%M:%S")
                print("[" + ts + "] mid=" + str(round(float(mid),1)) + " sprd=" + str(round(float(sprd),1)) + " Pos=" + str(round(float(position),3)) + " PnL=" + str(round(float(daily_pnl),3)) + " Vol=" + str(round(float(total_vol),0)) + " F:" + str(fill_count))
                last_snap = now

            loop_count += 1
            await asyncio.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        print("  手動停止")
    finally:
        try:
            await ca(grvt)
        except:
            pass
        print("=" * 62)
        print("  Vol="    + str(round(float(total_vol),0)))
        print("  Rebate=" + str(round(float(total_rebate),4)))
        print("  Fills="  + str(fill_count))
        print("  PnL="    + str(round(float(daily_pnl),3)))
        print("  Pos="    + str(round(float(position),3)))
        print("=" * 62)
        await grvt.close()

asyncio.run(main())
