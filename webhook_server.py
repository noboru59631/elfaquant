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

import json

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
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


async def _balance_refresh_loop() -> None:
    while True:
        await _refresh_balances_cache()
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _fetch_and_update_balance()
    await _refresh_balances_cache()
    asyncio.create_task(_balance_refresh_loop())
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


TRADES_FILE = THIS_DIR / "trades.json"
STATE_FILE  = THIS_DIR / "analysis" / "position_state.json"

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ElfaQuant Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;min-height:100vh;padding:28px 24px}
h1{color:#ff6b00;font-size:1.9rem;letter-spacing:2px;margin-bottom:2px}
.sub{color:#555;font-size:.82rem;margin-bottom:4px}
.ticker{color:#ff6b00;font-size:.75rem;text-align:right;margin-bottom:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.card{background:#111;border:1px solid #222;border-radius:8px;padding:20px;margin-bottom:16px}
.card.long-active{border-color:#00c853;box-shadow:0 0 12px #00c85322}
.card h2{color:#ff6b00;font-size:.88rem;letter-spacing:1px;margin-bottom:14px;border-bottom:1px solid #1e1e1e;padding-bottom:8px}
.row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #161616;font-size:.88rem}
.row:last-child{border-bottom:none}
.lbl{color:#777}
.val{color:#e0e0e0;font-weight:bold}
.flat{color:#555;text-align:center;padding:10px 0;font-size:1rem}
.long-badge{color:#00c853;font-weight:bold}
.pnl-pos{color:#00c853}
.pnl-neg{color:#ff1744}
.btn{background:#ff6b00;color:#000;border:none;padding:10px 26px;font-size:.95rem;font-family:'Courier New',monospace;font-weight:bold;cursor:pointer;border-radius:4px;letter-spacing:1px;transition:background .2s}
.btn:hover{background:#ff8c33}
.btn:disabled{background:#444;color:#888;cursor:not-allowed}
.arow{display:flex;align-items:center;gap:16px;margin-bottom:12px}
.ast{color:#666;font-size:.85rem}
.regime-badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.78rem;font-weight:bold}
.regime-TREND_UP{background:#003322;color:#00c853}
.regime-TREND_DOWN{background:#330011;color:#ff1744}
.regime-RANGE{background:#1a1a00;color:#ffd600}
.regime-HIGH_VOL{background:#1a001a;color:#e040fb}
.dec-LONG{color:#00c853}
.dec-SHORT{color:#ff1744}
.dec-HOLD{color:#888}
.chart-wrap{position:relative;height:200px}
.no-trades{color:#444;text-align:center;padding:60px 0;font-size:.9rem;position:absolute;top:0;left:0;right:0}
.divider{border:none;border-top:1px solid #1a1a1a;margin:20px 0}
.tx-box{background:#0d0d0d;border:1px solid #1e1e1e;border-radius:4px;padding:10px 14px;font-size:.76rem;margin-bottom:14px}
.tx-box a{color:#ff6b00;text-decoration:none;word-break:break-all}
.links{display:flex;gap:12px;flex-wrap:wrap}
.link-btn{background:transparent;color:#ff6b00;border:1px solid #ff6b00;padding:7px 18px;border-radius:4px;text-decoration:none;font-family:'Courier New',monospace;font-size:.82rem;transition:background .2s,color .2s}
.link-btn:hover{background:#ff6b00;color:#000}
</style>
</head>
<body>

<h1>&#9889; ElfaQuant</h1>
<p class="sub">AI-Powered DeFi Trading Agent on Mantle Network</p>
<p class="ticker" id="ticker">MNT price loading...</p>

<div class="grid">
  <div class="card" id="posCard">
    <h2>&#128205; CURRENT POSITION</h2>
    <div id="posBody"><div class="flat">- FLAT  waiting -</div></div>
  </div>
  <div class="card">
    <h2>&#128176; WALLET BALANCE (Mantle)</h2>
    <div class="row"><span class="lbl">MNT</span><span class="val" id="bMnt">loading...</span></div>
    <div class="row"><span class="lbl">USDT</span><span class="val" id="bUsdt">loading...</span></div>
    <div class="row"><span class="lbl">Total (USDT est.)</span><span class="val" id="bTotal">loading...</span></div>
  </div>
</div>

<div class="card">
  <h2>&#128269; LIVE ANALYSIS</h2>
  <div class="arow">
    <button class="btn" id="analyzeBtn" onclick="runAnalyze()">&#128269; Analyze Now</button>
    <span class="ast" id="analyzeStatus">Click to run Phase1-5 pipeline</span>
  </div>
  <div id="analyzeResult" style="display:none">
    <div class="row"><span class="lbl">Market Regime</span><span class="val" id="regime">-</span></div>
    <div class="row"><span class="lbl">Technical Score</span><span class="val" id="techScore">-</span></div>
    <div class="row"><span class="lbl">Decision</span><span class="val" id="decision">-</span></div>
    <div class="row"><span class="lbl">Entry / SL / TP</span><span class="val" id="entrySlTp">-</span></div>
    <div class="row"><span class="lbl">Size</span><span class="val" id="size">-</span></div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>&#128197; DAILY P&amp;L (%)</h2>
    <div class="chart-wrap">
      <canvas id="dailyChart"></canvas>
      <div class="no-trades" id="noDaily">No trades yet</div>
    </div>
  </div>
  <div class="card">
    <h2>&#128200; CUMULATIVE P&amp;L (%)</h2>
    <div class="chart-wrap">
      <canvas id="cumChart"></canvas>
      <div class="no-trades" id="noCum">No trades yet</div>
    </div>
  </div>
</div>

<hr class="divider">
<h2 style="color:#ff6b00;font-size:.88rem;letter-spacing:1px;margin-bottom:8px">&#128279; ON-CHAIN PROOF</h2>
<div class="tx-box">
  Live swap &middot; Mantle Mainnet &middot; WMNT &#8594; USDT via Fluxion V3<br><br>
  <a href="https://explorer.mantle.xyz/tx/615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294" target="_blank">
    0x615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294
  </a>
</div>
<div class="links">
  <a class="link-btn" href="https://github.com/noboru59631/elfaquant" target="_blank">GitHub</a>
  <a class="link-btn" href="/docs" target="_blank">API Docs</a>
</div>

<script>
var dailyChart = null;
var cumChart   = null;

var chartOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#666', font: { family: 'Courier New', size: 10 } }, grid: { color: '#1a1a1a' } },
    y: { ticks: { color: '#666', font: { family: 'Courier New', size: 10 } }, grid: { color: '#1a1a1a' } }
  }
};

function updatePosition() {
  fetch('/position').then(function(r){ return r.json(); }).then(function(s) {
    var card = document.getElementById('posCard');
    var body = document.getElementById('posBody');
    if (s.status === 'LONG' && s.entry_price) {
      var cur = s.current_price || s.entry_price;
      var pnl = (cur - s.entry_price) / s.entry_price * 100;
      var tp  = s.entry_price * 1.005;
      var sl  = s.entry_price * 0.997;
      var pc  = pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
      var sign = pnl >= 0 ? '+' : '';
      card.classList.add('long-active');
      body.innerHTML =
        '<div class="row"><span class="lbl">Status</span><span class="long-badge">LONG</span></div>' +
        '<div class="row"><span class="lbl">Entry</span><span class="val">$' + s.entry_price.toFixed(4) + '</span></div>' +
        '<div class="row"><span class="lbl">Current</span><span class="val">$' + cur.toFixed(4) + '</span></div>' +
        '<div class="row"><span class="lbl">P&L</span><span class="val ' + pc + '">' + sign + pnl.toFixed(2) + '%</span></div>' +
        '<div class="row"><span class="lbl">TP / SL</span><span class="val">$' + tp.toFixed(4) + ' / $' + sl.toFixed(4) + '</span></div>' +
        '<div class="row"><span class="lbl">Amount</span><span class="val">' + (s.entry_amount || '-') + ' MNT</span></div>';
      document.getElementById('ticker').textContent = 'MNT $' + cur.toFixed(4) + '  updated ' + new Date().toLocaleTimeString();
    } else {
      card.classList.remove('long-active');
      body.innerHTML = '<div class="flat">- FLAT  waiting -</div>';
      if (s.current_price) {
        document.getElementById('ticker').textContent = 'MNT $' + s.current_price.toFixed(4) + '  updated ' + new Date().toLocaleTimeString();
      }
    }
  }).catch(function(){});
}

function updateBalance() {
  fetch('/balances').then(function(r){ return r.json(); }).then(function(b) {
    document.getElementById('bMnt').textContent  = b.mnt  != null ? b.mnt.toFixed(4)  + ' MNT'  : '-';
    document.getElementById('bUsdt').textContent = b.usdt != null ? b.usdt.toFixed(4) + ' USDT' : '-';
    var total = (b.usdt || 0) + (b.mnt || 0) * (b.mnt_price || 0);
    document.getElementById('bTotal').textContent = total > 0 ? '$' + total.toFixed(2) : '-';
    if (b.mnt_price) {
      document.getElementById('ticker').textContent = 'MNT $' + parseFloat(b.mnt_price).toFixed(4) + '  updated ' + new Date().toLocaleTimeString();
    }
  }).catch(function(){
    document.getElementById('bMnt').textContent  = 'error';
    document.getElementById('bUsdt').textContent = 'error';
    document.getElementById('bTotal').textContent = 'error';
  });
}

function updateCharts() {
  fetch('/trades').then(function(r){ return r.json(); }).then(function(trades) {
    if (!trades || trades.length === 0) {
      document.getElementById('noDaily').style.display = 'block';
      document.getElementById('noCum').style.display   = 'block';
      if (dailyChart) { dailyChart.destroy(); dailyChart = null; }
      if (cumChart)   { cumChart.destroy();   cumChart   = null; }
      return;
    }
    document.getElementById('noDaily').style.display = 'none';
    document.getElementById('noCum').style.display   = 'none';

    var dailyMap = {};
    trades.forEach(function(t) {
      var day = (t.exit_time || '').slice(0, 10);
      if (day) dailyMap[day] = (dailyMap[day] || 0) + (t.pnl_pct || 0);
    });
    var days     = Object.keys(dailyMap).sort();
    var dayVals  = days.map(function(d){ return parseFloat(dailyMap[d].toFixed(2)); });
    var dayColors = dayVals.map(function(v){ return v >= 0 ? '#00c853' : '#ff1744'; });
    if (dailyChart) dailyChart.destroy();
    dailyChart = new Chart(document.getElementById('dailyChart'), {
      type: 'bar',
      data: { labels: days, datasets: [{ data: dayVals, backgroundColor: dayColors, borderRadius: 3 }] },
      options: chartOpts
    });

    var cum = 0, cumLabels = [], cumVals = [];
    trades.forEach(function(t, i) {
      cum += t.pnl_pct || 0;
      cumLabels.push('#' + (i + 1));
      cumVals.push(parseFloat(cum.toFixed(3)));
    });
    var cc = cum >= 0 ? '#00c853' : '#ff1744';
    if (cumChart) cumChart.destroy();
    cumChart = new Chart(document.getElementById('cumChart'), {
      type: 'line',
      data: { labels: cumLabels, datasets: [{ data: cumVals, borderColor: cc, backgroundColor: cc + '22', fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: cc }] },
      options: chartOpts
    });
  }).catch(function(){});
}

function runAnalyze() {
  var btn = document.getElementById('analyzeBtn');
  var st  = document.getElementById('analyzeStatus');
  var res = document.getElementById('analyzeResult');
  btn.disabled = true;
  btn.textContent = 'Analyzing...';
  st.textContent  = 'Running Phase1-5 pipeline...';
  res.style.display = 'none';
  fetch('/analyze').then(function(r){ return r.json(); }).then(function(d) {
    var regime   = (d.phase1 && d.phase1.regime)   || '-';
    var score    = d.phase3  && d.phase3.total_score;
    var decision = (d.phase4 && d.phase4.decision)  || '-';
    var p5       = d.phase5 || {};
    var dc = decision.indexOf('LONG') >= 0 ? 'LONG' : decision.indexOf('SHORT') >= 0 ? 'SHORT' : 'HOLD';
    document.getElementById('regime').innerHTML    = '<span class="regime-badge regime-' + regime + '">' + regime + '</span>';
    document.getElementById('techScore').textContent = score != null ? score.toFixed(3) : '-';
    document.getElementById('decision').innerHTML  = '<span class="dec-' + dc + '">' + decision + '</span>';
    document.getElementById('entrySlTp').textContent = p5.entry_price
      ? '$' + p5.entry_price.toLocaleString() + ' / $' + (p5.sl_price||0).toLocaleString() + ' / $' + (p5.tp_price||0).toLocaleString()
      : '-';
    document.getElementById('size').textContent = p5.size != null ? p5.size + ' BTC' : '-';
    res.style.display = 'block';
    st.textContent = 'Done - ' + new Date().toLocaleTimeString();
  }).catch(function(e){
    st.textContent = 'Error: ' + e.message;
  }).finally(function(){
    btn.disabled = false;
    btn.textContent = 'Analyze Now';
  });
}

function refreshAll() { updatePosition(); updateBalance(); updateCharts(); }

// 起動時
refreshAll();
runAnalyze();

// 10秒ごと: 残高・ポジション・チャート更新
setInterval(refreshAll, 10000);

// 60秒ごと: 分析も実行
setInterval(runAnalyze, 60000);
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
    return {
        "phase1":  result["phase1"],
        "phase2":  result["phase2"],
        "phase3":  result["phase3"],
        "phase4":  phase4,
        "phase5":  phase5,
        "balance": balance,
    }


@app.get("/position")
async def get_position():
    if STATE_FILE.exists():
        return JSONResponse(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return JSONResponse({"status": "FLAT"})


@app.get("/trades")
async def get_trades():
    if TRADES_FILE.exists():
        return JSONResponse(json.loads(TRADES_FILE.read_text(encoding="utf-8")))
    return JSONResponse([])


_cached_balances: dict = {"mnt": None, "usdt": None, "mnt_price": None}


async def _refresh_balances_cache() -> None:
    import requests as _req
    global _cached_balances
    loop = asyncio.get_event_loop()
    try:
        mnt, usdt = await loop.run_in_executor(None, mx.get_balances)
        price_str = await loop.run_in_executor(
            None, lambda: _req.get(
                "https://api.bybit.com/v5/market/tickers?category=spot&symbol=MNTUSDT", timeout=5
            ).json()["result"]["list"][0]["lastPrice"]
        )
        _cached_balances = {"mnt": mnt, "usdt": usdt, "mnt_price": float(price_str)}
        logger.info(f"[BALANCES] cache refreshed: MNT={mnt:.4f} USDT={usdt:.4f} price={price_str}")
    except Exception as e:
        logger.warning(f"[BALANCES] refresh failed: {e}")


@app.get("/balances")
async def get_balances_endpoint():
    return JSONResponse(_cached_balances)


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
