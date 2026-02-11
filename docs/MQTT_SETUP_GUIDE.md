# MQTT Mosquittoブローカー セットアップガイド

## Windows版Mosquittoのインストール

### 方法1: 公式インストーラー（推奨）

1. 以下のサイトからMosquittoをダウンロード：
   https://mosquitto.org/download/

2. Windows用インストーラー（mosquitto-x.x.x-install-windows-x64.exe）をダウンロード

3. インストーラーを実行し、デフォルト設定でインストール

4. インストール後、設定ファイルを編集：
   `C:\Program Files\mosquitto\mosquitto.conf`

### 方法2: Chocolateyを使用（コマンドライン）

```powershell
choco install mosquitto
```

## Mosquittoの設定

`C:\Program Files\mosquitto\mosquitto.conf` に以下を追加：

```conf
# 全てのネットワークインターフェースでリッスン
listener 1883 0.0.0.0

# 匿名アクセスを許可（開発環境用）
allow_anonymous true

# ログレベル
log_dest file C:\Program Files\mosquitto\mosquitto.log
log_type all
```

## Mosquittoサービスの起動

### 方法1: サービスとして起動（推奨）

管理者権限でコマンドプロンプトを開き：

```cmd
net start mosquitto
```

停止する場合：
```cmd
net stop mosquitto
```

### 方法2: コマンドラインで起動

```cmd
cd "C:\Program Files\mosquitto"
mosquitto.exe -c mosquitto.conf -v
```

## 動作確認

### テスト1: ローカルでのPublish/Subscribe

ターミナル1（Subscribe）:
```cmd
mosquitto_sub -h localhost -t "test/topic" -v
```

ターミナル2（Publish）:
```cmd
mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT!"
```

### テスト2: ライトタワーゲートウェイのトピックを監視

```cmd
mosquitto_sub -h localhost -t "lighttower/gateway/data" -v
```

## トラブルシューティング

### ポート1883が既に使用されている場合

```cmd
netstat -ano | findstr :1883
```

プロセスを確認して、必要に応じて終了させます。

### ファイアウォールの設定

Windowsファイアウォールで、ポート1883の受信接続を許可：

```cmd
netsh advfirewall firewall add rule name="Mosquitto MQTT" dir=in action=allow protocol=TCP localport=1883
```

## 設定ファイルの場所

- 設定ファイル: `C:\Program Files\mosquitto\mosquitto.conf`
- ログファイル: `C:\Program Files\mosquitto\mosquitto.log`
- データディレクトリ: `C:\Program Files\mosquitto\data`
