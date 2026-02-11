# ライトタワーゲートウェイ 設定ガイド

## 概要

このシステムは以下の3つのコンポーネントで構成されています：

1. **センサーデバイス** (Sender_1sample1min_3sampletocheck.ino)
   - ライトタワーの状態（赤・黄・緑ランプ）を検出
   - バッテリー残量を測定
   - ESP-NOW経由でゲートウェイに送信

2. **ゲートウェイデバイス** (JP_LightTowerUpdate_LAN_1.4.0.ino)
   - ESP-NOWでセンサーからデータを受信
   - イーサネット（W5500）経由でMQTTブローカーに送信
   - MQTTコマンドを受信して処理

3. **MQTTブローカー** (Mosquitto)
   - データの中継サーバー
   - センサーデータを保存・配信

## 現在の設定

### ゲートウェイ設定 (JP_LightTowerUpdate_LAN_1.4.0.ino)

```cpp
// ネットワーク設定
IPAddress myIP(192, 168, 2, 232);      // ゲートウェイのIPアドレス
IPAddress myGW(192, 168, 2, 1);        // デフォルトゲートウェイ
IPAddress mySN(255, 255, 255, 0);      // サブネットマスク
IPAddress myDNS(8, 8, 8, 8);           // DNSサーバー

// MACアドレス (ESP-NOW通信用)
uint8_t newMACAddress[] = { 0xC4, 0xDE, 0xE2, 0xFB, 0xD9, 0x68 };

// MQTT設定
#define clientID "JP_LightTower_GW001"
const char *mqtt_broker = "192.168.2.1";           // MQTTブローカーのIPアドレス
const char *mqtt_username = "";                    // 認証なしの場合は空
const char *mqtt_password = "";                    // 認証なしの場合は空
const int mqtt_port = 1883;

// MQTTトピック
String defaultTopicSub = "lighttower/gateway/command";  // コマンド受信
String defaultTopicPub = "lighttower/gateway/data";     // データ送信
```

### センサーデバイス設定 (Sender_1sample1min_3sampletocheck.ino)

```cpp
// ゲートウェイのMACアドレス（送信先）
uint8_t broadcastAddress[] = {0xc4, 0xde, 0xe2, 0xfb, 0xd9, 0x68};

// デバイスID（複数のセンサーを識別）
#define idOfDevice 1  // 各センサーで異なる番号を設定

// スリープ時間
#define TIME_TO_SLEEP 57  // 秒（約1分ごとに起動）
```

## セットアップ手順

### 1. Mosquitto MQTTブローカーのインストール

`MQTT_SETUP_GUIDE.md` を参照してください。

### 2. MQTTブローカーのIPアドレスを確認

Windows PCがMQTTブローカーを実行する場合：

```cmd
ipconfig
```

`192.168.2.x` の範囲のIPアドレスを確認し、ゲートウェイコードの `mqtt_broker` に設定します。

例：
- PCのIP: 192.168.2.100 の場合
- `const char *mqtt_broker = "192.168.2.100";` に変更

### 3. ゲートウェイデバイスのアップロード

1. Arduino IDEまたはPlatformIOを開く
2. `JP_LightTowerUpdate_LAN_1.4.0.ino` を開く
3. 必要なライブラリをインストール：
   - WebServer_ESP32_W5500
   - ArduinoJson (v6.x)
   - PubSubClient
   - otadrive_esp（OTA無効化しているが、コンパイルには必要）
4. ボードを選択：ESP32 Dev Module
5. アップロード

### 4. センサーデバイスのアップロード

1. `Sender_1sample1min_3sampletocheck.ino` を開く
2. 必要なライブラリをインストール：
   - DFRobot_MAX17043
3. `idOfDevice` を各センサーで異なる番号に設定（1, 2, 3...）
4. ボードを選択：ESP32 Dev Module
5. アップロード

### 5. 動作確認

Pythonスクリプトでデータを監視：

```bash
cd C:\Users\拓磨成尾\my_python_project\kado
python mqtt_receiver.py
```

## MQTTデータフォーマット

### センサーデータ（ゲートウェイ→MQTTブローカー）

トピック: `lighttower/gateway/data`

```json
{
  "gateway_id": "JP0000000001",
  "addr": "ECDA3BBE61E8",
  "error_code": "TMS001",
  "error": "Successful",
  "data": [
    "01",           // ステータスコード (00: Not Working, 01: Running, 02: Stop, 03: Error)
    "Running",      // ステータステキスト
    85              // バッテリー残量 (%)
  ]
}
```

### コマンド（MQTTブローカー→ゲートウェイ）

トピック: `lighttower/gateway/command`

#### Heartbeat（生存確認）

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

応答:
```json
{
  "trans_code": "12345",
  "res_code": 1,
  "error_code": "ok",
  "error_cont": "JP_OK",
  "data": ["pong"]
}
```

## トラブルシューティング

### 問題1: ゲートウェイがMQTTブローカーに接続できない

- MQTTブローカーのIPアドレスが正しいか確認
- Mosquittoサービスが起動しているか確認：`net start mosquitto`
- ファイアウォールがポート1883をブロックしていないか確認

### 問題2: センサーからデータが届かない

- ゲートウェイとセンサーのMACアドレスが一致しているか確認
- ESP-NOWの通信距離（最大200m、障害物により短くなる）
- センサーのバッテリー残量を確認

### 問題3: コンパイルエラー

- 必要なライブラリがすべてインストールされているか確認
- Arduino IDEのボード設定が正しいか確認（ESP32 Dev Module）
- ライブラリのバージョンを確認（ArduinoJsonはv6.xが必要）

## 補足

### 複数のセンサーを追加する場合

1. センサーのMACアドレスを取得
2. ゲートウェイコードの `clientESP[]` 配列に追加
3. `idOfDevice` を各センサーで異なる番号に設定

### MQTTの認証を有効にする場合

1. Mosquittoの設定ファイルでユーザー/パスワードを設定
2. ゲートウェイコードの `mqtt_username` と `mqtt_password` を設定
