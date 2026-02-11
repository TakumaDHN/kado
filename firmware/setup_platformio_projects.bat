@echo off
chcp 65001 >nul
echo ============================================================
echo PlatformIO プロジェクト自動セットアップ
echo ============================================================
echo.

REM 現在のディレクトリを取得
set CURRENT_DIR=%~dp0

echo 現在のディレクトリ: %CURRENT_DIR%
echo.

REM ゲートウェイプロジェクトの作成
echo [1/4] ゲートウェイプロジェクトを作成中...
if not exist "%CURRENT_DIR%LightTower_Gateway" (
    mkdir "%CURRENT_DIR%LightTower_Gateway"
    mkdir "%CURRENT_DIR%LightTower_Gateway\src"
    mkdir "%CURRENT_DIR%LightTower_Gateway\include"
    mkdir "%CURRENT_DIR%LightTower_Gateway\lib"
    echo ✓ ディレクトリを作成しました
) else (
    echo ✓ ディレクトリは既に存在します
)

REM ゲートウェイの設定ファイルをコピー
echo [2/4] ゲートウェイの設定ファイルをコピー中...
copy /Y "%CURRENT_DIR%platformio_gateway.ini" "%CURRENT_DIR%LightTower_Gateway\platformio.ini" >nul
if exist "%CURRENT_DIR%JP_LightTowerUpdate_LAN_1.4.0.ino" (
    copy /Y "%CURRENT_DIR%JP_LightTowerUpdate_LAN_1.4.0.ino" "%CURRENT_DIR%LightTower_Gateway\src\main.cpp" >nul
    echo ✓ main.cpp をコピーしました
) else (
    echo ⚠ JP_LightTowerUpdate_LAN_1.4.0.ino が見つかりません
)
echo ✓ platformio.ini をコピーしました

REM センサープロジェクトの作成
echo [3/4] センサープロジェクトを作成中...
if not exist "%CURRENT_DIR%LightTower_Sensor" (
    mkdir "%CURRENT_DIR%LightTower_Sensor"
    mkdir "%CURRENT_DIR%LightTower_Sensor\src"
    mkdir "%CURRENT_DIR%LightTower_Sensor\include"
    mkdir "%CURRENT_DIR%LightTower_Sensor\lib"
    echo ✓ ディレクトリを作成しました
) else (
    echo ✓ ディレクトリは既に存在します
)

REM センサーの設定ファイルをコピー
echo [4/4] センサーの設定ファイルをコピー中...
copy /Y "%CURRENT_DIR%platformio_sensor.ini" "%CURRENT_DIR%LightTower_Sensor\platformio.ini" >nul
if exist "%CURRENT_DIR%Sender_1sample1min_3sampletocheck.ino" (
    copy /Y "%CURRENT_DIR%Sender_1sample1min_3sampletocheck.ino" "%CURRENT_DIR%LightTower_Sensor\src\main.cpp" >nul
    echo ✓ main.cpp をコピーしました
) else (
    echo ⚠ Sender_1sample1min_3sampletocheck.ino が見つかりません
)
echo ✓ platformio.ini をコピーしました

echo.
echo ============================================================
echo セットアップ完了！
echo ============================================================
echo.
echo 次のステップ:
echo   1. VSCode を開く
echo   2. PlatformIO 拡張機能をインストール（まだの場合）
echo   3. File ^> Open Folder で以下を開く:
echo      - ゲートウェイ: %CURRENT_DIR%LightTower_Gateway
echo      - センサー: %CURRENT_DIR%LightTower_Sensor
echo   4. PlatformIO がライブラリを自動でダウンロードします
echo   5. ビルド（Ctrl+Alt+B）またはアップロード（Ctrl+Alt+U）
echo.
echo ワークスペースを作成する場合:
echo   File ^> Save Workspace As... で LightTower.code-workspace として保存
echo.
pause
