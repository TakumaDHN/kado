# ライトタワーゲートウェイ クイックスタートガイド

このガイドでは、最短でシステムをセットアップしてデータを受信できるようにします。

## 前提条件

- Windows 10/11
- Python 3.7以上（✓ インストール済み: Python 3.12.4）
- Arduino IDEまたはPlatformIO
- ESP32開発ボード（ゲートウェイ用とセンサー用）

## セットアップ手順（5ステップ）

### ステップ1: Mosquitto MQTTブローカーのインストール

#### オプションA: 公式インストーラー（推奨）

1. https://mosquitto.org/download/ からWindows版をダウンロード
2. インストーラーを実行（デフォルト設定でOK）
3. 設定ファイルを編集：
   - ファイル: `C:\Program Files\mosquitto\mosquitto.conf`
   - 最後に以下を追加：
     ```conf
     listener 1883 0.0.0.0
     allow_anonymous true
     ```
4. サービスを起動：
   ```cmd
   net start mosquitto
   ```

#### オプションB: Chocolatey

管理者権限でPowerShellを開き：
```powershell
choco install mosquitto
net start mosquitto
```

### ステップ2: Pythonライブラリのインストール

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
pip install -r requirements.txt
```

### ステップ3: ゲートウェイコードの設定

1. Arduino IDEで `JP_LightTowerUpdate_LAN_1.4.0.ino` を開く

2. PCのIPアドレスを確認：
   ```cmd
   ipconfig
   ```
   `192.168.2.x` のアドレスをメモする（例: 192.168.2.100）

3. コード内の設定を確認・修正（必要に応じて）：
   ```cpp
   // 111行目付近 - MQTTブローカーのIPアドレス
   const char *mqtt_broker = "192.168.2.100";  // ← PCのIPアドレスに変更
   ```

4. 必要なライブラリをインストール：
   - Tools → Manage Libraries...
   - 検索してインストール：
     - `WebServer_ESP32_W5500`
     - `ArduinoJson` (v6.x)
     - `PubSubClient`
     - `otadrive_esp`

5. ボード設定：
   - Board: "ESP32 Dev Module"
   - Upload Speed: 115200
   - Flash Mode: QIO

6. ESP32に書き込み

### ステップ4: センサーコードの設定

1. Arduino IDEで `Sender_1sample1min_3sampletocheck.ino` を開く

2. 必要なライブラリをインストール：
   - `DFRobot_MAX17043`

3. デバイスIDを確認（複数のセンサーを使う場合は変更）：
   ```cpp
   // 20行目
   #define idOfDevice 1  // 各センサーで異なる番号に
   ```

4. ESP32に書き込み

### ステップ5: 動作確認

#### 5-1. MQTTブローカーの起動確認

```cmd
net start mosquitto
```

#### 5-2. Pythonスクリプトでデータを監視

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
python mqtt_receiver.py
```

#### 5-3. ゲートウェイの電源を入れる

- シリアルモニタで起動メッセージを確認
- "Connected to MQTT server" が表示されればOK

#### 5-4. センサーの電源を入れる

- 約1分に1回、データが送信されます
- Pythonスクリプトにデータが表示されれば成功！

#### 5-5. Heartbeatテスト（オプション）

別のターミナルで：
```cmd
python mqtt_send_command.py heartbeat
```

ゲートウェイから "pong" が返ってくればOK

## データフォーマット

### 受信データの例

```json
{
  "gateway_id": "JP0000000001",
  "addr": "ECDA3BBE61E8",
  "error_code": "TMS001",
  "error": "Successful",
  "data": [
    "01",        // ステータス: 01=Running
    "Running",   // ステータステキスト
    85           // バッテリー: 85%
  ]
}
```

### ステータスコード

- `00`: Not Working（動作していない）
- `01`: Running（稼働中）
- `02`: Stop（停止中）
- `03`: Error（エラー）

## トラブルシューティング

### 問題: MQTTブローカーに接続できない

**症状:** Pythonスクリプトで "ConnectionRefusedError" が発生

**解決方法:**
1. Mosquittoサービスが起動しているか確認
   ```cmd
   net start mosquitto
   ```

2. ファイアウォールの設定を確認
   ```cmd
   netsh advfirewall firewall add rule name="Mosquitto MQTT" dir=in action=allow protocol=TCP localport=1883
   ```

3. Mosquittoの設定ファイルを確認
   - `C:\Program Files\mosquitto\mosquitto.conf`
   - `listener 1883 0.0.0.0` が追加されているか

### 問題: ゲートウェイがMQTTブローカーに接続できない

**症状:** シリアルモニタで "MQTT LOST CONNECTION" が表示

**解決方法:**
1. `mqtt_broker` のIPアドレスが正しいか確認
2. PCとゲートウェイが同じネットワークにいるか確認
3. ゲートウェイのIPアドレス (192.168.2.232) が他のデバイスと競合していないか確認

### 問題: センサーからデータが来ない

**症状:** Pythonスクリプトで何も表示されない

**解決方法:**
1. センサーとゲートウェイのMACアドレスが一致しているか確認
   - ゲートウェイ: `0xC4, 0xDE, 0xE2, 0xFB, 0xD9, 0x68`
   - センサー: `{0xc4, 0xde, 0xe2, 0xfb, 0xd9, 0x68}`

2. 通信距離を確認（最大200m、障害物により短くなる）

3. センサーのシリアルモニタで "Delivery Success" が表示されているか確認

### 問題: コンパイルエラー

**症状:** Arduino IDEでコンパイルエラーが発生

**解決方法:**
1. 必要なライブラリがすべてインストールされているか確認
2. ArduinoJsonのバージョンがv6.xであることを確認（v7.xは非互換）
3. ボード設定が正しいか確認（ESP32 Dev Module）

## 次のステップ

### 複数のセンサーを追加

1. 新しいセンサーのMACアドレスを取得
2. ゲートウェイコードの `clientESP[]` 配列に追加
3. センサーコードの `idOfDevice` を変更

### データの可視化

- Grafana + InfluxDBでダッシュボードを作成
- Node-REDでフロー制御
- Webアプリでリアルタイムモニタリング

### 本番環境への移行

1. MQTTの認証を有効化
2. SSL/TLS暗号化を有効化
3. OTA機能を有効化（otadrive_esp）

## 参考ドキュメント

- 詳細な設定: `CONFIG.md`
- MQTTセットアップ: `MQTT_SETUP_GUIDE.md`
- トラブルシューティング: `CONFIG.md` の最後

## サポート

問題が解決しない場合は、以下の情報を添えて質問してください：

1. エラーメッセージ（完全なログ）
2. シリアルモニタの出力
3. Mosquittoのログ（`C:\Program Files\mosquitto\mosquitto.log`）
4. ネットワーク設定（`ipconfig` の出力）
