"""
MQTTクライアント - バックグラウンドで動作してデータを受信
"""
import paho.mqtt.client as mqtt
import json
import asyncio
import os
import uuid
from datetime import datetime
from typing import Callable
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()

# MQTT設定（環境変数から取得、デフォルトはlocalhost）
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_DATA = os.getenv("MQTT_TOPIC", "lighttower/gateway/data")


class MQTTClient:
    """MQTTクライアントクラス"""

    def __init__(self, on_message_callback: Callable = None, event_loop=None):
        """
        初期化

        Args:
            on_message_callback: メッセージ受信時のコールバック関数
            event_loop: メインスレッドのイベントループ
        """
        # ユニークなクライアントIDを生成（クライアントIDの競合を防ぐ）
        unique_id = str(uuid.uuid4())[:8]
        client_id = f"LightTower_WebApp_{unique_id}"
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.on_message_callback = on_message_callback
        self.event_loop = event_loop
        self.connected = False

        logger.info(f"MQTTクライアントID: {client_id}")

        # コールバック設定
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT接続時のコールバック"""
        if rc == 0:
            logger.info(f"MQTTブローカーに接続しました: {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
            # トピックを購読
            client.subscribe(TOPIC_DATA)
            logger.info(f"トピックを購読: {TOPIC_DATA}")
        else:
            logger.error(f"MQTT接続失敗。エラーコード: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """MQTT切断時のコールバック"""
        self.connected = False
        if rc != 0:
            logger.warning(f"予期しない切断。エラーコード: {rc}")

    def _on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        try:
            payload = msg.payload.decode()
            data = json.loads(payload)

            # ゲートウェイから送信されるデータ形式
            # {
            #   "gateway_id": "JP0000000001",
            #   "addr": "ECDA3BBE61E8",
            #   "error_code": "TMS001",
            #   "error": "Successful",
            #   "data": ["01", "Running", 85]
            # }

            if "data" in data and isinstance(data["data"], list) and len(data["data"]) >= 3:
                status_code = data["data"][0]  # "01", "02", "03", "00"
                status_text = data["data"][1]  # "Running", "Stop", "Error", "Not Working"
                battery = data["data"][2]      # バッテリー残量(%)

                # MACアドレスから数値のデバイスIDを生成（最後の4桁を使用）
                addr = data.get("addr", "Unknown")
                device_id = int(addr[-4:], 16) if addr != "Unknown" else 0

                # ステータスコードからライト状態を復元
                # 01: green=1, red=0, yellow=0 (Running)
                # 02: yellow=1, red=0, green=0 (Stop)
                # 03: red=1, green=0, yellow=0 (Stop - 旧Error)
                # 00: red=0, green=0, yellow=0 (Not Working)
                green = (status_code == "01")
                yellow = (status_code == "02")
                red = (status_code == "03")

                # ステータステキストを統一（Errorを全てStopに変更）
                if status_text == "Error" or status_code == "03":
                    status_text = "Stop"

                parsed_data = {
                    "device_id": device_id,
                    "device_addr": addr,  # MACアドレスも保存
                    "gateway_id": data.get("gateway_id", "Unknown"),
                    "status_code": status_code,
                    "status_text": status_text,
                    "battery": battery,
                    "red": red,
                    "yellow": yellow,
                    "green": green,
                    "timestamp": datetime.utcnow()
                }
            else:
                logger.warning(f"未知のデータ形式: {data}")
                return

            logger.info(f"受信データ: Device={parsed_data['device_addr']}, Status={status_text}, Battery={battery}%")

            # コールバック実行
            if self.on_message_callback:
                # スレッドセーフに非同期タスクを実行
                try:
                    if self.event_loop:
                        asyncio.run_coroutine_threadsafe(self.on_message_callback(parsed_data), self.event_loop)
                    else:
                        logger.warning("イベントループが設定されていません")
                except Exception as e:
                    logger.error(f"コールバック実行エラー: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")

    def start(self):
        """MQTTクライアントを開始"""
        try:
            logger.info(f"MQTTブローカーに接続中: {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            # 非ブロッキングループを開始
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT接続エラー: {e}")
            raise

    def stop(self):
        """MQTTクライアントを停止"""
        logger.info("MQTTクライアントを停止中...")
        self.client.loop_stop()
        self.client.disconnect()
