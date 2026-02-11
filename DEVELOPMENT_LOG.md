# ライトタワー監視システム - 開発進行状況

## プロジェクト概要

ESP32ベースのライトタワーゲートウェイシステムのリアルタイム監視Webアプリケーション。
MQTTプロトコルを使用してライトタワーの状態を収集し、リアルタイムダッシュボードで可視化します。

## 技術スタック

### バックエンド
- **Python 3.10+**
- **FastAPI** - Webフレームワーク
- **Uvicorn** - ASGIサーバー
- **SQLAlchemy** - ORM
- **SQLite** - データベース
- **Paho-MQTT** - MQTTクライアント
- **APScheduler** - タスクスケジューラー
- **Pytz** - タイムゾーン処理

### フロントエンド
- **Bootstrap 5** - UIフレームワーク
- **Chart.js** - グラフ表示
- **WebSocket** - リアルタイム通信

### ハードウェア
- **ESP32** - マイクロコントローラ
- **BLE** - センサーとの通信
- **WiFi** - MQTT通信

## ディレクトリ構造

```
kado/
├── app/                      # Webアプリケーション本体
│   ├── __init__.py
│   ├── main.py              # FastAPIメインアプリケーション
│   ├── database.py          # データベース接続設定
│   ├── models.py            # SQLAlchemyモデル定義
│   ├── mqtt_client.py       # MQTTクライアント実装
│   ├── device_config.py     # デバイス設定管理
│   ├── routers/             # APIルーター（将来の拡張用）
│   │   └── __init__.py
│   └── utils/               # ユーティリティ関数
│       ├── __init__.py
│       ├── validators.py    # バリデーション関数
│       └── status.py        # ステータス判定関数
│
├── static/                   # 静的ファイル
│   ├── css/                 # スタイルシート
│   └── js/                  # JavaScript
│
├── templates/                # HTMLテンプレート
│   └── index.html           # ダッシュボード画面
│
├── scripts/                  # ユーティリティスクリプト
│   ├── add_6am_reset_data.py        # 6:00リセットデータ追加
│   ├── cleanup_duplicate_history.py # 重複データクリーンアップ
│   ├── mqtt_receiver.py             # MQTTテスト用受信機
│   ├── mqtt_send_command.py         # MQTTコマンド送信
│   └── update_database.py           # データベース更新
│
├── docs/                     # ドキュメント
│   ├── CONFIG.md            # 設定ガイド
│   ├── CURRENT_SETUP.md     # 現在のセットアップ状況
│   ├── DATA_FORMAT.md       # データフォーマット仕様
│   ├── DEVICE_CONFIG_GUIDE.md
│   ├── MIGRATION_GUIDE.md
│   ├── MQTT_SETUP_GUIDE.md
│   ├── NETWORK_SETUP.md
│   ├── QUICK_TEST.md
│   ├── QUICKSTART.md
│   ├── VSCODE_SETUP.md
│   ├── WEBAPP_GUIDE.md
│   └── WIFI_PC_SETUP.md
│
├── firmware/                 # ファームウェア関連
│   ├── JP_LightTowerUpdate_LAN_1.4.0.ino
│   ├── Sender_1sample1min_3sampletocheck.ino
│   ├── ESP32_Gateway_backup_2026-01-22.bin
│   ├── platformio_gateway.ini
│   ├── platformio_sensor.ini
│   └── setup_platformio_projects.bat
│
├── config/                   # 設定ファイル
│   ├── mosquitto_test.conf
│   └── add_mosquitto_config.ps1
│
├── lighttower.db            # SQLiteデータベース
├── requirements.txt         # Python依存関係
├── run_webapp.bat          # Webアプリ起動スクリプト
├── .env                    # 環境変数（Gitignore対象）
├── .env.example            # 環境変数のサンプル
├── .gitignore
└── README.md               # プロジェクトREADME

```

## 実装済み機能

### 1. リアルタイムダッシュボード
- [x] WebSocketによるリアルタイム更新
- [x] 全デバイスの状態表示（緑/黄/赤ライト）
- [x] バッテリー残量表示
- [x] 最終更新時刻表示
- [x] レスポンシブデザイン（モバイル対応）
- [x] 全画面表示機能
- [x] 列数表示切替（2/3/4/5列）
- [x] 5列簡易表示モード（設備名/ステータス/ライト/稼働率/タイムラインのみ）

### 2. デバイス管理
- [x] デバイス一覧表示
- [x] デバイス登録・編集・削除
- [x] MACアドレスによる識別
- [x] デバイス名・設置場所の管理
- [x] 表示順序の設定

### 3. データ収集・保存
- [x] MQTTメッセージの受信
- [x] デバイス状態の自動保存
- [x] 履歴データの記録
- [x] 重複データの防止（asyncio.Lock + 1秒チェック）
- [x] ライト状態変更時のみ履歴記録

### 4. 稼働率分析
- [x] 日次稼働率の計算（選択した日付）
- [x] 現在の稼働率表示（6:00～現在）
- [x] 1分毎の自動更新
- [x] タイムライン表示（24時間）
- [x] グラフによる可視化
- [x] 全体稼働状況円グラフ（稼働時間割合）
- [x] 時間帯別稼働推移積上げ棒グラフ（24時間表示）
- [x] 日次稼働率推移折れ線グラフ（年月選択可能）

### 8. GreenApple gamificationシステム
- [x] 時間帯別稼働率に基づくGreenApple獲得
- [x] 獲得ルール（30%超:1個、35%以上:2個、40%以上:3個、50%以上:5個）
- [x] 本日の収穫量をヘッダーにリアルタイム表示
- [x] 月間GreenApple収穫量グラフ（年月選択可能）
- [x] 日別グラフクリックで時間帯別詳細表示
- [x] リンゴアイコンによる視覚的表示（アニメーション付き）

### 5. データログ機能
- [x] デバイスごとの受信ログ表示
- [x] モーダルウィンドウでの詳細表示
- [x] 最新100件の履歴表示
- [x] タイムスタンプ・ステータスの簡易表示
- [x] ステータスバッジの色分け（稼働中/黄色STOP/赤色STOP/休止中）

### 6. 自動リセット機能
- [x] 毎日6:00 JSTに全デバイスを休止状態にリセット
- [x] スケジューラーによる自動実行
- [x] その日の最初の信号受信時に6:00データを自動追加
- [x] アプリ停止時やオフライン時にも対応

### 7. MQTT統合
- [x] MQTTブローカーとの接続
- [x] トピックのサブスクライブ
- [x] 自動再接続機能
- [x] ユニークなクライアントID生成（接続競合回避）

## データベーススキーマ

### DeviceStatus（現在の状態）
- device_id: デバイスID
- device_addr: MACアドレス（ユニーク）
- gateway_id: ゲートウェイID
- battery: バッテリー残量
- red/yellow/green: ライト状態
- status_code: ステータスコード
- status_text: ステータステキスト
- is_active: アクティブフラグ
- last_update: 最終更新時刻

### DeviceHistory（履歴）
- id: 主キー
- device_id: デバイスID
- device_addr: MACアドレス
- battery: バッテリー残量
- red/yellow/green: ライト状態
- status_code: ステータスコード
- status_text: ステータステキスト
- timestamp: 記録時刻（UTC）

### DeviceRegistration（登録情報）
- device_addr: MACアドレス（主キー）
- name: デバイス名
- location: 設置場所
- index: 表示順序
- created_at: 登録日時
- updated_at: 更新日時

## API エンドポイント

### デバイス関連
- `GET /api/devices` - デバイス一覧取得
- `GET /api/devices/config` - デバイス管理用一覧
- `POST /api/devices/register` - デバイス登録
- `PUT /api/devices/{device_addr}` - デバイス更新
- `DELETE /api/devices/{device_addr}` - デバイス削除

### 履歴・分析関連
- `GET /api/devices/{device_id}/history` - デバイス履歴取得
- `GET /api/devices/{device_addr}/timeline` - タイムライン取得
- `GET /api/devices/{device_addr}/operation-rate` - 稼働率取得（日付指定）
- `GET /api/devices/{device_addr}/current-operation-rate` - 現在の稼働率
- `GET /api/devices/{device_addr}/data-logs` - データログ取得

### 全体分析・統計関連
- `GET /api/overall/current-status` - 全体稼働状況（円グラフ用）
- `GET /api/overall/hourly-status` - 時間帯別稼働推移とGreenApple獲得数
- `GET /api/overall/daily-operation-rate` - 日次稼働率推移（年月指定可能）
- `GET /api/overall/daily-green-apples` - 月間GreenApple収穫量（年月指定）
- `GET /api/overall/hourly-green-apples` - 時間帯別GreenApple収穫量（日付指定）

### その他
- `GET /` - ダッシュボード画面
- `GET /health` - ヘルスチェック
- `WebSocket /ws` - リアルタイム通信

## 主要な実装課題と解決策

### 1. 重複ログの防止
**課題**: 同じMQTTメッセージが複数回処理され、重複したログが保存される

**解決策**:
- デバイスごとのasyncio.Lockによる排他制御
- ライト状態変更時のみ履歴記録
- 1秒以内の重複チェック
- トランザクションの適切な分離

### 2. MQTT接続エラー（エラーコード7）
**課題**: 固定のクライアントIDにより、uvicornの自動リロード時に接続が競合

**解決策**:
- UUIDを使用したユニークなクライアントID生成
- `LightTower_WebApp_{uuid}` 形式で一意性を保証

### 3. タイムゾーン処理
**課題**: データベースはUTC、ユーザーはJSTで表示が必要

**解決策**:
- データベースには常にUTCで保存
- API レスポンスでJSTに変換
- pytzによる正確なタイムゾーン変換

### 4. 6:00リセットの信頼性
**課題**: アプリ停止時やオフライン時に6:00のリセットが記録されない

**解決策**:
- その日の最初の信号受信時に6:00データの存在をチェック
- 存在しない場合は自動的に追加
- スケジューラーと手動追加の併用

### 5. ESP32とPCのIPアドレス不一致
**課題**: PCのIPアドレスが変更されると、ESP32からのMQTTメッセージが届かない

**原因**:
- ESP32ファームウェア内でMQTTブローカーのIPアドレスがハードコード
- DHCPによりPCのIPアドレスが動的に変更される

**解決策**:
- PCのIPアドレスを固定設定（推奨）
- または、ESP32ファームウェアのIPアドレスを更新して再書き込み
- 診断方法: `ipconfig`でPCのIPアドレスを確認し、ESP32の設定と照合

## 設定ファイル

### .env
```env
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=lighttower/gateway/data
```

### ESP32ファームウェア設定
ESP32ゲートウェイのファームウェア（`C:\Users\拓磨成尾\Documents\PlatformIO\Projects\LightTower_Gateway\src\main.cpp`）内のMQTTブローカーアドレスを、PCの固定IPアドレスに合わせて設定：

```cpp
const char *mqtt_broker = "192.168.0.231";  // PCの固定IPアドレス
const int mqtt_port = 1883;
```

**重要**: PCのIPアドレスを変更した場合は、ESP32ファームウェアも更新して再書き込みが必要です。

### requirements.txt
```
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
paho-mqtt>=1.6.1
sqlalchemy>=2.0.23
pytz>=2023.3
jinja2>=3.1.2
python-multipart>=0.0.6
apscheduler>=3.10.4
```

## 起動方法

### 0. 事前準備
起動前に以下を確認してください：

1. **Mosquitto MQTTブローカーの起動**
   ```bash
   net start mosquitto
   ```

2. **PCのIPアドレス確認**
   ```bash
   ipconfig
   ```
   Wi-FiアダプターのIPv4アドレスが `192.168.0.231` であることを確認

3. **ESP32ゲートウェイの接続**
   - ESP32の電源が入っていること
   - LANケーブルで有線接続されていること
   - ESP32のシリアルモニターで接続状態を確認可能

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. Webアプリケーション起動
```bash
# Windows
run_webapp.bat

# または手動で
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. アクセス
- ダッシュボード: http://localhost:8000
- API文書: http://localhost:8000/docs

### 4. トラブルシューティング
データが更新されない場合：

1. **MQTTブローカーの確認**
   ```bash
   tasklist | findstr mosquitto
   ```

2. **IPアドレスの確認**
   ```bash
   ipconfig
   ```
   PCのIPアドレスが `192.168.0.231` か確認

3. **MQTTメッセージの受信確認**
   ```bash
   cd scripts
   python mqtt_receiver.py
   ```
   ESP32からのメッセージが表示されるか確認

4. **ESP32のシリアルモニター確認**
   - WiFi接続状態
   - MQTT接続状態
   - BLEデータ受信状態

## 今後の課題・拡張予定

### 機能拡張
- [ ] ユーザー認証・権限管理
- [ ] アラート通知機能（メール・Slack等）
- [ ] 統計レポート自動生成
- [ ] デバイスグループ管理
- [ ] データのエクスポート機能（CSV、Excel）
- [ ] 異常検知・予測機能

### パフォーマンス改善
- [ ] データベースインデックスの最適化
- [ ] キャッシュの導入（Redis等）
- [ ] 履歴データのアーカイブ機能
- [ ] ページネーション・無限スクロール

### 運用改善
- [ ] Docker化
- [ ] ログローテーション
- [ ] 自動バックアップ
- [ ] モニタリング・メトリクス収集
- [ ] CI/CDパイプライン
- [x] IPアドレス固定設定による接続安定化
- [ ] ESP32ファームウェアのmDNS対応（ホスト名による接続）
- [ ] ネットワーク設定ガイドの整備

### コード品質
- [ ] ユニットテスト追加
- [ ] 統合テスト追加
- [ ] API ルーターの完全分離
- [ ] 型ヒントの完全化
- [ ] ドキュメンテーションの充実

## 変更履歴

### 2026-02-04
- **GreenApple gamification機能の実装**
  - 時間帯別稼働率に基づくGreenApple収穫システムの導入
    - 稼働率30%超: 🍏1個
    - 稼働率35%以上: 🍏2個
    - 稼働率40%以上: 🍏3個
    - 稼働率50%以上: 🍏🍏🍏🍏🍏5個
  - ヘッダーに本日のGreenApple収穫量をリアルタイム表示（アニメーション付き）
  - GreenApple収穫ルールを時間帯別稼働推移セクションに表示

- **全体稼働状況の可視化強化**
  - 全体稼働状況円グラフの追加（本日6:00～現在の稼働時間割合）
  - 時間帯別稼働推移積上げ棒グラフの追加（24時間表示、6:00～翌5:00）
  - 24時間分のデータを事前表示（データがない時間帯も0として表示）
  - 円グラフ横幅を2/3に縮小し、時間帯別グラフを拡大（レイアウト調整）

- **月間GreenApple収穫量グラフの追加**
  - 月間の日別GreenApple収穫量を棒グラフで表示
  - グラフの棒をクリックすると時間帯別収穫量の詳細モーダルを表示
  - 時間帯別収穫量は棒グラフではなくリンゴアイコンのグリッド表示
  - アニメーション・ホバーエフェクト付き

- **期間選択機能の実装**
  - 日次稼働率推移グラフに年月セレクトボックスを追加
  - 月間GreenApple収穫量グラフに年月セレクトボックスを追加
  - デフォルトで現在の月の1日～末日を表示
  - 過去3年分のデータを選択可能
  - グラフごとに独立した期間選択が可能

- **API拡張**
  - `GET /api/overall/hourly-status` - 時間帯別稼働時間割合とGreenApple獲得数を返す
  - `GET /api/overall/current-status` - 現在の全体稼働状況（円グラフ用）
  - `GET /api/overall/daily-operation-rate` - 年月パラメータ対応に変更
  - `GET /api/overall/daily-green-apples` - 月間GreenApple収穫量データ
  - `GET /api/overall/hourly-green-apples` - 特定日の時間帯別GreenApple収穫量

- **CSS/UIの追加**
  - GreenAppleアニメーション（浮遊エフェクト、グロー効果）
  - 収穫ルール表示用のグラデーションカード
  - 時間帯別リンゴグリッドレイアウト
  - 収穫ありの時間帯をハイライト表示

### 2026-02-02
- UI/UXの改善
  - 5列簡易表示モードの実装（設備名/ステータス/ライト/稼働率/タイムラインのみ表示）
  - 全画面表示機能の追加
  - 列数表示切替機能（2/3/4/5列）
  - 受信ログ内のSTOPステータスを黄色と赤色で区別
  - モーダルヘッダーの透過問題を修正（ログが透けて見える問題）
  - ログ表示部とヘッダーの配置・z-index調整
- トラブルシューティング
  - ESP32とPCのIPアドレス不一致問題の診断手順を確立
  - IPアドレス固定設定による接続安定化の対処法を文書化

### 2026-01-29
- ディレクトリ構造の整理
  - scripts/ ディレクトリ作成、Pythonスクリプトを移動
  - docs/ ディレクトリ作成、ドキュメントを移動
  - firmware/ ディレクトリ作成、ファームウェア関連ファイルを移動
  - config/ ディレクトリ作成、設定ファイルを移動
- コードリファクタリング
  - app/utils/ モジュール作成
  - validate_mac_address を app/utils/validators.py に分離
  - get_status_from_lights を app/utils/status.py に分離
- その日の最初の信号受信時に6:00リセットデータを自動追加する機能を実装

### 2026-01-28
- 重複ログ防止機能の実装
  - asyncio.Lock による排他制御
  - ライト状態変更検知
  - 1秒以内の重複チェック
- MQTT接続エラーの修正（ユニークなクライアントID生成）
- 現在の稼働率表示機能の追加（1分毎自動更新）
- データ受信ログ機能の追加
- 稼働率の分母表示を時間+分に改善

### 2026-01-27
- 毎日6:00 JSTの自動リセット機能実装
- APScheduler 導入

## プロジェクトメンバー・連絡先

（必要に応じて記載）

## ライセンス

（必要に応じて記載）

---

最終更新: 2026-02-04
