# CLAUDE.md
elfa_grvt_bot の実装状況メモ。session開始時にここを読んで現状を把握すること。

## 実装済み

- `analysis/phase1_regime.py`: 市場レジーム判定（TREND_UP/DOWN/RANGE/HIGH_VOL）
- `analysis/phase2_fundamentals.py`: 需給スコアリング（funding/OI/netflow）
- `analysis/phase3_technical.py`: テクニカルスコアリング（4グループ）
- `analysis/phase4_entry.py`: 3フェーズ統合判定（ENTER_LONG/SHORT/HOLD）
- `analysis/phase5_sizing.py`: SL/TP/ポジションサイズ計算（ATR×1.5/3.0、1%リスク、0.001BTC最小保証）
- `analysis/main_analysis.py`: 全フェーズ統合ランナー（絵文字サマリー付き）
- `analysis/position_manager.py`: MNT価格監視・自動売買ループ（TP+0.5%/SL-0.3%、10秒間隔）
- `mantle_executor.py`: Fluxion DEX スワップ実行（MNT↔USDT）、get_balances()、execute_swap_wmnt_to_usdt()
- `webhook_server.py`: Elfa Webhook受信・ダッシュボード（GET /）・残高自動取得・/position /trades /balances /analyze エンドポイント
- `trades.json`: トレード履歴（exit_long()成功時に自動生成）
- `analysis/position_state.json`: ポジション状態（10秒ごとに自動保存）

## 起動方法

```bash
# Webhookサーバー＋ダッシュボード（port 8000）
venv/Scripts/python.exe webhook_server.py

# 自動売買ループ（MNT価格監視）
venv/Scripts/python.exe analysis/position_manager.py

# ngrok外部公開
ngrok http 8000

# 分析のみ手動実行
venv/Scripts/python.exe analysis/main_analysis.py
```

## APIエンドポイント

| エンドポイント | 説明 |
|---|---|
| GET / | ダッシュボードHTML |
| GET /analyze | Phase1-5分析実行、JSON返却 |
| GET /position | position_state.json の内容 |
| GET /trades | trades.json の内容 |
| GET /balances | Mantleウォレット残高（キャッシュ、30秒更新） |
| POST /webhook | Elfa Auto トリガー受信 |
| POST /test_order | ドライランテスト（mode="long"/"short"） |

## 設計メモ

- MNT価格取得: Bybit API (MNTUSDT)
- BTC分析データ: Binance Futures API
- DEX: Fluxion V3 on Mantle (chainId 5000)
- TP: entry × 1.005 (+0.5%)
- SL: entry × 0.997 (-0.3%)
- 監視間隔: 10秒
- ウォレット: 0xbF59f8fbF2dC60e0D2c179bdECcFE425C8528266
- gasLimit: max(api_gas × 3, 300000)固定（QuoterV2のgasEstimateはcallback分を含まないため）
- WMNT: 0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8
- USDT0: 0x779Ded0c9e1022225f8E0630b35a9b54bE713736
- Router: 0x5628a59dF0ECAC3f3171f877A94bEb26BA6DFAa0
- Python venv: venv/Scripts/python.exe（Windows環境）

## Elfa トリガー情報

- query_id: bd734071-0ca1-4944-bf9d-c8041f8768e5
- 条件: BTC 4H RSI <= 40 かつ 価格 < EMA50
- Webhook: https://cystic-unreplevined-lucinda.ngrok-free.dev/webhook
- 有効期限: 7日間（登録日: 2026-06-08、期限: 2026-06-15）
- 再登録コマンド: venv/Scripts/python.exe setup_elfa_trigger.py

## ハッカソン情報

- イベント: Turing Test Hackathon 2026（AI Trading & Strategyトラック）
- DoraHacks: https://dorahacks.io
- GitHub: https://github.com/noboru59631/elfaquant
- 締切: 2026-06-16 06:59
- 実績TX: 0x615e0fb0798ced3cbafdab6b8a1356767b12c69d472fb277b48c18c713ac7294

## 次のタスク

- [ ] Elfaトリガー有効期限（2026-06-15）が切れたら再登録する
- [ ] ペーパートレード100回実施後に本番運用
- [ ] Elfaトリガー発火時のペイロード形式を実際のログで確認する
- [ ] netflow_score実装（phase2_fundamentals.pyのTODO）
- [ ] ngrok URLが変わった場合: setup_elfa_trigger.pyを再実行する
