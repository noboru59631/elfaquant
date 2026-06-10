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
from fastapi.responses import HTMLResponse
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


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ElfaQuant Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0a0a0a; color: #e0e0e0; font-family: 'Courier New', monospace; min-height: 100vh; padding: 32px 24px; }
  h1 { color: #ff6b00; font-size: 2rem; letter-spacing: 2px; margin-bottom: 4px; }
  .subtitle { color: #666; font-size: 0.85rem; margin-bottom: 32px; }
  .btn {
    background: #ff6b00; color: #000; border: none; padding: 12px 32px;
    font-size: 1rem; font-family: 'Courier New', monospace; font-weight: bold;
    cursor: pointer; border-radius: 4px; letter-spacing: 1px; transition: background 0.2s;
  }
  .btn:hover { background: #ff8c33; }
  .btn:disabled { background: #555; color: #999; cursor: not-allowed; }
  .status { margin-top: 16px; color: #888; font-size: 0.9rem; min-height: 24px; }
  .card {
    background: #111; border: 1px solid #222; border-radius: 8px;
    padding: 24px; margin-top: 24px; display: none;
  }
  .card.visible { display: block; }
  .card h2 { color: #ff6b00; font-size: 1rem; margin-bottom: 16px; letter-spacing: 1px; border-bottom: 1px solid #222; padding-bottom: 8px; }
  .row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1a1a1a; font-size: 0.9rem; }
  .row:last-child { border-bottom: none; }
  .label { color: #888; }
  .value { color: #e0e0e0; font-weight: bold; }
  .decision-LONG  { color: #00c853; font-size: 1.1rem; }
  .decision-SHORT { color: #ff1744; font-size: 1.1rem; }
  .decision-HOLD  { color: #888;    font-size: 1.1rem; }
  .regime-badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.8rem; font-weight: bold;
  }
  .regime-TREND_UP   { background: #003322; color: #00c853; }
  .regime-TREND_DOWN { background: #330011; color: #ff1744; }
  .regime-RANGE      { background: #1a1a00; color: #ffd600; }
  .regime-HIGH_VOL   { background: #1a001a; color: #e040fb; }
  .links { margin-top: 32px; display: flex; gap: 16px; flex-wrap: wrap; }
  .link-btn {
    background: transparent; color: #ff6b00; border: 1px solid #ff6b00;
    padding: 8px 20px; border-radius: 4px; text-decoration: none;
    font-family: 'Courier New', monospace; font-size: 0.85rem;
    transition: background 0.2s, color 0.2s;
  }
  .link-btn:hover { background: #ff6b00; color: #000; }
  .divider { border: none; border-top: 1px solid #1e1e1e; margin: 32px 0; }
  .tx-box { background: #0d0d0d; border: 1px solid #1e1e1e; border-radius: 4px; padding: 12px 16px; margin-top: 8px; font-size: 0.78rem; }
  .tx-box a { color: #ff6b00; text-decoration: none; word-break: break-all; }
  .tx-box a:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>⚡ ElfaQuant</h1>
<p class="subtitle">AI-Powered DeFi Trading Agent on Mantle Network</p>

<button class="btn" id="analyzeBtn" onclick="runAnalyze()">🔍 Analyze Now</button>
<p class="status" id="status"></p>

<div class="card" id="resultCard">
  <h2>📊 ANALYSIS RESULT</h2>
  <div class="row">
    <span class="label">Market Regime</span>
    <span class="value" id="regime">—</span>
  </div>
  <div class="row">
    <span class="label">Technical Score</span>
    <span class="value" id="techScore">—</span>
  </div>
  <div class="row">
    <span class="label">Decision</span>
    <span class="value" id="decision">—</span>
  </div>
  <div class="row">
    <span class="label">Entry Price</span>
    <span class="value" id="entry">—</span>
  </div>
  <div class="row">
    <span class="label">Stop-Loss</span>
    <span class="value" id="sl">—</span>
  </div>
  <div class="row">
    <span class="label">Take-Profit</span>
    <span class="value" id="tp">—</span>
  </div>
  <div class="row">
    <span class="label">Position Size</span>
    <span class="value" id="size">—</span>
  </div>
  <div class="row">
    <span class="label">Balance</span>
    <span class="value" id="bal">—</span>
  </div>
</div>

<hr class="divider">

<div>
  <h2 style="color:#ff6b00; font-size:0.95rem; letter-spacing:1px; margin-bottom:12px;">🔗 ON-CHAIN PROOF</h2>
  <div class="tx-box">
    Live swap on Mantle Mainnet (WMNT → USDT via Fluxion V3):<br><br>
    <a href="https://explorer.mantle.xyz/tx/615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294" target="_blank">
      0x615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294
    </a>
  </div>
</div>

<div class="links">
  <a class="link-btn" href="https://github.com/noboru59631/elfaquant" target="_blank">⌥ GitHub</a>
  <a class="link-btn" href="/docs" target="_blank">📄 API Docs</a>
</div>

<script>
async function runAnalyze() {
  const btn = document.getElementById('analyzeBtn');
  const status = document.getElementById('status');
  const card = document.getElementById('resultCard');
  btn.disabled = true;
  btn.textContent = '⏳ Analyzing...';
  status.textContent = 'Running 5-phase pipeline...';
  card.classList.remove('visible');
  try {
    const res = await fetch('/analyze');
    const d = await res.json();
    const regime = d.phase1?.regime ?? '—';
    const techScore = d.phase3?.total_score ?? '—';
    const decision = d.phase4?.decision ?? '—';
    const p5 = d.phase5 ?? {};
    document.getElementById('regime').innerHTML =
      '<span class="regime-badge regime-' + regime + '">' + regime + '</span>';
    document.getElementById('techScore').textContent =
      typeof techScore === 'number' ? techScore.toFixed(3) : techScore;
    const decClass = decision.includes('LONG') ? 'LONG' : decision.includes('SHORT') ? 'SHORT' : 'HOLD';
    document.getElementById('decision').innerHTML =
      '<span class="decision-' + decClass + '">' + decision + '</span>';
    document.getElementById('entry').textContent =
      p5.entry_price ? '$' + p5.entry_price.toLocaleString(undefined, {minimumFractionDigits:1}) : '—';
    document.getElementById('sl').textContent =
      p5.sl_price ? '$' + p5.sl_price.toLocaleString(undefined, {minimumFractionDigits:1}) : '—';
    document.getElementById('tp').textContent =
      p5.tp_price ? '$' + p5.tp_price.toLocaleString(undefined, {minimumFractionDigits:1}) : '—';
    document.getElementById('size').textContent =
      p5.size != null ? p5.size + ' BTC' : '—';
    document.getElementById('bal').textContent =
      d.balance != null ? '$' + parseFloat(d.balance).toLocaleString(undefined, {minimumFractionDigits:2}) : '—';
    card.classList.add('visible');
    status.textContent = '✅ Done — ' + new Date().toLocaleTimeString();
  } catch(e) {
    status.textContent = '❌ Error: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Analyze Now';
  }
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/analyze")
async def analyze():
    result = run_analysis(symbol="BTC", balance=balance)
    phase4 = result["phase4"]
    phase5 = result["phase5"]
    mock_phase4 = {"decision": phase4["decision"], "regime": result["phase1"].get("regime")}
    return {
        "phase1":  result["phase1"],
        "phase2":  result["phase2"],
        "phase3":  result["phase3"],
        "phase4":  phase4,
        "phase5":  phase5,
        "balance": balance,
    }


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
