"""
================================================================
  GRVT HFT Volume Bot v8
  戦略：Post-Only メイカー両建て + 高速キャンセル＆リプレイス
  認証：v7と同じ .env + GrvtClient を流用
================================================================
"""

import asyncio
import time
import pathlib
import json
from decimal import Decimal
from datetime import datetime, timezone
from colorama import Fore, Style, init

# v7と同じクライアントをそのまま流用
from elfa_grvt_bot.grvt_client import GrvtClient
from mm_bot_v7 import get_account as get_account_data, cancel_all as cancel_all_v7

init(autoreset=True)

# ================================================================
#  ⚙️  設定値（ここだけ書き換えればOK）
# ================================================================

SYMBOL         = "BTC_USDT_Perp"       # 取引ペア
BASE_SIZE      = Decimal("0.05")       # 1注文あたりのBTCサイズ
MAX_POSITION   = Decimal("0.05")  # BASE_SIZEと同じ：ナンピン完全排除       # 最大許容ポジション（BTC）
SPREAD_OFFSET  = Decimal("0.5")        # ミッドからの価格オフセット（$）
REORDER_THRESH = Decimal("1.0")        # 再配置トリガー価格差（$）
REFRESH_SEC    = 0.5                   # ループ間隔（秒）★v7の3.0sより高速

# 安全装置
MAX_CONSEC_ERRORS = 5                  # 連続エラー上限
DAILY_LOSS_LIMIT  = Decimal("-20.0")   # 日次損失上限（USD）

# 手数料
MAKER_REBATE   = Decimal("0.00001")    # メイカーリベート率 0.001%
TAKER_FEE      = Decimal("0.00037")   # テイカー手数料率（使用禁止）

DRY_RUN        = False                 # テスト時はTrue

# ================================================================
#  📊  状態管理
# ================================================================

position        : Decimal = Decimal("0")
bid_price       : Decimal | None = None   # 現在発注中のBID価格
ask_price       : Decimal | None = None   # 現在発注中のASK価格
total_volume    : Decimal = Decimal("0")  # 累積取引高（USDT）
total_rebate    : Decimal = Decimal("0")  # 累積リベート（USD）
daily_pnl       : Decimal = Decimal("0")  # 日次損益
consec_errors   : int     = 0             # 連続エラー回数
fill_count      : int     = 0             # 約定回数
start_balance   : Decimal = Decimal("0")  # セッション開始残高
mid_price       : Decimal = Decimal("0")  # 現在ミッド価格
running         : bool    = True          # 稼働フラグ
start_time      : float   = time.time()

# ================================================================
#  📝  ログ表示
# ================================================================

def log_snapshot():
    """現在状態をカラー表示（v7スタイル踏襲）"""
    elapsed = int(time.time() - start_time)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60

    pos_color = Fore.GREEN if position >= 0 else Fore.RED
    pnl_color = Fore.GREEN if daily_pnl >= 0 else Fore.RED

    bid_str = f"${float(bid_price):,.1f}" if bid_price else "---"
    ask_str = f"${float(ask_price):,.1f}" if ask_price else "---"

    print(
        f"{Fore.CYAN}[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]{Style.RESET_ALL} "
        f"mid=${float(mid_price):,.1f} "
        f"BID:{bid_str} ASK:{ask_str} "
        f"Pos:{pos_color}{float(position):+.3f}BTC{Style.RESET_ALL} "
        f"日次:{pnl_color}${float(daily_pnl):+.3f}{Style.RESET_ALL} "
        f"Vol:${float(total_volume):,.0f} "
        f"Rebate:${float(total_rebate):.4f} "
        f"F:{fill_count} "
        f"[{h:02d}:{m:02d}:{s:02d}]"
    )

def log_fill(side: str, size: Decimal, price: Decimal, rebate: Decimal):
    emoji = "🟢" if side == "BID" else "🔴"
    sign  = "+" if side == "BID" else "-"
    print(
        f"  {emoji} {Fore.YELLOW}[{side}フィル]{Style.RESET_ALL} "
        f"{sign}{float(size):.3f}BTC @ ${float(price):,.1f}  "
        f"Rebate:+${float(rebate):.4f}  "
        f"累積Vol:${float(total_volume):,.0f}"
    )

def log_error(msg: str):
    print(f"  {Fore.RED}❌ [ERROR]{Style.RESET_ALL} {msg}")

def log_info(msg: str):
    print(f"  {Fore.BLUE}ℹ️  {Style.RESET_ALL}{msg}")

def log_warning(msg: str):
    print(f"  {Fore.YELLOW}⚠️  {Style.RESET_ALL}{msg}")

def log_circuit_breaker(reason: str):
    print(f"\n{'='*60}")
    print(f"  {Fore.RED}🚨 サーキットブレーカー発動{Style.RESET_ALL}")
    print(f"  理由: {reason}")
    print(f"  累積取引高  : ${float(total_volume):,.0f}")
    print(f"  累積リベート: ${float(total_rebate):.4f}")
    print(f"  日次損益    : ${float(daily_pnl):+.3f}")
    print(f"{'='*60}\n")

def print_summary():
    elapsed = int(time.time() - start_time)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}📊 v8 セッションサマリー{Style.RESET_ALL}")
    print(f"  稼働時間     : {h:02d}:{m:02d}:{s:02d}")
    print(f"  累積取引高   : {Fore.YELLOW}${float(total_volume):,.2f}{Style.RESET_ALL}")
    print(f"  累積リベート : {Fore.GREEN}+${float(total_rebate):.4f}{Style.RESET_ALL}")
    print(f"  約定回数     : {fill_count}回")
    print(f"  日次損益     : "
          f"{Fore.GREEN if daily_pnl >= 0 else Fore.RED}"
          f"${float(daily_pnl):+.3f}{Style.RESET_ALL}")
    print(f"  最終ポジション: {float(position):+.3f}BTC")
    print(f"{'='*60}\n")

# ================================================================
#  📡  注文操作（GrvtClientを直接使用）
# ================================================================

async def place_maker_order(
    grvt    : GrvtClient,
    is_buy  : bool,
    price   : Decimal,
    size    : Decimal
) -> bool:
    """
    Post-Only メイカー注文を発注
    - post_only=True でテイカー約定を完全回避
    """
    global consec_errors

    if DRY_RUN:
        side = "BID" if is_buy else "ASK"
        log_info(f"[DRY] {side} ${float(price):,.1f} x{float(size):.3f}")
        return True

    try:
        await grvt._place_single_order(
            symbol       = SYMBOL,
            is_buying    = is_buy,
            amount       = size,
            is_market    = False,
            limit_price  = price,
            time_in_force= "GTC",
            post_only    = True,    # ← テイカー完全回避
            reduce_only  = False,
        )
        consec_errors = 0           # 成功時はエラーカウントリセット
        return True

    except Exception as e:
        log_error(f"注文失敗 {'BID' if is_buy else 'ASK'}@{float(price):,.1f}: {e}")
        consec_errors += 1
        return False

async def do_cancel_all(grvt: GrvtClient):
    """全注文キャンセル（v7のcancel_allを流用）"""
    global bid_price, ask_price
    if DRY_RUN:
        bid_price = None
        ask_price = None
        return
    try:
        await cancel_all_v7(grvt)
        bid_price = None
        ask_price = None
    except Exception as e:
        log_error(f"キャンセル失敗: {e}")

# ================================================================
#  🔄  コアMMロジック
# ================================================================

async def refresh_and_place(grvt: GrvtClient):
    """
    価格乖離チェック → キャンセル → 両側再発注
    v8の中心ロジック
    """
    global bid_price, ask_price, position

    if mid_price == 0:
        return

    new_bid = (mid_price - SPREAD_OFFSET).quantize(Decimal("0.1"))
    new_ask = (mid_price + SPREAD_OFFSET).quantize(Decimal("0.1"))

    # 乖離チェック：REORDER_THRESH以上ずれたらリプレイス
    bid_stale = (bid_price is None or
                 abs(bid_price - new_bid) > REORDER_THRESH)
    ask_stale = (ask_price is None or
                 abs(ask_price - new_ask) > REORDER_THRESH)

    if not bid_stale and not ask_stale:
        return  # 両方まだ有効 → 何もしない

    # 全キャンセル → 再発注
    await do_cancel_all(grvt)

    tasks = []

    # ポジション制限チェック付きで発注
    can_buy  = position + BASE_SIZE <= MAX_POSITION
    can_sell = position - BASE_SIZE >= -MAX_POSITION

    if can_buy:
        tasks.append(("BID", place_maker_order(grvt, True,  new_bid, BASE_SIZE)))
    else:
        log_warning(f"BIDスキップ: ポジション上限 {float(position):+.3f}BTC")

    if can_sell:
        tasks.append(("ASK", place_maker_order(grvt, False, new_ask, BASE_SIZE)))
    else:
        log_warning(f"ASKスキップ: ポジション下限 {float(position):+.3f}BTC")

    if not tasks:
        return

    # BID/ASK 並列発注
    results = await asyncio.gather(*[t[1] for t in tasks])

    for (side, _), ok in zip(tasks, results):
        if ok:
            if side == "BID":
                bid_price = new_bid
            else:
                ask_price = new_ask

# ================================================================
#  📊  フィル検知 + 状態更新
# ================================================================

async def detect_fills(grvt: GrvtClient, prev_pos: Decimal) -> Decimal:
    """
    ポジション変化からフィルを検知し
    出来高・リベート・損益を更新して新しいポジションを返す
    """
    global position, total_volume, total_rebate
    global fill_count, daily_pnl

    # v7と同じアカウント取得関数を流用
    acct   = await get_account_data(grvt)
    equity = Decimal(str(
        acct.get("total_equity", 0) or
        acct.get("totalEquity", 0) or
        start_balance
    ))
    daily_pnl = equity - start_balance

    # ポジション取得
    new_pos = Decimal("0")
    for p in acct.get("positions", []):
        if p.get("instrument") == SYMBOL:
            new_pos = Decimal(str(p["size"]))
            break

    # フィル検知
    if new_pos != prev_pos:
        diff   = new_pos - prev_pos
        side   = "BID" if diff > 0 else "ASK"

        # 出来高・リベート計算
        notional        = abs(diff) * mid_price
        rebate          = notional * MAKER_REBATE
        total_volume   += notional
        total_rebate   += rebate
        fill_count     += 1

        log_fill(side, abs(diff), mid_price, rebate)

    return new_pos

# ================================================================
#  🚨  サーキットブレーカー
# ================================================================

async def check_circuit_breaker(grvt: GrvtClient) -> bool:
    """
    以下の条件でサーキットブレーカー発動：
    1. 連続エラー ≥ MAX_CONSEC_ERRORS
    2. 日次損失 ≤ DAILY_LOSS_LIMIT
    3. ポジションが MAX_POSITION の1.5倍超
    """
    global running
    reason = None

    if consec_errors >= MAX_CONSEC_ERRORS:
        reason = f"連続エラー {consec_errors}回 (上限: {MAX_CONSEC_ERRORS})"

    elif daily_pnl <= DAILY_LOSS_LIMIT:
        reason = (f"日次損失上限到達: ${float(daily_pnl):.3f} "
                  f"(上限: ${float(DAILY_LOSS_LIMIT)})")

    elif abs(position) > MAX_POSITION * Decimal("1.5"):
        reason = f"ポジション緊急超過: {float(position):+.3f}BTC"

    if reason:
        log_circuit_breaker(reason)
        await do_cancel_all(grvt)
        running = False
        return True

    return False

# ================================================================
#  🚀  メインループ
# ================================================================

async def main():
    global position, mid_price, start_balance, running, start_time

    # ── .env 読み込み（v7と完全同一）──
    env = {
        k.strip(): v.strip()
        for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.startswith("#")
        for k, v in [line.split("=", 1)]
    }

    # ── GrvtClient 初期化（v7と完全同一）──
    grvt = GrvtClient(
        api_key     = env["GRVT_TRADING_API_KEY"],
        private_key = env["GRVT_TRADING_PRIVATE_KEY"]
    )
    await grvt.login()

    # ── 開始残高取得 ──
    acct          = await get_account_data(grvt)
    start_balance = Decimal(str(
        acct.get("total_equity", 0) or
        acct.get("totalEquity", 0) or 0
    ))

    running    = True
    start_time = time.time()

    print(f"\n{'='*62}")
    print(f"  {Fore.GREEN}🚀 GRVT HFT Volume Bot v8{Style.RESET_ALL}")
    print(f"  Symbol   : {SYMBOL}")
    print(f"  Size     : {BASE_SIZE} BTC/注文")
    print(f"  MaxPos   : ±{MAX_POSITION} BTC")
    print(f"  Spread   : ±${SPREAD_OFFSET}")
    print(f"  Refresh  : {REFRESH_SEC}s（v7の{3.0/REFRESH_SEC:.0f}倍速）")
    print(f"  {'[DRY RUN]' if DRY_RUN else '[LIVE]'}")
    print(f"{'='*62}")
    print(f"✅ ログイン成功  残高: ${float(start_balance):,.2f}\n")

    last_snapshot = time.time()

    try:
        while running:

            # ① 価格取得
            try:
                mid_price = Decimal(str(
                    await grvt.fetch_mid_price(SYMBOL)
                ))
            except Exception as e:
                log_error(f"価格取得失敗: {e}")
                await asyncio.sleep(REFRESH_SEC)
                continue

            # ② サーキットブレーカーチェック
            if await check_circuit_breaker(grvt):
                break

            # ③ 注文乖離チェック＆リプレイス（コア）
            await refresh_and_place(grvt)

            # ④ フィル検知＆状態更新
            position = await detect_fills(grvt, position)

            # ⑤ スナップショット（5秒に1回）
            if time.time() - last_snapshot >= 5.0:
                log_snapshot()
                last_snapshot = time.time()

            await asyncio.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        log_info("手動停止（Ctrl+C）")

    finally:
        log_info("シャットダウン中...")
        await do_cancel_all(grvt)
        print_summary()
        await grvt.close()


# ================================================================
#  エントリーポイント
# ================================================================

if __name__ == "__main__":
    asyncio.run(main())
