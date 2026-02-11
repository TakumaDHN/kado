# Mosquitto設定を追加するスクリプト
# 管理者権限で実行してください

$configPath = "C:\Program Files\mosquitto\mosquitto.conf"
$configToAdd = @"

# 全てのネットワークインターフェースでリッスン
listener 1883 0.0.0.0

# 匿名アクセスを許可（開発環境用）
allow_anonymous true

# ログレベル
log_dest file C:\Program Files\mosquitto\mosquitto.log
log_type all
"@

Add-Content -Path $configPath -Value $configToAdd
Write-Host "設定を追加しました。" -ForegroundColor Green
