@echo off
echo ========================================
echo ライトタワー監視システム 起動スクリプト
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 必要なライブラリを確認中...
pip install -r requirements.txt

echo.
echo [2/2] Webアプリケーションを起動中...
echo.
echo ダッシュボードURL: http://localhost:8000
echo API文書: http://localhost:8000/docs
echo.
echo 終了するには Ctrl+C を押してください
echo ========================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
