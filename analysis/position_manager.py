"""
Position manager: monitors MNT/USDT price, runs Phase1-5 analysis on FLAT state,
and executes entry/exit swaps via mantle_executor.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

THIS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THIS_DIR))

from analysis.main_analysis import run_analysis
from analysis.phase5_sizing import calculate_sizing
import mantle_executor as mx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("position_manager")

TRADES_FILE  = THIS_DIR / "trades.json"
MONITOR_INTERVAL = 10   # seconds
RISK_PCT     = 0.01
TP_RATIO     = 1.005    # +0.5%
SL_RATIO     = 0.997    # -0.3%
BALANCE      = 700.0    # fallback; replaced at runtime if available

# ── State ────────────────────────────────────────────────────────────────────
state: dict = {
    "status":        "FLAT",   # "FLAT" | "LONG"
    "entry_price":   None,
    "entry_time":    None,
    "entry_amount":  None,     # MNT amount held
    "tx_entry":      None,
}


def _get_mnt_price() -> float:
    url = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=MNTUSDT"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["result"]["list"][0]["lastPrice"])


def _load_trades() -> list:
    if TRADES_FILE.exists():
        with open(TRADES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_trade(record: dict) -> None:
    trades = _load_trades()
    trades.append(record)
    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)


def enter_long(price: float, amount_mnt: float) -> None:
    logger.info(f"[POSITION] ENTER_LONG @ ${price:.4f} | amount={amount_mnt} MNT")
    try:
        # Buy MNT: swap USDT → WMNT
        amount_usdt = amount_mnt * price
        tx = mx.execute_short(amount_usdt)
    except Exception as e:
        logger.error(f"[POSITION] enter_long swap failed: {e}")
        return

    state["status"]       = "LONG"
    state["entry_price"]  = price
    state["entry_time"]   = datetime.now(timezone.utc).isoformat()
    state["entry_amount"] = amount_mnt
    state["tx_entry"]     = tx
    logger.info(f"[POSITION] entered LONG tx={tx}")


def exit_long(price: float, reason: str) -> None:
    entry_price = state["entry_price"]
    amount_mnt  = state["entry_amount"]
    pnl_pct     = (price - entry_price) / entry_price * 100

    logger.info(f"[POSITION] EXIT reason={reason} price=${price:.4f} pnl={pnl_pct:+.2f}%")
    try:
        # Sell WMNT → USDT (no wrap; WMNT already held from entry)
        tx = mx.execute_swap_wmnt_to_usdt(amount_mnt)
    except Exception as e:
        logger.error(f"[POSITION] exit_long swap failed: {e}")
        return

    record = {
        "entry_time":  state["entry_time"],
        "entry_price": entry_price,
        "exit_time":   datetime.now(timezone.utc).isoformat(),
        "exit_price":  price,
        "pnl_pct":     round(pnl_pct, 4),
        "reason":      reason,
        "tx_entry":    state["tx_entry"],
        "tx_exit":     tx,
    }
    _save_trade(record)
    logger.info(f"[POSITION] trade saved: pnl={pnl_pct:+.2f}% tx={tx}")

    state["status"]       = "FLAT"
    state["entry_price"]  = None
    state["entry_time"]   = None
    state["entry_amount"] = None
    state["tx_entry"]     = None


def run_monitor(balance: float = BALANCE) -> None:
    logger.info(f"[MONITOR] starting — interval={MONITOR_INTERVAL}s balance=${balance:.2f}")

    while True:
        try:
            price = _get_mnt_price()
            logger.info(f"[MONITOR] MNT/USDT=${price:.4f} state={state['status']}")

            if state["status"] == "FLAT":
                result   = run_analysis(symbol="BTC", balance=balance)
                phase4   = result["phase4"]
                phase5   = result["phase5"]
                decision = phase4["decision"]
                logger.info(f"[MONITOR] analysis decision={decision} score={phase4['total_score']:.3f}")

                if decision == "ENTER_LONG":
                    size_mnt = phase5.get("size") or 0.0
                    if size_mnt > 0:
                        enter_long(price, size_mnt)
                    else:
                        logger.info("[MONITOR] ENTER_LONG skipped: size=0")
                else:
                    logger.info(f"[MONITOR] FLAT — holding ({decision})")

            elif state["status"] == "LONG":
                entry = state["entry_price"]
                tp    = entry * TP_RATIO
                sl    = entry * SL_RATIO

                if price >= tp:
                    exit_long(price, "TP")
                elif price <= sl:
                    exit_long(price, "SL")
                else:
                    logger.info(
                        f"[MONITOR] LONG holding — entry=${entry:.4f} "
                        f"tp=${tp:.4f} sl=${sl:.4f} current=${price:.4f}"
                    )

        except Exception as e:
            logger.error(f"[MONITOR] error: {e}")

        time.sleep(MONITOR_INTERVAL)


if __name__ == "__main__":
    bal = float(os.getenv("BALANCE", str(BALANCE)))
    run_monitor(balance=bal)
