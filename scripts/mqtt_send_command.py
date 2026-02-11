#!/usr/bin/env python3
"""
ライトタワーゲートウェイ MQTTコマンド送信スクリプト

このスクリプトは、ゲートウェイにMQTT経由でコマンドを送信します。

使用方法:
    python mqtt_send_command.py [command]

コマンド:
    heartbeat  - ゲートウェイの生存確認（デフォルト）
    status     - ステータス確認
"""

import paho.mqtt.client as mqtt
import json
import sys
import time
from datetime import datetime

# MQTT設定
MQTT_BROKER = "localhost"  # または "192.168.2.1" など
MQTT_PORT = 1883
MQTT_USERNAME = None
MQTT_PASSWORD = None

# トピック
TOPIC_COMMAND = "lighttower/gateway/command"
TOPIC_DATA = "lighttower/gateway/data"

# グローバル変数
response_received = False
client_instance = None

def on_connect(client, userdata, flags, rc):
    """MQTTブローカーに接続したときの処理"""
    if rc == 0:
        print(f"✓ MQTTブローカーに接続しました ({MQTT_BROKER}:{MQTT_PORT})")
        # 応答を受信するためにトピックを購読
        client.subscribe(TOPIC_DATA)
        print(f"✓ 応答トピックを購読: {TOPIC_DATA}\n")
    else:
        print(f"✗ 接続失敗。エラーコード: {rc}")
        sys.exit(1)

def on_message(client, userdata, msg):
    """メッセージを受信したときの処理"""
    global response_received

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    topic = msg.topic
    payload = msg.payload.decode()

    print("-" * 60)
    print(f"[{timestamp}] ゲートウェイから応答を受信")
    print(f"トピック: {topic}")

    try:
        data = json.loads(payload)
        print("\n応答データ (JSON):")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # heartbeat応答の場合
        if "data" in data and isinstance(data["data"], list) and "pong" in data["data"]:
            print("\n✓ Heartbeat応答: pong を受信しました")
            response_received = True
    except json.JSONDecodeError:
        print(f"\n生データ: {payload}")

    print("-" * 60)
    print()

def send_heartbeat(client):
    """Heartbeatコマンドを送信"""
    trans_code = str(int(time.time()))

    command = {
        "comp_id": "JP0001",
        "lang": "jp",
        "trans_code": trans_code,
        "client_tp": "python_test",
        "object": "gateway",
        "funct": "heartbeat",
        "input": []
    }

    payload = json.dumps(command, ensure_ascii=False)

    print("=" * 60)
    print("Heartbeatコマンドを送信します")
    print("=" * 60)
    print(f"トピック: {TOPIC_COMMAND}")
    print(f"ペイロード:\n{json.dumps(command, indent=2, ensure_ascii=False)}")
    print("=" * 60)
    print()

    result = client.publish(TOPIC_COMMAND, payload)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print("✓ コマンドを送信しました")
        print(f"  メッセージID: {result.mid}")
        print(f"  トランザクションコード: {trans_code}")
        print("\nゲートウェイからの応答を待機中...\n")
        return True
    else:
        print(f"✗ 送信失敗。エラーコード: {result.rc}")
        return False

def send_status_request(client):
    """ステータス確認コマンドを送信"""
    trans_code = str(int(time.time()))

    command = {
        "comp_id": "JP0001",
        "lang": "jp",
        "trans_code": trans_code,
        "client_tp": "python_test",
        "object": "gateway",
        "funct": "status",
        "input": []
    }

    payload = json.dumps(command, ensure_ascii=False)

    print("=" * 60)
    print("ステータス確認コマンドを送信します")
    print("=" * 60)
    print(f"トピック: {TOPIC_COMMAND}")
    print(f"ペイロード:\n{json.dumps(command, indent=2, ensure_ascii=False)}")
    print("=" * 60)
    print()

    result = client.publish(TOPIC_COMMAND, payload)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print("✓ コマンドを送信しました")
        print(f"  メッセージID: {result.mid}")
        return True
    else:
        print(f"✗ 送信失敗。エラーコード: {result.rc}")
        return False

def main():
    """メイン処理"""
    global client_instance

    # コマンドライン引数からコマンドを取得
    command = "heartbeat"
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

    print("=" * 60)
    print("ライトタワーゲートウェイ MQTTコマンド送信プログラム")
    print("=" * 60)
    print(f"設定:")
    print(f"  ブローカー: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  コマンド: {command}")
    print("=" * 60)
    print()

    # MQTTクライアントの作成
    client = mqtt.Client(client_id="LightTower_Commander", clean_session=True)
    client_instance = client

    # 認証が必要な場合
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # コールバック関数の設定
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # MQTTブローカーに接続
        print(f"MQTTブローカー {MQTT_BROKER}:{MQTT_PORT} に接続中...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

        # バックグラウンドでメッセージループを開始
        client.loop_start()

        # 接続を待つ
        time.sleep(1)

        # コマンドを送信
        if command == "heartbeat":
            success = send_heartbeat(client)
        elif command == "status":
            success = send_status_request(client)
        else:
            print(f"✗ 未知のコマンド: {command}")
            print("使用可能なコマンド: heartbeat, status")
            client.loop_stop()
            client.disconnect()
            sys.exit(1)

        if not success:
            client.loop_stop()
            client.disconnect()
            sys.exit(1)

        # 応答を待つ（最大10秒）
        timeout = 10
        elapsed = 0
        while not response_received and elapsed < timeout:
            time.sleep(0.5)
            elapsed += 0.5

        if response_received:
            print("\n✓ テスト成功: ゲートウェイとの通信が確認できました")
        else:
            print(f"\n⚠ タイムアウト: {timeout}秒以内に応答がありませんでした")
            print("\n確認事項:")
            print("  1. ゲートウェイデバイスが起動しているか")
            print("  2. ゲートウェイがMQTTブローカーに接続されているか")
            print("  3. ネットワーク設定が正しいか")

        # クリーンアップ
        client.loop_stop()
        client.disconnect()

    except ConnectionRefusedError:
        print(f"\n✗ エラー: MQTTブローカー {MQTT_BROKER}:{MQTT_PORT} に接続できませんでした")
        print("\n確認事項:")
        print("  1. Mosquittoサービスが起動しているか")
        print("     コマンド: net start mosquitto")
        print("  2. IPアドレスが正しいか")
        print(f"     現在の設定: {MQTT_BROKER}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nプログラムを中断しました")
        if client_instance:
            client_instance.loop_stop()
            client_instance.disconnect()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
