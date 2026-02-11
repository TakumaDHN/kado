"""
MQTT接続診断スクリプト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    import paho.mqtt.client as mqtt
    import socket

    # .envファイルを読み込み
    load_dotenv()

    MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

    print("=" * 50)
    print("MQTT接続診断")
    print("=" * 50)
    print()

    # 1. 設定確認
    print(f"📋 設定:")
    print(f"  - MQTTブローカー: {MQTT_BROKER}")
    print(f"  - ポート: {MQTT_PORT}")
    print()

    # 2. ホスト名解決
    print(f"🔍 ホスト名解決:")
    try:
        ip = socket.gethostbyname(MQTT_BROKER)
        print(f"  ✓ {MQTT_BROKER} → {ip}")
    except socket.gaierror as e:
        print(f"  ✗ ホスト名解決失敗: {e}")
        sys.exit(1)
    print()

    # 3. ポート接続確認
    print(f"🔌 ポート接続確認:")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((ip, MQTT_PORT))
    sock.close()

    if result == 0:
        print(f"  ✓ ポート {MQTT_PORT} は開いています")
    else:
        print(f"  ✗ ポート {MQTT_PORT} に接続できません")
        print(f"  原因:")
        print(f"    - Mosquittoが起動していない")
        print(f"    - ファイアウォールでブロックされている")
        print(f"    - IPアドレスが間違っている")
        sys.exit(1)
    print()

    # 4. MQTT接続テスト
    print(f"🔗 MQTT接続テスト:")

    connected = False
    error_msg = None

    def on_connect(client, userdata, flags, rc, properties=None):
        global connected, error_msg
        if rc == 0:
            connected = True
            print(f"  ✓ MQTT接続成功")
        else:
            error_msg = f"接続失敗 (コード: {rc})"
            print(f"  ✗ {error_msg}")

    def on_disconnect(client, userdata, rc, properties=None):
        print(f"  切断されました")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="diagnostic_client")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        print(f"  接続中...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        # 接続を待つ
        import time
        for _ in range(10):
            if connected or error_msg:
                break
            time.sleep(0.5)

        client.loop_stop()
        client.disconnect()

        print()

        if connected:
            print("=" * 50)
            print("✅ 診断完了: すべて正常です")
            print("=" * 50)
            print()
            print("データが受信できない場合:")
            print("  1. ESP32デバイスが起動しているか確認")
            print("  2. ESP32デバイスの接続先IPアドレスを確認")
            print("  3. Webアプリのログを確認")
        else:
            print("=" * 50)
            print("❌ 診断完了: 問題が見つかりました")
            print("=" * 50)
            sys.exit(1)

    except Exception as e:
        print(f"  ✗ エラー: {e}")
        sys.exit(1)

except ImportError as e:
    print(f"❌ 必要なパッケージがインストールされていません:")
    print(f"   {e}")
    print()
    print("以下のコマンドを実行してください:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
