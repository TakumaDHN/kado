# VSCode + PlatformIO セットアップガイド

VSCodeでESP32開発を行うための設定ガイドです。Arduino IDEよりも高機能で使いやすい開発環境を構築できます。

## PlatformIOのメリット

- **統合開発環境**: コード補完、デバッグ、シリアルモニタがすべてVSCode内で完結
- **依存関係管理**: ライブラリのバージョン管理が簡単
- **複数プロジェクト管理**: ゲートウェイとセンサーを別プロジェクトとして管理
- **ビルドが速い**: Arduino IDEより高速
- **Git統合**: バージョン管理が簡単

## セットアップ手順

### 1. PlatformIO拡張機能のインストール

1. VSCodeを開く
2. 左側の拡張機能アイコン（四角が4つ）をクリック
3. "PlatformIO IDE" を検索
4. インストール
5. VSCodeを再起動

### 2. ゲートウェイプロジェクトの作成

#### 2-1. 新しいプロジェクトを作成

1. PlatformIOアイコン（蟻のマーク）をクリック
2. "New Project" をクリック
3. 設定：
   - **Name**: `LightTower_Gateway`
   - **Board**: `Espressif ESP32 Dev Module`
   - **Framework**: `Arduino`
   - **Location**: プロジェクトの保存場所を選択
4. "Finish" をクリック（初回は時間がかかります）

#### 2-2. 既存の.inoファイルをコピー

プロジェクトフォルダ構成：
```
LightTower_Gateway/
├── platformio.ini        # 設定ファイル
├── src/
│   └── main.cpp          # ← ここに .ino の内容をコピー
├── lib/
└── include/
```

`JP_LightTowerUpdate_LAN_1.4.0.ino` の内容を `src/main.cpp` にコピー

**注意**: ファイル拡張子は `.cpp` に変更されますが、中身はそのままでOKです。

#### 2-3. platformio.ini の設定

`platformio.ini` を以下の内容に書き換え：

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino

# シリアル通信設定
monitor_speed = 115200
upload_speed = 115200

# 必要なライブラリ
lib_deps =
    khoih-prog/WebServer_ESP32_W5500@^1.5.3
    bblanchon/ArduinoJson@^6.21.3
    knolleary/PubSubClient@^2.8
    Wire
    SPI
    WiFi
    HTTPClient
    otadrive/OTAdrive ESP32-Arduino@^2.0.0

# ビルドフラグ
build_flags =
    -D DEBUG_ETHERNET_WEBSERVER_PORT=Serial
    -D _ETHERNET_WEBSERVER_LOGLEVEL_=3
```

### 3. センサープロジェクトの作成

#### 3-1. 新しいプロジェクトを作成

1. "New Project" をクリック
2. 設定：
   - **Name**: `LightTower_Sensor`
   - **Board**: `Espressif ESP32 Dev Module`
   - **Framework**: `Arduino`
3. "Finish" をクリック

#### 3-2. 既存の.inoファイルをコピー

`Sender_1sample1min_3sampletocheck.ino` の内容を `src/main.cpp` にコピー

#### 3-3. platformio.ini の設定

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino

# シリアル通信設定
monitor_speed = 115200
upload_speed = 115200

# 必要なライブラリ
lib_deps =
    https://github.com/DFRobot/DFRobot_MAX17043.git
    Wire
    WiFi

# ビルドフラグ（省電力設定）
build_flags =
    -D ARDUINO_ARCH_ESP32
```

## 使用方法

### ビルド（コンパイル）

1. 下部のステータスバーのチェックマーク（✓）をクリック
2. または `Ctrl + Alt + B`

### アップロード

1. ESP32をUSBで接続
2. 下部のステータスバーの矢印（→）をクリック
3. または `Ctrl + Alt + U`

### シリアルモニタ

1. 下部のステータスバーのコンセントマーク（🔌）をクリック
2. または `Ctrl + Alt + S`

### クリーンビルド

ビルドエラーが発生した場合：

1. PlatformIOアイコン → Project Tasks → esp32dev → General → Clean
2. または下部のゴミ箱マークをクリック

## ライブラリのインストール

### 方法1: platformio.ini に記述（推奨）

`lib_deps` セクションに追加すると、自動でインストールされます。

```ini
lib_deps =
    ライブラリ名@バージョン
    GitHubのURL
```

### 方法2: PlatformIO Library Manager

1. PlatformIOアイコン → Libraries
2. ライブラリを検索
3. "Add to Project" をクリック

## トラブルシューティング

### 問題: ライブラリが見つからない

```bash
# ライブラリを手動でインストール
pio lib install "WebServer_ESP32_W5500"
```

### 問題: コンパイルエラー

1. プロジェクトをクリーン
2. `.pio` フォルダを削除
3. 再ビルド

### 問題: シリアルポートが見つからない

1. デバイスマネージャーでCOMポートを確認
2. `platformio.ini` に以下を追加：

```ini
upload_port = COM3    # ← 実際のポート番号
monitor_port = COM3
```

### 問題: ESP32が認識されない

1. CP210xまたはCH340ドライバーをインストール
   - CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
   - CH340: http://www.wch-ic.com/downloads/CH341SER_ZIP.html

## プロジェクト構成の推奨

```
kado/
├── LightTower_Gateway/          # ゲートウェイプロジェクト
│   ├── platformio.ini
│   ├── src/
│   │   └── main.cpp
│   └── .pio/                    # ビルド成果物（自動生成）
│
├── LightTower_Sensor/           # センサープロジェクト
│   ├── platformio.ini
│   ├── src/
│   │   └── main.cpp
│   └── .pio/
│
├── mqtt_receiver.py             # テストスクリプト
├── mqtt_send_command.py
└── requirements.txt
```

## ワークスペースの作成（オプション）

複数のプロジェクトを1つのVSCodeウィンドウで管理：

1. File → Save Workspace As...
2. `LightTower.code-workspace` として保存

ワークスペースファイルの例：

```json
{
  "folders": [
    {
      "path": "LightTower_Gateway"
    },
    {
      "path": "LightTower_Sensor"
    }
  ],
  "settings": {}
}
```

## 便利な機能

### インテリセンス（コード補完）

- 関数名、変数名を自動補完
- ドキュメントの表示
- エラーのリアルタイム検出

### デバッグ

ESP32のハードウェアデバッガー（JTAG）を使用すれば、ブレークポイントを設定してデバッグ可能。

### Git統合

- ソースコードのバージョン管理
- 変更履歴の確認
- ブランチの切り替え

## Arduino IDEとの比較

| 機能 | Arduino IDE | VSCode + PlatformIO |
|------|-------------|---------------------|
| コード補完 | 基本的 | 高度（IntelliSense） |
| ライブラリ管理 | 手動 | 自動 |
| 複数プロジェクト | 難しい | 簡単 |
| Git統合 | なし | あり |
| ビルド速度 | 遅い | 速い |
| デバッグ | なし | あり（要ハードウェア） |
| 学習曲線 | 簡単 | やや複雑 |

## まとめ

VSCode + PlatformIOは、Arduino IDEより強力で柔軟な開発環境です。特に大規模プロジェクトや複数デバイスの管理に適しています。

既存の `.ino` ファイルもそのまま使えるため、移行も簡単です。
