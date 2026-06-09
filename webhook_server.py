"""
Webhook server: receives Elfa Auto trigger notifications, runs the Phase1-5
analysis pipeline, and executes Mantle swaps via mantle_executor.
  ENTER_LONG  → wrap_mnt → approve_token → execute_swap (MNT→USDT)
  ENTER_SHORT → HOLD (未実装)
"""
import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
import uvicorn

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from analysis.main_analysis import run_analysis
from analysis.phase5_sizing import calculate_sizing
from elfa_grvt_bot.grvt_client import GrvtClient
from mm_bot_v6 import get_account_data
import mantle_executor as mx

load_dotenv(THIS_DIR / ".env")

# --- 設定値 ------------------------------------------------------------------
SYMBOL       = "BTC_USDT_Perp"
RISK_PCT     = 0.01
COOLDOWN_SEC = 300
PORT         = 8000

GRVT_TRADING_API_KEY     = os.getenv("GRVT_TRADING_API_KEY")
GRVT_TRADING_PRIVATE_KEY = os.getenv("GRVT_TRADING_PRIVATE_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("webhook_server")

# --- グローバル残高 -----------------------------------------------------------
balance: float = 700.0


async def _fetch_and_update_balance() -> bool:
    """GRVTにログインして残高を取得し、グローバル balance を更新する。"""
    global balance
    try:
        async with GrvtClient(GRVT_TRADING_API_KEY, GRVT_TRADING_PRIVATE_KEY) as grvt:
            await grvt.login()
            data = await get_account_data(grvt)
            equity = data.get("total_equity")
            if equity is not None:
                balance = float(equity)
                logger.info(f"[BALANCE] fetched balance: ${balance:.2f}")
                return True
            logger.warning("[BALANCE] WARNING: failed to fetch balance, using default $700.0 (total_equity missing)")
    except Exception as e:
        logger.warning(f"[BALANCE] WARNING: failed to fetch balance, using default $700.0 ({e})")
    return False


async def _run_long(amount_mnt: float) -> str:
    """wrap_mnt → approve_token → execute_swap を非同期で実行してtx hashを返す。"""
    loop = asyncio.get_event_loop()
    logger.info(f"[LONG] wrap {amount_mnt} MNT → WMNT")
    await loop.run_in_executor(None, mx.wrap_mnt, amount_mnt)
    logger.info("[LONG] approve WMNT → Router")
    await loop.run_in_executor(None, mx.approve_token)
    logger.info(f"[LONG] execute_swap {amount_mnt} WMNT → USDT")
    tx_hash = await loop.run_in_executor(None, mx.execute_swap, amount_mnt)
    return tx_hash


async def _run_short(amount_usdt: float) -> str:
    """approve_usdt → execute_swap_usdt_to_mnt を非同期で実行してtx hashを返す。"""
    loop = asyncio.get_event_loop()
    logger.info(f"[SHORT] execute_short {amount_usdt} USDT → WMNT")
    tx_hash = await loop.run_in_executor(None, mx.execute_short, amount_usdt)
    return tx_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _fetch_and_update_balance()
    yield


app = FastAPI(lifespan=lifespan)

_last_trigger: Dict[str, float] = {}


class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    symbol:    Optional[str]   = None
    trigger:   Optional[str]   = None
    value:     Optional[float] = None
    timestamp: Optional[str]   = None


def _cooldown_remaining(symbol: str) -> Optional[float]:
    last = _last_trigger.get(symbol)
    if last is None:
        return None
    elapsed = time.monotonic() - last
    if elapsed < COOLDOWN_SEC:
        return COOLDOWN_SEC - elapsed
    return None


@app.post("/webhook")
async def webhook(payload: WebhookPayload):
    logger.info(f"[WEBHOOK] received payload: {payload.model_dump()}")

    symbol = (payload.symbol or "BTC").upper()

    remaining = _cooldown_remaining(symbol)
    if remaining is not None:
        reason = f"cooldown active for {symbol} ({remaining:.0f}s remaining)"
        logger.info(f"[WEBHOOK] skipped: {reason}")
        return {"status": "skipped", "decision": None, "reason": reason}

    _last_trigger[symbol] = time.monotonic()

    logger.info(f"[ANALYSIS] running Phase1-5 for {symbol} (balance={balance}, risk_pct={RISK_PCT})")
    result   = run_analysis(symbol=symbol, balance=balance)
    phase4   = result["phase4"]
    phase5   = result["phase5"]
    decision = phase4["decision"]
    logger.info(f"[ANALYSIS] decision={decision} total_score={phase4['total_score']} "
                f"reason={phase4['reason']}")

    if decision == "HOLD":
        return {"status": "hold", "decision": decision, "reason": phase4["reason"]}

    if decision == "ENTER_LONG":
        size_mnt = phase5.get("size") or 0.0
        if size_mnt <= 0:
            reason = "computed size is zero - swap skipped"
            logger.info(f"[ORDER] skipped: {reason}")
            return {"status": "skipped", "decision": decision, "reason": reason}
        logger.info(f"[ORDER] ENTER_LONG → Mantle swap {size_mnt} MNT→USDT "
                    f"(entry={phase5.get('entry_price')} sl={phase5.get('sl_price')} tp={phase5.get('tp_price')})")
        try:
            tx_hash = await _run_long(size_mnt)
            logger.info(f"[ORDER] long swap placed: tx={tx_hash}")
            return {
                "status":   "ok",
                "decision": decision,
                "tx_hash":  tx_hash,
                "size_mnt": size_mnt,
                "explorer": f"https://explorer.mantle.xyz/tx/{tx_hash}",
                "reason":   f"ENTER_LONG swap {size_mnt} MNT→USDT",
            }
        except Exception as e:
            logger.error(f"[ORDER] long swap failed: {e}")
            return {"status": "error", "decision": decision, "reason": f"swap failed: {e}"}

    # ENTER_SHORT: USDT→WMNT スワップ（risk_amount USDT分）
    size_usdt = phase5.get("risk_amount") or 3.83
    logger.info(f"[ORDER] ENTER_SHORT → Mantle swap {size_usdt} USDT→WMNT "
                f"(entry={phase5.get('entry_price')} sl={phase5.get('sl_price')} tp={phase5.get('tp_price')})")
    try:
        tx_hash = await _run_short(size_usdt)
        logger.info(f"[ORDER] short swap placed: tx={tx_hash}")
        return {
            "status":     "ok",
            "decision":   decision,
            "tx_hash":    tx_hash,
            "size_usdt":  size_usdt,
            "explorer":   f"https://explorer.mantle.xyz/tx/{tx_hash}",
            "reason":     f"ENTER_SHORT swap {size_usdt} USDT→WMNT",
        }
    except Exception as e:
        logger.error(f"[ORDER] short swap failed: {e}")
        return {"status": "error", "decision": decision, "reason": f"swap failed: {e}"}


class TestOrderBody(BaseModel):
    mode: str = "long"  # "long" or "short"


@app.post("/test_order")
async def test_order(body: TestOrderBody = TestOrderBody()):
    """ENTER_LONG / ENTER_SHORT を強制シミュレート。実注文は一切行わない (dry_run=True)。
    Body: {"mode": "long"} または {"mode": "short"}
    """
    mode = body.mode.lower()
    logger.info(f"[TEST] dry-run test_order triggered (mode={mode})")

    result         = run_analysis(symbol="BTC", balance=balance)
    phase1, phase3 = result["phase1"], result["phase3"]

    price = phase3.get("price")
    atr   = phase1.get("atr")
    if price is None or price <= 0 or atr is None or atr <= 0:
        return {"error": f"could not fetch live price/ATR (price={price}, atr={atr})"}

    if mode == "short":
        mock_phase4 = {"decision": "ENTER_SHORT", "regime": phase1.get("regime")}
        phase5      = calculate_sizing(mock_phase4, price=price, balance=balance, atr=atr, risk_pct=RISK_PCT)
        size_usdt   = phase5["risk_amount"]
        logger.info(
            f"[TEST] DRY-RUN: would swap {size_usdt} USDT→WMNT on Mantle "
            f"entry={price:.1f} sl={phase5['sl_price']} tp={phase5['tp_price']}"
        )
        return {
            "dry_run":    True,
            "decision":   "ENTER_SHORT",
            "entry_price": phase5["entry_price"],
            "sl_price":   phase5["sl_price"],
            "tp_price":   phase5["tp_price"],
            "size_usdt":  size_usdt,
            "balance":    balance,
            "swap_flow":  "approve_usdt → execute_swap_usdt_to_mnt (USDT→WMNT)",
            "message":    "dry-run only, no real swap executed",
        }

    # mode == "long" (default)
    mock_phase4 = {"decision": "ENTER_LONG", "regime": phase1.get("regime")}
    phase5      = calculate_sizing(mock_phase4, price=price, balance=balance, atr=atr, risk_pct=RISK_PCT)
    size_mnt    = phase5["size"]
    logger.info(
        f"[TEST] DRY-RUN: would swap {size_mnt} MNT→USDT on Mantle "
        f"entry={price:.1f} sl={phase5['sl_price']} tp={phase5['tp_price']}"
    )
    return {
        "dry_run":    True,
        "decision":   "ENTER_LONG",
        "entry_price": phase5["entry_price"],
        "sl_price":   phase5["sl_price"],
        "tp_price":   phase5["tp_price"],
        "size_mnt":   size_mnt,
        "balance":    balance,
        "swap_flow":  "wrap_mnt → approve_token → execute_swap (MNT→USDT)",
        "message":    "dry-run only, no real swap executed",
    }


if __name__ == "__main__":
    logger.info(f"[WEBHOOK] starting server on port {PORT} "
                f"(symbol={SYMBOL}, cooldown={COOLDOWN_SEC}s)")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
