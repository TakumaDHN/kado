# 別PCへのインストールガイド

このガイドでは、ライトタワー監視システムを別のPCにインストールし、既存のデータを移行する方法を説明します。

## 前提条件

- Windows 10/11
- Python 3.8以上
- Git
- インターネット接続

## 手順

### 1. Pythonのインストール

1. [Python公式サイト](https://www.python.org/downloads/)からPython 3.8以上をダウンロード
2. インストール時に「Add Python to PATH」にチェックを入れる
3. インストール後、コマンドプロンプトで確認：
   ```cmd
   python --version
   ```

### 2. Gitのインストール（未インストールの場合）

1. [Git公式サイト](https://git-scm.com/download/win)からGitをダウンロード
2. デフォルト設定でインストール

### 3. プロジェクトのクローン

コマンドプロンプトまたはPowerShellで実行：

```cmd
cd C:\Users\<ユーザー名>
mkdir my_python_project
cd my_python_project
git clone https://github.com/TakumaDHN/kado.git
cd kado
```

### 4. 依存パッケージのインストール

```cmd
pip install -r requirements.txt
```

### 5. 環境変数ファイルの作成

`.env.example` をコピーして `.env` を作成：

```cmd
copy .env.example .env
```

必要に応じて `.env` ファイルを編集（通常は編集不要）。

### 6. データベースの移行

#### 6.1. 元のPCでデータベースをバックアップ

元のPCで以下のコマンドを実行：

```cmd
cd C:\Users\拓磨成尾\my_python_project\kado
copy lighttower.db lighttower_backup.db
```

#### 6.2. データベースファイルを新しいPCにコピー

`lighttower_backup.db` を以下の方法で新しいPCに転送：

- USBメモリ
- ネットワーク共有フォルダ
- クラウドストレージ（OneDrive, Googleドライブなど）

#### 6.3. 新しいPCでデータベースを配置

新しいPCのプロジェクトディレクトリに配置：

```cmd
cd C:\Users\<ユーザー名>\my_python_project\kado
copy <転送元パス>\lighttower_backup.db lighttower.db
```

### 7. Mosquitto MQTTブローカーのインストール（必要な場合）

MQTTブローカーを新しいPCでも実行する場合：

1. [Mosquitto公式サイト](https://mosquitto.org/download/)からダウンロード
2. インストール後、サービスとして起動

詳細は [docs/MQTT_SETUP_GUIDE.md](MQTT_SETUP_GUIDE.md) を参照。

### 8. アプリケーションの起動

```cmd
run_webapp.bat
```

または、手動で起動：

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 9. ブラウザでアクセス

```
http://localhost:8000
```

## ネットワーク設定

社内の他のPCからもアクセスする場合：

### ファイアウォール設定

PowerShell（管理者権限）で実行：

```powershell
New-NetFirewallRule -DisplayName "ライトタワー監視システム" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

### IPアドレスの確認

```cmd
ipconfig
```

IPv4アドレスを確認し、他のPCから `http://<IPアドレス>:8000` でアクセス。

## トラブルシューティング

### データベースエラーが発生する場合

```cmd
python scripts/update_database.py
```

### MQTTに接続できない場合

1. Mosquittoサービスが起動しているか確認
2. `.env` ファイルのMQTT設定を確認
3. ファイアウォールでポート1883が開放されているか確認

### ポート8000が使用中の場合

別のポートで起動：

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## データバックアップの推奨

定期的にデータベースをバックアップすることを推奨：

```cmd
copy lighttower.db backup\lighttower_%date:~0,4%%date:~5,2%%date:~8,2%.db
```

## 更新方法

GitHubからの最新版の取得：

```cmd
cd C:\Users\<ユーザー名>\my_python_project\kado
git pull origin main
pip install -r requirements.txt
```

**注意**: データベースファイル（lighttower.db）は `git pull` では上書きされません。

## サポート

問題が発生した場合は、以下を確認：

1. [docs/QUICKSTART.md](QUICKSTART.md) - クイックスタートガイド
2. [docs/WEBAPP_GUIDE.md](WEBAPP_GUIDE.md) - Webアプリケーション詳細
3. [docs/MQTT_SETUP_GUIDE.md](MQTT_SETUP_GUIDE.md) - MQTT設定

GitHub Issues: https://github.com/TakumaDHN/kado/issues
