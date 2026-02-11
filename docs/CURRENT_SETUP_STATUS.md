# 現在のセットアップ状況（2026-01-22）

## 完了した作業

### ✅ ソフトウェア
- [x] Mosquitto MQTTブローカー インストール・起動完了
- [x] Python環境構築完了
- [x] 必要なライブラリインストール完了（requirements.txt）
- [x] Webアプリケーション作成完了

### ✅ ネットワーク設定
- [x] PCの有線LAN（イーサネット）に固定IP設定: `192.168.2.1`
- [x] デフォルトゲートウェイ: 空欄（WiFi経由でインターネット維持）
- [x] ファイアウォール: ポート1883許可済み

### ✅ Webアプリ
- [x] データベース初期化完了
- [x] 7台のデバイス登録完了
- [x] MQTTブローカー接続成功
- [x] Webアプリ起動成功（http://localhost:8000）

## 現在の状態

### 動作中
```
✅ Mosquitto (localhost:1883)
✅ Webアプリ (http://localhost:8000)
✅ WiFiインターネット接続
```

### 未確認
```
❓ ESP32ゲートウェイの接続状態
❓ ESP32にゲートウェイコードが書き込まれているか
```

## 次のステップ

### 1. ESP32のシリアルモニタを確認

**目的:** ESP32にゲートウェイコード（JP_LightTowerUpdate_LAN_1.4.0.ino）が書き込まれているか確認

**Arduino IDEの場合:**
1. Arduino IDE起動
2. ESP32をUSB接続
3. ツール → ポート → COM3（または表示されるポート）を選択
4. 右上の虫眼鏡アイコン🔍をクリック
5. 右下のボーレートを「115200」に設定
6. ESP32のリセットボタンを押す

**期待される表示:**
```
ETH Started
ETH Connected
[NEW] ESP32 Board MAC Address:  C4:DE:E2:FB:D9:68
GWI001
Light Tower Gateway
Copyright by Bui-Van Thanh
Version 1.4.1 (Development)
connecting to broker
Connected to MQTT server
```

### 2. ESP32の接続確認

**物理接続:**
- [ ] ESP32とPCをLANケーブルで接続
- [ ] LANポートのLEDが点灯しているか確認
- [ ] ESP32の電源が入っているか確認

**ネットワーク確認:**
```cmd
ping 192.168.2.232
```

### 3. データ受信テスト

別のコマンドプロンプトで実行（実行したまま）:
```cmd
cd "C:\Program Files\mosquitto"
mosquitto_sub.exe -h localhost -t "lighttower/#" -v
```

ESP32からデータが送信されると、ここに表示される。

## 設定済みデバイス（7台）

| # | MACアドレス | 設備名 | 場所 |
|---|-------------|--------|------|
| 1 | ECDA3BBE61E8 | 設備1号機 | 製造ライン A |
| 2 | B08184044C94 | 設備2号機 | 製造ライン A |
| 3 | 188B0E936AF8 | 設備3号機 | 製造ライン B |
| 4 | 188B0E93DAD8 | 設備4号機 | 製造ライン B |
| 5 | 188B0E91ABD4 | 設備5号機 | 製造ライン C |
| 6 | 188B0E915D9C | 設備6号機 | 製造ライン C |
| 7 | 188B0E93B5D4 | 設備7号機 | 製造ライン C |

## ESP32の設定値

```cpp
// JP_LightTowerUpdate_LAN_1.4.0.ino
IPAddress myIP(192, 168, 2, 232);      // ESP32のIP
IPAddress myGW(192, 168, 2, 1);        // ゲートウェイ（PC）
const char *mqtt_broker = "192.168.2.1";  // MQTTブローカー（PC）
```

## トラブルシューティング

### ESP32に接続できない場合

1. **シリアルモニタで起動メッセージを確認**
   - ゲートウェイコードが書き込まれているか
   - 「ETH Connected」が表示されるか

2. **物理接続を確認**
   - LANケーブルが両端に刺さっているか
   - LEDが点灯しているか

3. **ネットワークアダプタをリセット**
   ```cmd
   netsh interface set interface "イーサネット" disabled
   netsh interface set interface "イーサネット" enabled
   ```

4. **ESP32を再起動**
   - 電源を入れ直す
   - 30秒待ってから再度Ping

### Webアプリを再起動する場合

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
run_webapp.bat
```

または

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 重要なファイル

### 設定ファイル
- `app/device_config.py` - デバイス設定（7台の設備名など）
- `app/main.py` - Webアプリ本体
- `templates/index.html` - ダッシュボードUI

### ドキュメント
- `WEBAPP_GUIDE.md` - Webアプリ詳細ガイド
- `DEVICE_CONFIG_GUIDE.md` - デバイス設定変更方法
- `NETWORK_SETUP.md` - ネットワーク設定詳細
- `WIFI_PC_SETUP.md` - WiFi+有線LAN構成ガイド
- `DATA_FORMAT.md` - データフォーマット仕様

### ESP32コード
- `JP_LightTowerUpdate_LAN_1.4.0.ino` - ゲートウェイ用（要書き込み）
- `Sender_1sample1min_3sampletocheck.ino` - センサー用

## 現在の問題点

```
❌ ESP32にPingが通らない
   → 原因: ESP32の起動状態が不明
   → 次のステップ: シリアルモニタで確認
```

## Webアプリのログ（最新）

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
2026-01-22 18:38:50,183 - app.main - INFO - データベースを初期化しました
2026-01-22 18:38:50,194 - app.main - INFO - 全7台のデバイスを初期化しました
2026-01-22 18:38:52,253 - app.main - INFO - MQTTクライアントを起動しました
2026-01-22 18:38:52,253 - app.mqtt_client - INFO - MQTTブローカーに接続しました: localhost:1883
```

→ Webアプリは正常動作中

## 連絡先・リソース

- **ダッシュボード**: http://localhost:8000
- **API文書**: http://localhost:8000/docs
- **ヘルスチェック**: http://localhost:8000/health

## メモ

- VSCodeを再起動しても会話履歴は残る
- このファイル（CURRENT_SETUP_STATUS.md）に現在の状況を記録
- 次回起動時はこのファイルを確認すれば状況がわかる
