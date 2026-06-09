# ElfaQuant - AI-Powered DeFi Trading Agent on Mantle

## Overview

ElfaQuant is a fully autonomous AI trading agent that combines **Elfa AI**, **Mantle Network**, and **Fluxion DEX** to execute data-driven DeFi trades without human intervention. It runs a 5-phase analysis pipeline — from market regime detection through position sizing — triggered automatically by Elfa Auto's condition engine. When a signal fires, the agent evaluates market conditions across multiple dimensions and executes a swap on Fluxion V3 DEX on Mantle Network if the entry criteria are met. The system is designed for low-latency, risk-aware execution with built-in cooldown protection and automatic balance tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ElfaQuant Flow                           │
└─────────────────────────────────────────────────────────────────┘

  Elfa Auto          Webhook Server         Analysis Pipeline
  ──────────         ──────────────         ─────────────────
  Condition   ──►   POST /webhook    ──►   Phase 1: Market Regime
  Engine              (FastAPI)             Phase 2: Fundamentals
  (RSI/EMA)                                 Phase 3: Technical
                                            Phase 4: Entry Decision
                                            Phase 5: Sizing (ATR)
                                                    │
                                                    ▼
                                     ┌──────────────────────────┐
                                     │   Decision: ENTER_LONG?  │
                                     └──────────────────────────┘
                                              │ YES
                                              ▼
                                     Mantle Network
                                     ─────────────
                                     wrap_mnt()
                                          │
                                     approve_token()
                                          │
                                     execute_swap()
                                     (Fluxion V3 DEX)
                                     MNT ──► USDT
```

## Features

- **Phase 1 — Market Regime Detection**: Classifies market into `TREND_UP`, `TREND_DOWN`, `RANGE`, or `HIGH_VOL` using EMA crossovers and ATR ratio analysis
- **Phase 2 — Fundamentals Scoring**: Evaluates funding rate, open interest change, and net flow to generate a bullish/bearish/neutral verdict
- **Phase 3 — Technical Scoring**: Scores 4 indicator groups (trend, momentum, price level, volume) using RSI, MACD, Bollinger Bands, and more
- **Phase 4 — Integrated Entry Decision**: Combines all phase scores to produce `ENTER_LONG`, `ENTER_SHORT`, or `HOLD`
- **Phase 5 — ATR-Based Position Sizing**: Calculates SL (ATR × 1.5), TP (ATR × 3.0), and position size capped at 1% account risk
- **Auto-triggered** by Elfa Auto condition engine (e.g., BTC 4H RSI ≤ 40 & Price < EMA50)
- **On-chain execution** via Fluxion V3 DEX on Mantle Network (WMNT → USDT)
- **Cooldown protection**: duplicate signals within 5 minutes per symbol are ignored
- **Auto balance fetch** from GRVT account at startup
- **Dry-run endpoint** (`POST /test_order`) for safe pre-flight checks

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Webhook Server | FastAPI + uvicorn |
| On-chain Execution | web3.py (Mantle transaction signing) |
| Condition Engine | Elfa Auto API |
| DEX | Fluxion V3 (Uniswap V3 fork on Mantle) |
| Market Data | Binance Futures API |
| Tunnel | ngrok (webhook exposure) |
| Balance Source | GRVT account summary API |

## Setup

### 1. Install dependencies

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # Windows
# or: venv/bin/pip install -r requirements.txt  # Linux/Mac
venv/Scripts/pip install web3 fastapi uvicorn python-dotenv requests
```

### 2. Configure `.env`

```env
# Elfa Auto
ELFA_API_KEY=your_elfa_api_key

# GRVT (balance tracking)
GRVT_TRADING_API_KEY=your_grvt_api_key
GRVT_TRADING_PRIVATE_KEY=0x...

# Mantle (swap execution)
MANTLE_PRIVATE_KEY=your_mantle_private_key_hex
MANTLE_WALLET_ADDRESS=0x...
MANTLE_RPC=https://rpc.mantle.xyz

# Privy (optional: server wallet)
PRIVY_APP_ID=your_privy_app_id
PRIVY_APP_SECRET=your_privy_app_secret
PRIVY_WALLET_ID=your_privy_wallet_id
```

### 3. Register Elfa Auto trigger

```bash
venv/Scripts/python.exe setup_elfa_trigger.py
```

This registers a webhook trigger with condition: **BTC 4H RSI ≤ 40 AND Price < EMA50**. The trigger expires after 7 days and must be re-registered.

## Usage

### Start the webhook server

```bash
venv/Scripts/python.exe webhook_server.py
```

Server starts on `http://0.0.0.0:8000`. At startup it fetches the current GRVT account balance automatically.

### Run analysis manually

```bash
venv/Scripts/python.exe analysis/main_analysis.py
```

### Test the order flow (dry-run, no real swap)

```bash
curl -X POST http://localhost:8000/test_order
```

Returns the computed entry price, SL, TP, and swap size without executing anything on-chain.

### Expose webhook via ngrok

```bash
ngrok http 8000
```

Update the Elfa trigger URL if the ngrok address changes:

```bash
venv/Scripts/python.exe setup_elfa_trigger.py
```

## Key Contract Addresses (Mantle Mainnet)

| Contract | Address |
|---|---|
| WMNT | `0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8` |
| USDT0 | `0x779Ded0c9e1022225f8E0630b35a9b54bE713736` |
| Fluxion Router | `0x5628a59dF0ECAC3f3171f877A94bEb26BA6DFAa0` |
| Fluxion Factory | `0xF883162Ed9c7E8EF604214c964c678E40c9B737C` |
| Fluxion QuoterV2 | `0x3E4eE18Ac7280813236a1EB850679Da5322E14CE` |

> **Note:** Fluxion's Quote API underestimates gas (excludes ~40k gas for the callback's `transferFrom`). ElfaQuant uses `gasLimit = max(api_gas × 3, 300_000)` to ensure reliable execution.

## Competition Track

**AI Trading & Strategy** — Turing Test Hackathon 2026

ElfaQuant demonstrates end-to-end AI-driven DeFi automation: a multi-phase scoring engine feeds real-time market signals from Elfa AI into on-chain swap execution on Mantle — fully autonomous, no human in the loop.

## 🎥 Live Demo

### Confirmed On-chain Transaction
- **Network**: Mantle Mainnet
- **Action**: MNT → USDT swap via Fluxion DEX
- **TX Hash**: `615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294`
- **Explorer**: https://explorer.mantle.xyz/tx/615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294

### Dry-run Results (2026-06-09)
| Mode | Entry | SL | TP | Size |
|------|-------|----|----|------|
| ENTER_LONG | $60,889 | $57,077 | $68,515 | 0.001 MNT |
| ENTER_SHORT | $60,863 | $64,672 | $53,244 | 3.83 USDT |

## License

MIT
