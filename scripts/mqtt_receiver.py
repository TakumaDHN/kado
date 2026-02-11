#!/usr/bin/env python3
"""
ライトタワーゲートウェイ MQTTデータ受信スクリプト

このスクリプトは、ゲートウェイから送信されるセンサーデータを
リアルタイムで監視・表示します。

使用方法:
    python mqtt_receiver.py

設定:
    MQTT_BROKER: MQTTブローカーのIPアドレス
    MQTT_PORT: MQTTブローカーのポート（デフォルト: 1883）
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
import sys
import signal

# MQTT設定 - 環境に合わせて変更してください
MQTT_BROKER = "localhost"  # または "192.168.2.1" など
MQTT_PORT = 1883
MQTT_USERNAME = None  # 認証が必要な場合は設定
MQTT_PASSWORD = None

# 購読するトピック
TOPIC_DATA = "lighttower/gateway/data"
TOPIC_COMMAND = "lighttower/gateway/command"
TOPIC_ALL = "lighttower/#"  # すべてのライトタワー関連トピック

# データカウンター
message_count = 0
device_status = {}

# ステータスコードの定義
STATUS_CODES = {
    "00": "Not Working",
    "01": "Running",
    "02": "Stop",
    "03": "Error"
}

def signal_handler(sig, frame):
    """Ctrl+C でプログラムを終了"""
    print("\n\nプログラムを終了します...")
    print(f"受信したメッセージ総数: {message_count}")
    sys.exit(0)

def on_connect(client, userdata, flags, rc):
    """MQTTブローカーに接続したときの処理"""
    if rc == 0:
        print("=" * 70)
        print("MQTTブローカーに接続しました")
        print(f"ブローカー: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"接続時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # トピックを購読
        client.subscribe(TOPIC_ALL)
        print(f"\n購読トピック: {TOPIC_ALL}")
        print("\nデータ受信待機中...\n")
    else:
        print(f"接続失敗。エラーコード: {rc}")
        print("エラーの種類:")
        print("  0: 成功")
        print("  1: プロトコルバージョン不正")
        print("  2: クライアントID不正")
        print("  3: サーバー利用不可")
        print("  4: ユーザー名/パスワード不正")
        print("  5: 認証失敗")

def parse_sensor_data(payload):
    """センサーデータをパース"""
    try:
        data = json.loads(payload)

        # 基本情報
        gateway_id = data.get("gateway_id", "Unknown")
        device_addr = data.get("addr", "Unknown")
        error_code = data.get("error_code", "Unknown")
        error_msg = data.get("error", "Unknown")

        # センサーデータ
        sensor_data = data.get("data", [])
        status_code = sensor_data[0] if len(sensor_data) > 0 else "Unknown"
        status_text = sensor_data[1] if len(sensor_data) > 1 else "Unknown"
        battery_pct = sensor_data[2] if len(sensor_data) > 2 else "Unknown"

        return {
            "gateway_id": gateway_id,
            "device_addr": device_addr,
            "status_code": status_code,
            "status_text": status_text,
            "battery": battery_pct,
            "error_code": error_code,
            "error_msg": error_msg,
            "raw_data": data
        }
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析エラー: {e}", "raw_payload": payload}
    except Exception as e:
        return {"error": f"データ解析エラー: {e}", "raw_payload": payload}

def format_status_display(device_addr, status_text, battery):
    """ステータス表示を色付きでフォーマット"""
    # ステータスに応じた絵文字
    status_emoji = {
        "Running": "🟢",
        "Stop": "🟡",
        "Error": "🔴",
        "Not Working": "⚫"
    }

    emoji = status_emoji.get(status_text, "❓")

    # バッテリー残量に応じた表示
    battery_str = f"{battery}%" if isinstance(battery, (int, float)) else str(battery)
    if isinstance(battery, (int, float)):
        if battery > 50:
            battery_icon = "🔋"
        elif battery > 20:
            battery_icon = "🔋"
        else:
            battery_icon = "🪫"
    else:
        battery_icon = "🔋"

    return f"{emoji} {status_text:12} | {battery_icon} {battery_str:>5}"

def on_message(client, userdata, msg):
    """メッセージを受信したときの処理"""
    global message_count, device_status
    message_count += 1

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    topic = msg.topic
    payload = msg.payload.decode()

    print("-" * 70)
    print(f"[{timestamp}] メッセージ #{message_count}")
    print(f"トピック: {topic}")

    # センサーデータの場合は詳細表示
    if topic == TOPIC_DATA:
        parsed = parse_sensor_data(payload)

        if "error" not in parsed:
            device_addr = parsed["device_addr"]
            status_text = parsed["status_text"]
            battery = parsed["battery"]

            # デバイスステータスを更新
            device_status[device_addr] = {
                "status": status_text,
                "battery": battery,
                "last_seen": timestamp
            }

            # 見やすく表示
            print(f"デバイス: {device_addr}")
            print(f"ゲートウェイ: {parsed['gateway_id']}")
            print(f"ステータス: {format_status_display(device_addr, status_text, battery)}")
            print(f"エラーコード: {parsed['error_code']} ({parsed['error_msg']})")

            # JSONデータも表示
            print("\n受信データ (JSON):")
            print(json.dumps(parsed["raw_data"], indent=2, ensure_ascii=False))
        else:
            print(f"エラー: {parsed['error']}")
            print(f"生データ: {parsed.get('raw_payload', payload)}")
    else:
        # その他のトピックは生データを表示
        print(f"ペイロード: {payload}")
        try:
            data = json.loads(payload)
            print("\nJSON形式:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            pass

    print("-" * 70)
    print()

    # 全デバイスのステータスサマリーを表示（5メッセージごと）
    if message_count % 5 == 0 and device_status:
        print("=" * 70)
        print("接続デバイス サマリー:")
        print("=" * 70)
        for addr, info in device_status.items():
            print(f"  {addr}: {format_status_display(addr, info['status'], info['battery'])}")
            print(f"    最終更新: {info['last_seen']}")
        print("=" * 70)
        print()

def on_disconnect(client, userdata, rc):
    """MQTTブローカーから切断されたときの処理"""
    if rc != 0:
        print(f"\n予期しない切断が発生しました。エラーコード: {rc}")
        print("再接続を試みています...")

def main():
    """メイン処理"""
    print("=" * 70)
    print("ライトタワーゲートウェイ MQTTデータ受信プログラム")
    print("=" * 70)
    print(f"設定:")
    print(f"  ブローカー: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  認証: {'有効' if MQTT_USERNAME else '無効'}")
    print("=" * 70)
    print("\nCtrl+C で終了します\n")

    # Ctrl+C のハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)

    # MQTTクライアントの作成
    client = mqtt.Client(client_id="LightTower_Monitor", clean_session=True)

    # 認証が必要な場合
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # コールバック関数の設定
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        # MQTTブローカーに接続
        print(f"MQTTブローカー {MQTT_BROKER}:{MQTT_PORT} に接続中...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

        # メッセージループを開始（ブロッキング）
        client.loop_forever()

    except ConnectionRefusedError:
        print(f"\nエラー: MQTTブローカー {MQTT_BROKER}:{MQTT_PORT} に接続できませんでした")
        print("\n確認事項:")
        print("  1. Mosquittoサービスが起動しているか確認")
        print("     コマンド: net start mosquitto")
        print("  2. IPアドレスが正しいか確認")
        print(f"     現在の設定: {MQTT_BROKER}")
        print("  3. ファイアウォールがポート1883をブロックしていないか確認")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nプログラムを終了します...")
        client.disconnect()
        sys.exit(0)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
