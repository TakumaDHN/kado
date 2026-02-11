# ライトタワーゲートウェイシステム

ESP32ベースのIoTゲートウェイシステムで、工場などの設備の稼働状態（ライトタワーの赤・黄・緑ランプ）を監視し、MQTT経由でリアルタイムにデータを送信します。

## システム構成

```
┌─────────────────┐
│ センサーデバイス  │  (複数台可能)
│   ESP32 + MAX17043 │  - ライト状態検出
│                  │  - バッテリー測定
└────────┬─────────┘  - 省電力動作
         │ ESP-NOW
         ▼
┌─────────────────┐
│ ゲートウェイ      │
│   ESP32 + W5500  │  - データ集約
│                  │  - 有線LAN接続
└────────┬─────────┘
         │ MQTT
         ▼
┌─────────────────┐
│ MQTTブローカー   │
│   Mosquitto      │  - データ中継
│                  │  - コマンド配信
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│ クライアント      │
│   Python/Web     │  - データ監視
│                  │  - 制御
└─────────────────┘
```

## 特徴

- **複数設備監視**: 最大7台の設備を同時監視
- **無線センサー**: ESP-NOWで低消費電力通信
- **長時間動作**: ディープスリープで約1分に1回起動
- **有線ゲートウェイ**: W5500イーサネットモジュールで安定通信
- **リアルタイムデータ**: MQTT経由で即座にデータ配信
- **Webダッシュボード**: FastAPIベースのリアルタイム監視UI
- **拡張性**: 複数のセンサーデバイスを1つのゲートウェイに接続可能
- **遠隔管理**: MQTT経由でコマンド送信・応答受信

## ファイル構成

```
kado/
├── JP_LightTowerUpdate_LAN_1.4.0.ino      # ゲートウェイ用コード
├── Sender_1sample1min_3sampletocheck.ino  # センサー用コード
├── app/                                   # Webアプリケーション
│   ├── main.py                           # FastAPIアプリ本体
│   ├── models.py                         # データベースモデル
│   ├── database.py                       # DB設定
│   ├── mqtt_client.py                    # MQTTクライアント
│   └── device_config.py                  # デバイス設定（7台）
├── templates/
│   └── index.html                        # ダッシュボードUI
├── mqtt_receiver.py                       # データ受信スクリプト
├── mqtt_send_command.py                   # コマンド送信スクリプト
├── run_webapp.bat                         # Webアプリ起動スクリプト
├── requirements.txt                       # Pythonライブラリ
├── QUICKSTART.md                          # クイックスタートガイド
├── CONFIG.md                              # 詳細設定ガイド
├── MQTT_SETUP_GUIDE.md                    # MQTTセットアップ
├── WEBAPP_GUIDE.md                        # Webアプリガイド
├── DEVICE_CONFIG_GUIDE.md                 # デバイス設定ガイド
├── DATA_FORMAT.md                         # データフォーマット仕様
├── VSCODE_SETUP.md                        # VSCode + PlatformIO ガイド
├── platformio_gateway.ini                 # ゲートウェイ用PlatformIO設定
├── platformio_sensor.ini                  # センサー用PlatformIO設定
├── setup_platformio_projects.bat          # PlatformIOプロジェクト自動作成
└── README.md                              # このファイル
```

## クイックスタート

### 1. 必要なもの

**ハードウェア:**
- ESP32開発ボード × 2（ゲートウェイ用、センサー用）
- W5500イーサネットモジュール
- MAX17043バッテリーゲージIC
- バッテリー（センサー用）

**ソフトウェア:**
- Windows 10/11
- Python 3.7以上
- **Arduino IDE** または **VSCode + PlatformIO**（推奨）
- Mosquitto MQTTブローカー

> **VSCodeユーザーへ**: Arduino IDEは不要です！VSCode + PlatformIOで開発できます。
> 詳細は `VSCODE_SETUP.md` を参照してください。

### 2. インストール（5分）

#### 2-1. Mosquittoのインストール

```cmd
# 公式サイトからダウンロード & インストール
https://mosquitto.org/download/

# サービスを起動
net start mosquitto
```

詳細は `MQTT_SETUP_GUIDE.md` を参照。

#### 2-2. Pythonライブラリのインストール

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
pip install -r requirements.txt
```

必要なライブラリ:
- `paho-mqtt` - MQTTクライアント
- `fastapi` - Webフレームワーク
- `uvicorn` - ASGIサーバー
- `sqlalchemy` - データベースORM
- `websockets` - WebSocket通信
- `python-dotenv` - 環境変数管理
- `pytz` - タイムゾーン処理

#### 2-3. 環境変数の設定（社内ネットワーク対応）

ESP32から社内ネットワーク経由でデータを受信する場合、MQTTブローカーのアドレスを設定します。

1. `.env.example`をコピーして`.env`を作成（既に作成済み）

2. `.env`ファイルを編集：

```env
# ESP32がデータを送信するMQTTブローカーのアドレス
# ローカルの場合
MQTT_BROKER=localhost

# 社内ネットワークの場合（例）
# MQTT_BROKER=192.168.1.100
# MQTT_PORT=1883
# MQTT_TOPIC=lighttower/gateway/data
```

**設定例:**

- **ローカル開発**: `MQTT_BROKER=localhost`（デフォルト）
- **社内MQTTサーバー**: `MQTT_BROKER=192.168.1.100`（社内サーバーのIPアドレス）
- **クラウドMQTT**: `MQTT_BROKER=mqtt.example.com`

> **注意**: `.env`ファイルは`.gitignore`に含まれているため、Gitにコミットされません。

### 3. 設定（10分）

#### 3-1. MQTTブローカーの設定

**Webアプリ側（データ受信）:**

`.env`ファイルを編集：

```env
# ESP32がデータを送信する先のMQTTブローカー
MQTT_BROKER=192.168.1.100  # 社内MQTTサーバーのIPアドレス
MQTT_PORT=1883
```

**ゲートウェイ側（データ送信）:**

`JP_LightTowerUpdate_LAN_1.4.0.ino` を編集：

```cpp
// MQTTブローカーのIPアドレス（上記と同じアドレス）
const char *mqtt_broker = "192.168.1.100";  // ← 変更
```

> **重要**: WebアプリとゲートウェイESP32は、同じMQTTブローカーに接続する必要があります。

#### 3-2. ESP32に書き込み

**Arduino IDEの場合:**
- ゲートウェイ: `JP_LightTowerUpdate_LAN_1.4.0.ino` を開いて書き込み
- センサー: `Sender_1sample1min_3sampletocheck.ino` を開いて書き込み

**VSCode + PlatformIOの場合:**
1. `setup_platformio_projects.bat` をダブルクリックして実行
2. VSCodeで `LightTower_Gateway` フォルダを開く
3. `Ctrl + Alt + U` でビルド＆アップロード
4. 同様に `LightTower_Sensor` も書き込み

詳細は `VSCODE_SETUP.md` を参照してください。

### 4. 実行

#### 方法1: Webダッシュボード（推奨）

```cmd
# Webアプリを起動
run_webapp.bat
```

ブラウザで http://localhost:8000 にアクセス

**ダッシュボード機能:**
- 7台の設備の稼働状況をリアルタイム表示
- ライトタワー状態の可視化（赤・黄・緑）
- バッテリー残量モニタリング（色付きテキスト表示）
  - 50%超: 緑色
  - 20-50%: 黄色
  - 20%未満: 赤色
- 稼働統計（稼働中/警告/エラー）
- 履歴データのグラフ表示
- オフライン検出
- **デバイス管理機能**: ウェブUI上でデバイスの追加・削除・編集
- **稼働状況タイムライン**: 日勤/夜勤別の稼働履歴バー表示
- **稼働率表示**: 期間指定での稼働率計算と円グラフ表示

詳細は `WEBAPP_GUIDE.md` を参照。

#### 方法2: コンソール監視

```cmd
# コンソールでデータ監視
python mqtt_receiver.py
```

ゲートウェイとセンサーの電源を入れると、データが表示されます。

#### 方法3: デバイス管理（Webダッシュボード）

Webダッシュボードから、デバイスの追加・編集・削除が可能です。

1. Webダッシュボードを開く: http://localhost:8000
2. 右上の「デバイス管理」ボタンをクリック
3. 「＋ 新規デバイス追加」から新しいデバイスを登録

**登録情報:**
- MACアドレス（12桁の16進数、例: ECDA3BBE61E8）
- 設備名（例: 設備1号機）
- 設置場所（例: 製造ライン A）
- 説明（例: メイン生産機）
- 表示順序（数字、小さい順に表示）

詳細は `QUICKSTART.md` を参照してください。

## 使用例

### データ受信

```cmd
python mqtt_receiver.py
```

出力例：
```
======================================================================
MQTTブローカーに接続しました
ブローカー: localhost:1883
接続時刻: 2025-01-21 10:30:15
======================================================================

----------------------------------------------------------------------
[2025-01-21 10:30:45] メッセージ #1
トピック: lighttower/gateway/data
デバイス: ECDA3BBE61E8
ゲートウェイ: JP0000000001
ステータス: 🟢 Running     | 🔋   85%
エラーコード: TMS001 (Successful)
----------------------------------------------------------------------
```

### コマンド送信

```cmd
# Heartbeat（生存確認）
python mqtt_send_command.py heartbeat
```

## データフォーマット

### センサーデータ（lighttower/gateway/data）

```json
{
  "gateway_id": "JP0000000001",
  "addr": "ECDA3BBE61E8",
  "error_code": "TMS001",
  "error": "Successful",
  "data": [
    "01",        // ステータスコード
    "Running",   // ステータステキスト
    85           // バッテリー残量 (%)
  ]
}
```

**ステータスコード:**
- `00`: Not Working（動作していない）
- `01`: Running（稼働中）🟢
- `02`: Stop（停止中）🟡
- `03`: Error（エラー）🔴

### コマンド（lighttower/gateway/command）

```json
{
  "comp_id": "JP0001",
  "lang": "jp",
  "trans_code": "12345",
  "client_tp": "web",
  "object": "gateway",
  "funct": "heartbeat",
  "input": []
}
```

## トラブルシューティング

### MQTTブローカーに接続できない

```cmd
# Mosquittoサービスを確認
net start mosquitto

# ファイアウォールを設定
netsh advfirewall firewall add rule name="Mosquitto MQTT" dir=in action=allow protocol=TCP localport=1883
```

### センサーからデータが来ない

1. MACアドレスが一致しているか確認
2. 通信距離を確認（最大200m）
3. バッテリー残量を確認

詳細は `CONFIG.md` のトラブルシューティングセクションを参照。

## 技術仕様

### ゲートウェイ

- **マイコン**: ESP32
- **通信**:
  - イーサネット: W5500（有線LAN）
  - 無線: ESP-NOW（センサー通信）
- **プロトコル**: MQTT
- **IP**: 192.168.2.232（固定）
- **MAC**: C4:DE:E2:FB:D9:68

### センサー

- **マイコン**: ESP32
- **通信**: ESP-NOW
- **電源**: バッテリー（MAX17043で残量測定）
- **動作**: ディープスリープ（57秒間隔）
- **センサー**: ライト状態検出（赤・黄・緑）

### MQTT

- **ブローカー**: Mosquitto
- **ポート**: 1883
- **認証**: なし（開発環境）
- **QoS**: 0
- **トピック**:
  - データ送信: `lighttower/gateway/data`
  - コマンド受信: `lighttower/gateway/command`

## 開発環境

- **Arduino IDE**: 1.8.x または 2.x
- **ESP32 Board**: 2.0.x
- **Python**: 3.7以上
- **OS**: Windows 10/11

### 必要なライブラリ

**Arduino:**
- WebServer_ESP32_W5500
- ArduinoJson (v6.x)
- PubSubClient
- DFRobot_MAX17043
- otadrive_esp

**Python:**
- paho-mqtt

## ライセンス

Copyright by Bui-Van Thanh

## バージョン履歴

- **v1.4.1** (2025-01-21) - 開発版、OTA無効化、ローカルMQTT対応
- **v1.4.0** - Nhật用リセットピン対応
- **v1.3.9** - Nhật用新コード
- **v1.3.8** - wizard_batクライアント追加
- **v1.3.7** - クライアント[1]〜[6]追加
- **v1.3.6** - アドレス変更
- **v1.3.5** - ブザー音削除、ファームウェア更新要求追加

## サポート

質問や問題がある場合は、以下のドキュメントを参照してください：

- **クイックスタート**: `QUICKSTART.md`
- **詳細設定**: `CONFIG.md`
- **MQTTセットアップ**: `MQTT_SETUP_GUIDE.md`
