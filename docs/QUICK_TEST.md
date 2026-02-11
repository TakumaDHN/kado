# クイックテストガイド（フェーズ1）

現在のPCで有線LAN接続してテストする手順です。

## 準備完了チェック

### ✅ ハードウェア
- [ ] PCとルーターを有線LANケーブルで接続
- [ ] ESP32ゲートウェイの電源準備
- [ ] ESP32センサーの電源準備（バッテリー）

### ✅ ソフトウェア
- [ ] Python インストール済み
- [ ] Mosquitto インストール済み
- [ ] Pythonライブラリ インストール済み（`pip install -r requirements.txt`）
- [ ] ESP32ゲートウェイのコード更新済み（mqtt_broker = "192.168.2.1"）

---

## テスト手順

### Step 1: ネットワーク確認

```cmd
ipconfig
```

**確認事項:**
```
イーサネット アダプター イーサネット:
   IPv4 アドレス . . . . . . . . . . . .: 192.168.2.1  ← これを確認
```

✅ `192.168.2.1` が表示されていればOK

---

### Step 2: Mosquitto 起動確認

```cmd
net start mosquitto
```

**期待される出力:**
```
Mosquitto Broker サービスは既に開始されています。
```
または
```
Mosquitto Broker サービスを開始します。
Mosquitto Broker サービスは正常に開始されました。
```

✅ エラーが出なければOK

**トラブルシューティング:**
```cmd
# サービス状態を確認
sc query mosquitto

# ポート1883が使用されているか確認
netstat -an | findstr 1883
```

---

### Step 3: Webアプリ起動

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
run_webapp.bat
```

**期待される出力:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
MQTTブローカーに接続中: localhost:1883
MQTTブローカーに接続しました: localhost:1883
```

✅ "Application startup complete" が表示されればOK

---

### Step 4: ブラウザで確認

ブラウザを開いて以下にアクセス：

```
http://localhost:8000
```

**確認事項:**
- [ ] ダッシュボードが表示される
- [ ] 「接続ステータス」が🟢緑色になっている
- [ ] 7台のデバイスカードが表示される（初期状態はオフライン）

---

### Step 5: ESP32ゲートウェイの起動

1. **ESP32をUSB接続**

2. **PlatformIOでアップロード**
   - VSCodeでプロジェクトを開く
   - `Ctrl + Alt + U` でビルド＆アップロード

3. **シリアルモニターで確認**
   - `Ctrl + Alt + S` でシリアルモニター起動

   **期待される出力:**
   ```
   Connecting to MQTT...
   Connected to MQTT server
   ```

4. **USB接続を外して電源アダプターで起動**（本番運用の場合）

---

### Step 6: ESP32センサーの起動

1. センサーデバイスの電源を入れる
2. 約1分待つ（初回起動時）

---

### Step 7: データ受信確認

#### 7-1. Webダッシュボードで確認

ブラウザ（`http://localhost:8000`）で以下を確認：

- [ ] デバイスカードのステータスが更新される
- [ ] ライトの色が点灯する（緑/黄/赤）
- [ ] バッテリー残量が表示される
- [ ] 「最終更新」の時刻が更新される
- [ ] 統計サマリーの数値が変わる

#### 7-2. コンソールログで確認

Webアプリのコンソールに以下が表示される：

```
INFO - デバイス ECDA3BBE61E8 (Running) のデータを保存しました
```

---

## 動作確認のポイント

### ✅ 正常動作の目安

1. **ESP32ゲートウェイ**
   - シリアルモニターで "Connected to MQTT server" と表示
   - 定期的にセンサーデータを受信

2. **Webダッシュボード**
   - リアルタイムでデバイス情報が更新される
   - WebSocket接続が🟢緑色
   - デバイスカードが「オフライン」から「稼働中」などに変わる

3. **データの流れ**
   ```
   センサー → (ESP-NOW) → ゲートウェイ → (MQTT) → Mosquitto → Webアプリ → ブラウザ
   ```

---

## トラブルシューティング

### ❌ データが届かない

**確認1: ネットワーク接続**
```cmd
ping 192.168.2.232
```
ESP32ゲートウェイに疎通できるか確認

**確認2: Mosquitto接続**
```cmd
# 別のターミナルでMQTT購読テスト
cd C:\Users\拓磨成尾\my_python_project\kado
python mqtt_receiver.py
```

データが表示されれば、MQTTは正常

**確認3: ファイアウォール**
```cmd
netsh advfirewall firewall add rule name="Mosquitto MQTT" dir=in action=allow protocol=TCP localport=1883
```

**確認4: ESP32のIPアドレス**

ESP32のシリアルモニターでIPアドレスを確認：
```
IP: 192.168.2.232
```

期待通りのIPか確認

---

### ❌ Webアプリが起動しない

**確認1: Pythonバージョン**
```cmd
python --version
```
Python 3.7以上が必要

**確認2: ライブラリインストール**
```cmd
pip install -r requirements.txt
```

**確認3: ポート8000が使用中**
```cmd
netstat -ano | findstr 8000
```

他のプログラムが使用していれば停止

---

### ❌ ESP32がMQTTに接続できない

**確認1: mqtt_brokerの設定**
```cpp
const char *mqtt_broker = "192.168.2.1";  // PCのIPと一致しているか
```

**確認2: Mosquittoの起動**
```cmd
sc query mosquitto
```

**確認3: ネットワーク疎通**

ESP32からPCへのpingが通るか確認（ルーターの管理画面などで）

---

## 次のステップ

テストが成功したら：

1. [ ] 数時間〜数日間、安定動作を確認
2. [ ] データベースにデータが蓄積されることを確認
3. [ ] デバイス管理機能をテスト（追加・編集・削除）
4. [ ] タイムライン表示機能をテスト
5. [ ] 稼働率表示機能をテスト

安定動作が確認できたら：

📄 **`MIGRATION_GUIDE.md`** を参照してノートPCへ移行

---

## サポート

問題が解決しない場合：
- README.md のトラブルシューティングセクション
- CONFIG.md の詳細設定
- MQTT_SETUP_GUIDE.md のMQTT設定

を参照してください。
