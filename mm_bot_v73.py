import asyncio, time, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

# ============================================================
# 設定
# ============================================================
SYMBOL            = "BTC_USDT_Perp"
BASE_SIZE         = Decimal("0.08")
SPREAD_ENTRY      = Decimal("2.0")
CLOSE_OFFSET_INIT = Decimal("0.3")
CLOSE_OFFSET_STEP = Decimal("0.2")
CLOSE_MAX_TRIES   = 10
CLOSE_WAIT_SEC    = 1.0
DAILY_LOSS_LIMIT  = Decimal("-20.0")
MAKER_REBATE      = Decimal("0.00001")
TAKER_FEE         = Decimal("0.00037")
DRY_RUN           = False

# ============================================================
# 状態
# ============================================================
position      = Decimal("0")
daily_pnl     = Decimal("0")
total_vol     = Decimal("0")
total_rebate  = Decimal("0")
taker_count   = 0
fill_count    = 0
start_balance = Decimal("0")
cycle         = 0

# ============================================================
# ヘルパー
# ============================================================
async def get_acct(grvt):
    from mm_bot_v6 import get_account_data
    return await get_account_data(grvt)

async def cancel_all(grvt):
    try:
        from mm_bot_v6 import cancel_all as ca
        await ca(grvt)
    except Exception as e:
        print("  [cancel] " + str(e))

async def place_maker(grvt, is_buy, price, size, reduce_only=False):
    if DRY_RUN:
        print("  [DRY] " + ("BID" if is_buy else "ASK") + " " + str(price) + " x" + str(size))
        return True
    try:
        await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buy,
            amount=size, is_market=False,
            limit_price=price, time_in_force="GTT",
            post_only=True, reduce_only=reduce_only)
        return True
    except Exception as e:
        print("  [order] " + str(e))
        return False

async def taker_close(grvt, mid):
    global position, daily_pnl, taker_count
    if abs(position) < Decimal("0.001"):
        return
    is_buy = position < 0
    size = abs(position)
    lp = (mid * (Decimal("1.02") if is_buy else Decimal("0.98"))).quantize(Decimal("0.1"))
    fee = size * mid * TAKER_FEE
    daily_pnl -= fee
    taker_count += 1
    if not DRY_RUN:
        try:
            await grvt._place_single_order(
                symbol=SYMBOL, is_buying=is_buy,
                amount=size, is_market=True,
                limit_price=lp, time_in_force="IOC",
                reduce_only=True)
        except Exception as e:
            print("  [taker close] " + str(e))
    print("  [TakerClose] size=" + str(size) + " fee=-" + str(round(float(fee), 4)))

async def get_pos(grvt):
    acct = await get_acct(grvt)
    for p in acct.get("positions", []):
        if p.get("instrument") == SYMBOL:
            return Decimal(str(p["size"]))
    return Decimal("0")

# ============================================================
# コア：エントリーフィル後に即メイカークローズ
# ============================================================
async def maker_close_loop(grvt, entry_mid):
    global position, total_vol, total_rebate, fill_count

    is_buy  = position < 0
    size    = abs(position)
    mid     = entry_mid

    for attempt in range(1, CLOSE_MAX_TRIES + 1):
        await cancel_all(grvt)

        offset   = CLOSE_OFFSET_INIT + CLOSE_OFFSET_STEP * (attempt - 1)
        close_px = (mid - offset if is_buy else mid + offset).quantize(Decimal("0.1"))

        print("  [MakerClose #" + str(attempt) + "] px=" + str(close_px) + " offset=" + str(round(float(offset), 1)))
        await place_maker(grvt, is_buy, close_px, size, reduce_only=True)
        await asyncio.sleep(CLOSE_WAIT_SEC)

        new_pos = await get_pos(grvt)
        if new_pos != position:
            filled  = abs(position - new_pos)
            vol     = filled * mid
            total_vol    += vol
            total_rebate += vol * MAKER_REBATE
            fill_count   += 1
            position = new_pos
            print("  [CloseFill]残Pos=" + str(round(float(position), 3)) + " cumVol=" + str(round(float(total_vol), 0)))

        if abs(position) < Decimal("0.001"):
            print("  [CloseOK] " + str(attempt) + "回目で完了 " + "+" + str(round(float(total_rebate), 4)) + " rebate")
            return True

        mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))

    print("  [CloseFAIL] Makerで閉じきれず → テイカークローズ")
    mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))
    await taker_close(grvt, mid)
    position = await get_pos(grvt)
    return False

# ============================================================
# メインループ
# ============================================================
async def main():
    global position, daily_pnl, total_vol, total_rebate
    global fill_count, start_balance, cycle

    env = {k.strip(): v.strip()
           for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines()
           if "=" in line and not line.startswith("#")
           for k, v in [line.split("=", 1)]}

    grvt = GrvtClient(
        api_key=env["GRVT_TRADING_API_KEY"],
        private_key=env["GRVT_TRADING_PRIVATE_KEY"])
    await grvt.login()

    acct = await get_acct(grvt)
    start_balance = Decimal(str(acct.get("total_equity", 0) or 0))

    print("=" * 62)
    print("  GRVT Maker Cycle Bot v7.3  [案3: 即メイカークローズ]")
    print("  SIZE=" + str(BASE_SIZE) + " SPREAD=" + str(SPREAD_ENTRY))
    print("  CloseOffset=" + str(CLOSE_OFFSET_INIT) + " Step=" + str(CLOSE_OFFSET_STEP) + " MaxTries=" + str(CLOSE_MAX_TRIES))
    print("  DailyLimit=" + str(DAILY_LOSS_LIMIT) + "  " + ("[DRY]" if DRY_RUN else "[LIVE]"))
    print("=" * 62)
    print("  Login OK  Balance: " + str(round(float(start_balance), 2)))
    print()

    position = await get_pos(grvt)

    try:
        while True:
            mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))

            acct = await get_acct(grvt)
            equity    = Decimal(str(acct.get("total_equity", 0) or start_balance))
            daily_pnl = equity - start_balance

            if daily_pnl < DAILY_LOSS_LIMIT:
                print("  DailyLimit: " + str(round(float(daily_pnl), 2)))
                break

            if abs(position) >= Decimal("0.001"):
                print("  [残ポジ処理] pos=" + str(round(float(position), 3)))
                await maker_close_loop(grvt, mid)
                continue

            # ポジションゼロ → 両側エントリー注文
            cycle += 1
            await cancel_all(grvt)

            bid_px = (mid - SPREAD_ENTRY / 2).quantize(Decimal("0.1"))
            ask_px = (mid + SPREAD_ENTRY / 2).quantize(Decimal("0.1"))

            await place_maker(grvt, True,  bid_px, BASE_SIZE)
            await place_maker(grvt, False, ask_px, BASE_SIZE)

            ts = time.strftime("%H:%M:%S")
            print("[" + ts + "] Cycle#" + str(cycle) +
                  " BID=" + str(bid_px) +
                  " ASK=" + str(ask_px) +
                  " mid=" + str(round(float(mid), 1)) +
                  " PnL=" + str(round(float(daily_pnl), 3)) +
                  " Vol=" + str(round(float(total_vol), 0)) +
                  " F:" + str(fill_count) +
                  " Taker:" + str(taker_count))

            # 1秒待ってフィル確認
            await asyncio.sleep(1.0)

            new_pos = await get_pos(grvt)
            if new_pos != position:
                filled = abs(new_pos - position)
                vol    = filled * mid
                total_vol    += vol
                total_rebate += vol * MAKER_REBATE
                fill_count   += 1
                position = new_pos
                print("  [EntryFill] pos=" + str(round(float(position), 3)) +
                      " vol=" + str(round(float(total_vol), 0)))
                await maker_close_loop(grvt, mid)
            else:
                # フィルなし → キャンセルして次サイクル
                await cancel_all(grvt)

    except KeyboardInterrupt:
        print("  Stopped")
    finally:
        await cancel_all(grvt)
        if abs(position) >= Decimal("0.001"):
            mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))
            await taker_close(grvt, mid)
        print("=" * 62)
        print("  Vol="     + str(round(float(total_vol), 0)) +
              " Rebate="   + str(round(float(total_rebate), 4)) +
              " Fills="    + str(fill_count) +
              " Takers="   + str(taker_count) +
              " PnL="      + str(round(float(daily_pnl), 3)))
        print("=" * 62)
        await grvt.close()

asyncio.run(main())
