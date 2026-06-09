# CLAUDE.md
elfa_grvt_bot の実装状況メモ。session開始時にここを読んで現状を把握すること。

## 実装済み

- `elfa_grvt_bot/grvt_client.py`: SL発注バグ修正済み
- `analysis/phase1_regime.py`: 市場レジーム判定（TREND_UP/DOWN/RANGE/HIGH_VOL）
- `analysis/phase2_fundamentals.py`: 需給スコアリング（funding/OI/netflow）
- `analysis/phase3_technical.py`: テクニカルスコアリング（4グループ）
- `analysis/phase4_entry.py`: 3フェーズ統合判定（ENTER_LONG/SHORT/HOLD）
- `analysis/phase5_sizing.py`: SL/TP/ポジションサイズ計算（ATR×1.5/3.0、1%リスク）
- `analysis/phase5_sizing.py`: 最小サイズ保証追加（balance≥$10時に0.001BTC保証）
- `analysis/main_analysis.py`: 全フェーズ統合ランナー（絵文字サマリー付き）
- `webhook_server.py`: Elfa Auto Webhook受信 → 分析 → Mantleスワップ（FastAPI, port 8000）
- `webhook_server.py`: 起動時にGRVT残高APIで balance を自動取得（mm_bot_v6.get_account_data使用）
- `webhook_server.py`: ENTER_LONG → wrap_mnt→approve_token→execute_swap (MNT→USDT) に変更
- `webhook_server.py`: ENTER_SHORT → HOLD扱い（未実装）
- `webhook_server.py`: /test_order ドライランエンドポイント（ENTER_LONG強制、size_mnt=0.001確認済み）
- `mantle_executor.py`: Fluxion V3経由MNT→USDTスワップ（wrap/approve/swap、gasLimit=300000固定）
- `transfer_mnt.py`: Privy API経由でMantleネットワーク上のMNT送金

## 起動方法

```bash
# 分析のみ手動実行
venv/Scripts/python.exe analysis/main_analysis.py

# Webhookサーバー起動（Elfa Auto連携）
venv/Scripts/python.exe webhook_server.py
```

## 次のタスク

- [ ] Elfaトリガー発火時のペイロード形式を実際のログで確認する
- [x] BALANCE定数を口座残高APIで自動更新する（lifespan + 注文後再取得）
- [x] /test_orderドライランテストで発注フロー確認（ENTER_LONG強制、size_mnt=0.001確認済み）
- [x] ENTER_LONG時にGRVTではなくMantleスワップ（mantle_executor経由）に切り替え
- [ ] ENTER_SHORT実装（MNT確保のためUSDT→MNT逆スワップ、または別手段）
- [ ] netflow_score実装（phase2_fundamentals.pyのTODO）
- [ ] ペーパートレード100回実施後に本番運用
- [ ] ngrok URLが変わった場合: setup_elfa_trigger.pyを再実行する
- [ ] Elfaトリガー有効期限（7日）が切れたら再登録する（期限: 2026-06-15）

## Elfa トリガー情報

- query_id: bd734071-0ca1-4944-bf9d-c8041f8768e5
- 条件: BTC 4H RSI <= 40 かつ 価格 < EMA50
- Webhook: https://cystic-unreplevined-lucinda.ngrok-free.dev/webhook
- 有効期限: 7日間（登録日: 2026-06-08）
- 再登録コマンド: venv/Scripts/python.exe setup_elfa_trigger.py

## 設計メモ

- データソース: Binance Futures API（scorer.py経由）
- Elfa: TAスナップショット不可→Webhookトリガー専用
- GRVT: 残高取得のみ（grvt_client.py）。注文執行はMantle経由に変更済み
- Mantle: Fluxion V3スワップで執行（mantle_executor.py）。gasLimit=300000固定（API値114096では不足）
- スワップtokenIn=WMNT(0x78c1b0...)、tokenOut=USDT0(0x779Ded...)、fee=3000、Router=0x5628a5...
- Python venv: venv/Scripts/python.exe
- Windows環境: bashコマンド不可、PowerShellを使う
- クールダウン: 同一シンボル5分以内の重複トリガー無視
- SL/TP: ATR×1.5（SL距離）、ATR×3.0（TP距離）、RR比1:2
- ポジションサイズ: 残高×1%リスク÷SL距離、最大レバ10%上限
