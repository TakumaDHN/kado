# ライトタワーシステム データフォーマット仕様

## 概要

このドキュメントでは、ESP32センサーからゲートウェイを経由してMQTTブローカーに送信されるデータの形式を詳細に説明します。

## データの流れ

```
┌──────────────────┐
│ ESP32センサー      │
│ (ライトタワー検出)  │
└────────┬─────────┘
         │ ESP-NOW (無線)
         │ struct_message
         ▼
┌──────────────────┐
│ ESP32ゲートウェイ  │
│ (W5500有線LAN)   │
└────────┬─────────┘
         │ MQTT over TCP
         │ JSON形式
         ▼
┌──────────────────┐
│ Mosquitto        │
│ MQTTブローカー    │
└────────┬─────────┘
         │ MQTT Subscribe
         │ lighttower/gateway/data
         ▼
┌──────────────────┐
│ FastAPI Webアプリ │
│ (Python)         │
└──────────────────┘
```

## 1. ESP32センサー → ゲートウェイ（ESP-NOW）

### データ構造

**ファイル:** `Sender_1sample1min_3sampletocheck.ino`

```c
typedef struct struct_message {
  int fameid;        // フレームID（ブートカウント）
  int id;            // デバイスID（通常1）
  int cntboot;       // ブートカウント
  float battery_per; // バッテリー残量(%)
  bool red;          // 赤ライト検出状態
  bool yellow;       // 黄ライト検出状態
  bool green;        // 緑ライト検出状態
} struct_message;
```

### 送信例

```c
myData.id = 1;
myData.fameid = bootCount;
myData.battery_per = 85.5;
myData.red = true;    // 赤ライト点灯
myData.green = false;
myData.yellow = false;
```

### 送信タイミング

- ライトタワーの状態が変化したとき
- 起動後最初の3回
- バッテリー測定時（60回起動ごと）

## 2. ゲートウェイ → MQTTブローカー（MQTT）

### データ構造

**ファイル:** `JP_LightTowerUpdate_LAN_1.4.0.ino`（166-252行目）

```json
{
  "gateway_id": "JP0000000001",
  "addr": "ECDA3BBE61E8",
  "error_code": "TMS001",
  "error": "Successful",
  "data": [
    "01",        // ステータスコード
    "Running",   // ステータステキスト
    85           // バッテリー残量(%)
  ]
}
```

### フィールド詳細

| フィールド | 型 | 説明 | 例 |
|-----------|---|------|-----|
| gateway_id | String | ゲートウェイID | "JP0000000001" |
| addr | String | センサーMACアドレス（大文字） | "ECDA3BBE61E8" |
| error_code | String | エラーコード | "TMS001" |
| error | String | エラーメッセージ | "Successful" |
| data[0] | String | ステータスコード（00-03） | "01" |
| data[1] | String | ステータステキスト | "Running" |
| data[2] | Integer | バッテリー残量(%) | 85 |

### ステータスコードの変換ロジック

**ソースコード:**（JP_LightTowerUpdate_LAN_1.4.0.ino 206-232行目）

```c
if (myData.red == 1 && myData.green == 0 && myData.yellow == 0) {
  STATE = RUN;         // "01", "Running"
} else if (myData.red == 0 && myData.green == 1 && myData.yellow == 0) {
  STATE = ERROR;       // "03", "Error"
} else if (myData.red == 0 && myData.green == 0 && myData.yellow == 1) {
  STATE = STOP;        // "02", "Stop"
} else if (myData.red == 0 && myData.green == 0 && myData.yellow == 0) {
  STATE = NOTWORKING;  // "00", "Not Working"
}
```

### ステータス一覧表

| ライト状態 (R/G/Y) | コード | テキスト | 意味 | ダッシュボード表示 |
|------------------|--------|---------|------|------------------|
| 1/0/0 | 01 | Running | 機械稼働中 | 🟢 緑バッジ |
| 0/0/1 | 02 | Stop | 機械停止中 | 🟡 黄バッジ |
| 0/1/0 | 03 | Error | 機械エラー | 🔴 赤バッジ |
| 0/0/0 | 00 | Not Working | 非稼働 | ⚫ グレーバッジ |

### MQTTトピック

- **データ送信:** `lighttower/gateway/data`
- **コマンド受信:** `lighttower/gateway/command`

## 3. Webアプリケーション内部データ

### データベーステーブル

#### DeviceStatus（現在のステータス）

```python
class DeviceStatus(Base):
    id = Integer              # プライマリキー
    device_id = Integer       # MACアドレスから生成（最後4桁を16進数変換）
    device_addr = String      # MACアドレス（例: "ECDA3BBE61E8"）
    gateway_id = String       # ゲートウェイID
    battery = Float           # バッテリー残量(%)
    red = Boolean             # 赤ライト状態
    yellow = Boolean          # 黄ライト状態
    green = Boolean           # 緑ライト状態
    status_code = String      # ステータスコード（00-03）
    status_text = String      # ステータステキスト
    last_update = DateTime    # 最終更新時刻
    is_active = Boolean       # アクティブ状態
```

#### DeviceHistory（履歴データ）

```python
class DeviceHistory(Base):
    id = Integer              # プライマリキー
    device_id = Integer       # デバイスID
    device_addr = String      # MACアドレス
    battery = Float           # バッテリー残量(%)
    red = Boolean             # 赤ライト状態
    yellow = Boolean          # 黄ライト状態
    green = Boolean           # 緑ライト状態
    status_code = String      # ステータスコード
    status_text = String      # ステータステキスト
    timestamp = DateTime      # 記録時刻
```

### WebSocket配信データ

```json
{
  "type": "device_update",
  "device_id": 24808,
  "device_addr": "ECDA3BBE61E8",
  "battery": 85,
  "red": true,
  "yellow": false,
  "green": false,
  "status_code": "01",
  "status_text": "Running",
  "timestamp": "2025-01-22T10:30:45.123456"
}
```

## 4. REST APIレスポンス

### GET /api/devices

全デバイスの現在のステータスを取得

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

### GET /api/devices/{device_id}/history?hours=24

指定デバイスの履歴データを取得

```json
[
  {
    "id": 1,
    "device_id": 24808,
    "device_addr": "ECDA3BBE61E8",
    "battery": 85.0,
    "red": true,
    "yellow": false,
    "green": false,
    "status_code": "01",
    "status_text": "Running",
    "timestamp": "2025-01-22T10:30:45"
  }
]
```

## 5. 実装の詳細

### MACアドレスからデバイスIDへの変換

```python
# app/mqtt_client.py (76-78行目)
addr = data.get("addr", "Unknown")  # "ECDA3BBE61E8"
device_id = int(addr[-4:], 16)      # "61E8" → 24808
```

### ステータスコードからライト状態への復元

```python
# app/mqtt_client.py (85-87行目)
red = (status_code == "01")      # Running
yellow = (status_code == "02")   # Stop
green = (status_code == "03")    # Error
```

## 6. デバッグ方法

### MQTTメッセージを直接確認

```cmd
cd "C:\Program Files\mosquitto"
mosquitto_sub.exe -h localhost -t "lighttower/gateway/data" -v
```

### Webアプリのログ確認

FastAPIを起動すると、受信したデータがコンソールに表示されます：

```
INFO - 受信データ: Device=ECDA3BBE61E8, Status=Running, Battery=85%
INFO - デバイス ECDA3BBE61E8 (Running) のデータを保存しました
```

### ブラウザの開発者ツール

1. F12を押して開発者ツールを開く
2. コンソールタブでWebSocketメッセージを確認
3. ネットワークタブでAPI通信を確認

## 付録: 登録済みデバイス一覧

**ソースコード:** JP_LightTowerUpdate_LAN_1.4.0.ino (37行目)

```c
const String clientESP[7] = {
  "ECDA3BBE61E8",  // デバイス 0
  "B08184044C94",  // デバイス 1
  "188B0E936AF8",  // デバイス 2
  "188B0E93DAD8",  // デバイス 3
  "188B0E91ABD4",  // デバイス 4
  "188B0E915D9C",  // デバイス 5
  "188B0E93B5D4"   // デバイス 6
};
```

これらのMACアドレスのデバイスからのデータのみがゲートウェイで処理されます。
