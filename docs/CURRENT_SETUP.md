# 現在の稼働環境

このドキュメントは、現在正常に動作しているシステムの構成を記録しています。

**最終更新**: 2026-01-27

---

## ✅ 動作確認済み構成

### ネットワーク構成

```
┌─────────────────────────────┐
│ ルーター                    │
│ ゲートウェイ: 192.168.1.99  │
│ ネットワーク: 192.168.0.x   │
│ サブネット: 255.255.254.0   │
└────┬───────────────┬─────────┘
     │ WiFi          │ 有線LAN
     │               │
┌────▼──────────┐   ┌▼─────────────────┐
│ PC            │   │ ESP32            │
│ WiFi接続      │   │ ゲートウェイ     │
│ 192.168.0.231 │   │ 192.168.0.55     │
│               │   │ (DHCP自動取得)   │
│ - Mosquitto   │◄──┤ MQTT送信         │
│ - Webアプリ   │   │                  │
└───────────────┘   └──────────────────┘
                           ▲
                           │ ESP-NOW
                           │
                    ┌──────┴──────┐
                    │ ESP32       │
                    │ センサー    │
                    │ (複数台)    │
                    └─────────────┘
```

---

## 📊 デバイス情報

### PC（監視サーバー）

| 項目 | 設定値 |
|------|--------|
| 接続方法 | WiFi |
| IPアドレス | 192.168.0.231 |
| サブネットマスク | 255.255.254.0 |
| ゲートウェイ | 192.168.1.99 |

**実行中のサービス:**
- Mosquitto MQTT Broker（ポート1883）
- Webアプリ（FastAPI、ポート8000）
- SQLiteデータベース

### ESP32ゲートウェイ

| 項目 | 設定値 |
|------|--------|
| 接続方法 | W5500有線LAN |
| MACアドレス | A8:42:E3:EE:39:7B |
| IPアドレス | 192.168.0.55（DHCP） |
| MQTT接続先 | 192.168.0.231:1883 |
| MQTT認証 | なし（allow_anonymous） |

**機能:**
- ESP-NOWでセンサーからデータ受信
- MQTTでPCにデータ送信
- JSON形式でデータ送信

### ESP32センサー（複数台）

| 項目 | 設定値 |
|------|--------|
| 通信方式 | ESP-NOW |
| 電源 | バッテリー |
| 動作間隔 | 約57秒（ディープスリープ） |
| 送信先MAC | C4:DE:E2:FB:D9:68 |

**登録済みデバイス:**
1. ECDA3BBE61E8 - 設備1号機
2. B08184044C94 - 設備2号機
3. 188B0E936AF8 - 設備3号機
4. 188B0E93DAD8 - 設備4号機
5. 188B0E91ABD4 - 設備5号機
6. 188B0E915D9C - 設備6号機
7. 188B0E93B5D4 - 設備7号機

---

## ⚙️ ソフトウェア設定

### Mosquitto設定

**ファイル**: `C:\Program Files\mosquitto\mosquitto.conf`

```conf
# ローカルネットワークからの接続を許可
listener 1883 0.0.0.0
allow_anonymous true
```

### Webアプリ設定

**ファイル**: `C:\Users\拓磨成尾\my_python_project\kado\.env`

```env
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=lighttower/gateway/data
```

### ESP32ゲートウェイ設定

**ファイル**: `C:\Users\拓磨成尾\Documents\PlatformIO\Projects\LightTower_Gateway\src\main.cpp`

```cpp
const char *mqtt_broker = "192.168.0.231";  // PCのWiFi IP
const char *mqtt_username = "";  // 認証なし
const char *mqtt_password = "";  // 認証なし
const int mqtt_port = 1883;
```

---

## 🔥 ファイアウォール設定

**Mosquitto MQTT通信を許可:**

```cmd
netsh advfirewall firewall add rule name="Mosquitto MQTT" dir=in action=allow protocol=TCP localport=1883
```

**確認コマンド:**

```cmd
netsh advfirewall firewall show rule name="Mosquitto MQTT"
```

---

## 🚀 起動手順

### 1. PC起動

PCがWiFi接続されていることを確認

```cmd
ipconfig
```

`192.168.0.231` が表示されることを確認

### 2. Mosquitto確認

```cmd
sc query mosquitto
```

STATE: RUNNING を確認

### 3. Webアプリ起動

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
run_webapp.bat
```

### 4. ブラウザでアクセス

```
http://localhost:8000
```

### 5. ESP32電源投入

ゲートウェイとセンサーの電源を入れる

---

## 📝 動作確認ポイント

### ESP32シリアルモニター

**期待される出力:**

```
ETH MAC: A8:42:E3:EE:39:7B, IPv4: 192.168.0.55
connecting to broker
Connecting without authentication...
Connected to MQTT server
```

### Webダッシュボード

- [ ] デバイスカードが表示される
- [ ] ライトの色が更新される（緑/黄/赤）
- [ ] バッテリー残量が表示される（色付きテキスト）
- [ ] タイムラインバーが表示される
- [ ] 統計サマリーが更新される

---

## 🔧 トラブルシューティング

### MQTT接続失敗（rc=-2）

**原因:** ネットワーク不一致

**確認:**
```cmd
ipconfig
```

PC WiFi IPが `192.168.0.231` であること

ESP32 IPが `192.168.0.55` であること

**解決策:**

ESP32の `mqtt_broker` をPCのIPアドレスに設定

### データが表示されない

**確認1: Mosquitto起動**
```cmd
sc query mosquitto
```

**確認2: ポート1883**
```cmd
netstat -an | findstr 1883
```

**確認3: ファイアウォール**
```cmd
netsh advfirewall firewall show rule name="Mosquitto MQTT"
```

---

## 📖 関連ドキュメント

- **README.md** - システム概要
- **QUICK_TEST.md** - テスト手順
- **MIGRATION_GUIDE.md** - ノートPC移行ガイド
- **WEBAPP_GUIDE.md** - Webアプリの使い方
- **MQTT_SETUP_GUIDE.md** - MQTT詳細設定

---

## 🔜 今後の予定

1. **数日間の安定動作確認**
   - データ収集の継続性
   - データベースの蓄積
   - システムの安定性

2. **ノートPCへの移行**
   - 24時間稼働環境の構築
   - 自動起動設定
   - バックアップ体制

3. **運用改善**
   - アラート機能の追加（オプション）
   - レポート機能の追加（オプション）
   - データ分析機能の強化（オプション）

---

このドキュメントは、システム移行時の参考として保存してください。
