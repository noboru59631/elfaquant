"""place_sl.py - BTC ショートポジションにSLとTP補完を設定"""
import asyncio, pathlib, time, random
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

SYMBOL        = "BTC_USDT_Perp"
ENTRY_PRICE   = 75386.29        # 実際のエントリー平均価格
POSITION_SIZE = 0.022           # ショートポジション合計
EXISTING_TP   = 0.018           # 既存TPがカバーしている量
REMAINING     = round(POSITION_SIZE - EXISTING_TP, 4)  # 0.004 BTC 未カバー分

SL_PCT  = 1.5   # エントリーから+1.5%上でSL（ショートなので価格上昇がリスク）
TP_PCT  = 3.5   # エントリーから-3.5%下でTP補完

sl_price = round(ENTRY_PRICE * (1 + SL_PCT / 100), 1)
tp_price = round(ENTRY_PRICE * (1 - TP_PCT / 100), 1)

print(f"ポジション  : SHORT {POSITION_SIZE} BTC @ ${ENTRY_PRICE:,.2f}")
print(f"既存TP      : {EXISTING_TP} BTC @ $74,978.7")
print(f"未カバー分  : {REMAINING} BTC")
print(f"SL価格      : ${sl_price:,.1f}  (+{SL_PCT}%)")
print(f"TP補完価格  : ${tp_price:,.1f}  (-{TP_PCT}%)")
print()

async def main():
    grvt = GrvtClient(
        api_key=env.get("GRVT_TRADING_API_KEY", ""),
        private_key=env.get("GRVT_TRADING_PRIVATE_KEY", "")
    )
    try:
        ok = await grvt.login()
        if not ok:
            print("ERROR: ログイン失敗"); return
        print(f"Login OK: account_id={grvt.account_id}")

        # --- SL注文: ポジション全体(0.022)をカバー ---
        print(f"\n--- SL注文送信: BUY {POSITION_SIZE} BTC market reduce_only @ >${sl_price:,.1f} ---")
        sl_result = await grvt._place_single_order(
            symbol=SYMBOL,
            side="buy",
            amount=POSITION_SIZE,
            is_market=True,
            reduce_only=True,
            trigger_price=sl_price,
            reference_price=ENTRY_PRICE
        )
        print(f"SL結果: {sl_result}")

    except TypeError:
        # trigger_price非対応の場合はシンプルなmarket SLとして送信
        print("trigger_price非対応 → シンプルSLとして送信")
        try:
            sl_result = await grvt._place_single_order(
                symbol=SYMBOL,
                side="buy",
                amount=POSITION_SIZE,
                is_market=True,
                reduce_only=True,
                reference_price=ENTRY_PRICE
            )
            print(f"SL結果: {sl_result}")
        except Exception as e:
            print(f"SL送信エラー: {e}")

    # --- TP補完注文: 残り0.004 BTC ---
    if REMAINING > 0:
        print(f"\n--- TP補完注文: BUY {REMAINING} BTC limit @ ${tp_price:,.1f} reduce_only ---")
        try:
            tp_result = await grvt._place_single_order(
                symbol=SYMBOL,
                side="buy",
                amount=REMAINING,
                is_market=False,
                reduce_only=True,
                limit_price=tp_price,
                reference_price=ENTRY_PRICE
            )
            print(f"TP補完結果: {tp_result}")
        except Exception as e:
            print(f"TP補完エラー: {e}")

    await grvt.close()

asyncio.run(main())
