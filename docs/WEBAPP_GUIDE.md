# ライトタワー監視Webアプリ セットアップガイド

## 概要

FastAPIを使用したリアルタイム機械稼働監視システムです。ESP32センサーからMQTT経由で受信したデータを、Webダッシュボードでリアルタイムに可視化します。

## システム構成

```
┌─────────────┐
│ ESP32センサー │ → MQTT → ┌──────────────┐ → WebSocket → ┌──────────┐
│  (ライトタワー) │          │ FastAPIサーバー │                │ ブラウザ  │
└─────────────┘          │  + SQLite DB  │                │ ダッシュ  │
                        └──────────────┘                └──────────┘
```

## 機能

### リアルタイムダッシュボード
- デバイスの稼働状態表示（赤・黄・緑ライト）
- バッテリー残量の可視化
- 接続デバイス数、稼働中/警告/エラー の統計表示
- WebSocketによる自動更新

### データ管理
- SQLiteデータベースに全履歴を保存
- デバイスごとの履歴データ取得API
- バッテリー推移グラフ
- ステータス履歴グラフ

### REST API
- `/api/devices` - 全デバイスの現在のステータス
- `/api/devices/{device_id}/history` - デバイス履歴取得
- `/health` - ヘルスチェック
- `/docs` - 自動生成されたAPI文書（Swagger UI）

## セットアップ手順

### 1. 必要なライブラリのインストール

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
pip install -r requirements.txt
```

インストールされるライブラリ:
- `fastapi` - 高速WebフレームワーK
- `uvicorn` - ASGIサーバー
- `sqlalchemy` - データベースORM
- `websockets` - WebSocket通信
- `paho-mqtt` - MQTTクライアント

### 2. Mosquitto MQTTブローカーの起動確認

```cmd
net start mosquitto
```

### 3. Webアプリケーションの起動

#### 方法1: バッチファイルを使用（簡単）

```cmd
run_webapp.bat
```

#### 方法2: コマンドラインから直接起動

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. ブラウザでアクセス

起動後、以下のURLにアクセス：

- **ダッシュボード**: http://localhost:8000
- **API文書（Swagger）**: http://localhost:8000/docs
- **ヘルスチェック**: http://localhost:8000/health

## 使い方

### ダッシュボードの見方

1. **接続ステータス**: 右上に表示
   - 🟢 接続中: WebSocketが正常に接続
   - 🔴 切断: 接続エラー（自動再接続を試行）

2. **統計カード**: 上部4つのカード
   - 接続デバイス: 登録されているデバイスの総数
   - 稼働中: 緑ライト点灯中のデバイス数
   - 警告: 黄ライト点灯中のデバイス数
   - エラー: 赤ライト点灯中のデバイス数

3. **デバイスカード**: 各デバイスの詳細情報
   - ライトタワー表示（赤・黄・緑）
   - バッテリー残量（プログレスバー）
   - 最終更新時刻

4. **グラフ**: 履歴データの可視化
   - バッテリー推移グラフ
   - ステータス履歴グラフ

### リアルタイム更新

- センサーからMQTTメッセージを受信すると、即座にダッシュボードに反映
- WebSocket接続により、ページをリロードせずに自動更新
- 接続が切れた場合、5秒後に自動再接続

## ファイル構成

```
kado/
├── app/
│   ├── __init__.py           # パッケージ初期化
│   ├── main.py               # FastAPIアプリケーション本体
│   ├── models.py             # データベースモデル
│   ├── database.py           # データベース設定
│   └── mqtt_client.py        # MQTTクライアント
├── templates/
│   └── index.html            # ダッシュボードHTML
├── static/
│   ├── css/                  # スタイルシート（将来の拡張用）
│   └── js/                   # JavaScript（将来の拡張用）
├── lighttower.db             # SQLiteデータベース（起動時に自動作成）
├── requirements.txt          # 依存ライブラリ
├── run_webapp.bat            # 起動スクリプト
└── WEBAPP_GUIDE.md           # このファイル
```

## データベース構造

### DeviceStatus テーブル（現在のステータス）

| カラム名     | 型       | 説明                 |
|-------------|----------|---------------------|
| id          | Integer  | プライマリキー        |
| device_id   | Integer  | デバイスID（ユニーク） |
| battery     | Float    | バッテリー残量 (%)    |
| red         | Boolean  | 赤ライト状態          |
| yellow      | Boolean  | 黄ライト状態          |
| green       | Boolean  | 緑ライト状態          |
| last_update | DateTime | 最終更新時刻          |
| is_active   | Boolean  | アクティブ状態        |

### DeviceHistory テーブル（履歴データ）

| カラム名     | 型       | 説明                 |
|-------------|----------|---------------------|
| id          | Integer  | プライマリキー        |
| device_id   | Integer  | デバイスID           |
| battery     | Float    | バッテリー残量 (%)    |
| red         | Boolean  | 赤ライト状態          |
| yellow      | Boolean  | 黄ライト状態          |
| green       | Boolean  | 緑ライト状態          |
| boot_count  | Integer  | ブートカウント        |
| timestamp   | DateTime | 記録時刻             |

## API使用例

### 全デバイスのステータスを取得

```bash
curl http://localhost:8000/api/devices
```

レスポンス例:
```json
[
  {
    "device_id": 24808,
    "device_addr": "ECDA3BBE61E8",
    "gateway_id": "JP0000000001",
    "battery": 85.0,
    "red": true,
    "yellow": false,
    "green": false,
    "status_code": "01",
    "status_text": "Running",
    "last_update": "2025-01-22T10:30:45",
    "is_active": true
  }
]
```

**フィールド説明:**
- `device_id`: MACアドレスの最後の4桁から生成された数値ID
- `device_addr`: センサーのMACアドレス（デバイス識別用）
- `gateway_id`: ゲートウェイのID
- `status_code`: ステータスコード（01=Running, 02=Stop, 03=Error, 00=Not Working）
- `status_text`: ステータステキスト

### デバイスの履歴を取得（過去24時間）

```bash
curl http://localhost:8000/api/devices/1/history?hours=24
```

### ヘルスチェック

```bash
curl http://localhost:8000/health
```

レスポンス例:
```json
{
  "status": "ok",
  "mqtt_connected": true,
  "websocket_clients": 2,
  "timestamp": "2025-01-22T10:30:45"
}
```

## トラブルシューティング

### 1. Webアプリが起動しない

**症状**: `uvicorn app.main:app` でエラーが出る

**対処法**:
```cmd
# ライブラリを再インストール
pip install --upgrade -r requirements.txt

# Pythonパスを確認
python --version

# app/__init__.py が存在するか確認
dir app
```

### 2. MQTTに接続できない

**症状**: ダッシュボードに「MQTT未接続」と表示される

**対処法**:
```cmd
# Mosquittoサービスを確認
net start mosquitto

# ポート1883を確認
netstat -ano | findstr :1883
```

### 3. WebSocketが接続できない

**症状**: ダッシュボード右上が「🔴 切断」のまま

**対処法**:
1. ブラウザの開発者ツールを開く（F12）
2. コンソールタブでエラーを確認
3. ファイアウォールがポート8000をブロックしていないか確認
4. ページをリロード（Ctrl+F5）

### 4. データが表示されない

**症状**: ダッシュボードは表示されるがデバイスが0台

**対処法**:
1. ESP32センサーが起動しているか確認
2. `mqtt_receiver.py` でデータを受信できるか確認:
   ```cmd
   python mqtt_receiver.py
   ```
3. `/health` APIでMQTT接続状態を確認:
   ```cmd
   curl http://localhost:8000/health
   ```

### 5. データベースエラー

**症状**: SQLiteエラーが表示される

**対処法**:
```cmd
# データベースファイルを削除して再作成
del lighttower.db
# アプリを再起動すると自動作成されます
```

## カスタマイズ

### MQTTブローカーのアドレスを変更

`app/mqtt_client.py` の以下の行を編集:

```python
MQTT_BROKER = "localhost"  # ← 変更
MQTT_PORT = 1883
```

### ポート番号を変更

起動時のコマンドで指定:

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### データ保持期間を設定

履歴データの保持期間を設定する場合は、定期的にクリーンアップするタスクを追加できます。

## 次のステップ

### 追加機能の開発

- [ ] アラート通知機能（メール・Slack）
- [ ] ユーザー認証
- [ ] デバイス管理機能（追加・削除・編集）
- [ ] レポート出力（CSV・PDF）
- [ ] 複数拠点対応
- [ ] モバイルアプリ対応

### デプロイ

本番環境にデプロイする場合:

1. **HTTPS対応**: Let's Encryptなどで証明書取得
2. **リバースプロキシ**: Nginx・Apacheの設置
3. **プロセス管理**: Systemd・PM2などでサービス化
4. **データベース移行**: SQLite → PostgreSQL・MySQL

## 参考リンク

- [FastAPI公式ドキュメント](https://fastapi.tiangolo.com/)
- [Uvicorn公式ドキュメント](https://www.uvicorn.org/)
- [SQLAlchemy公式ドキュメント](https://www.sqlalchemy.org/)
- [Chart.js公式ドキュメント](https://www.chartjs.org/)
- [Bootstrap公式ドキュメント](https://getbootstrap.com/)

## サポート

問題が発生した場合は、以下を確認してください:

1. `lighttower.db` の存在確認
2. `app/` ディレクトリ内の全ファイルの存在確認
3. ログ出力の確認（コンソールに表示されます）
