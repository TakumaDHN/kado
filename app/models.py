"""
データベースモデル定義
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from .database import Base


class DeviceStatus(Base):
    """デバイスの現在のステータス"""
    __tablename__ = "device_status"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, unique=True, index=True)  # デバイスID（MACアドレスから生成）
    device_addr = Column(String, unique=True, index=True)  # MACアドレス
    gateway_id = Column(String)  # ゲートウェイID
    battery = Column(Float)  # バッテリー残量 (%)
    red = Column(Boolean, default=False)  # 赤ライト
    yellow = Column(Boolean, default=False)  # 黄ライト
    green = Column(Boolean, default=False)  # 緑ライト
    status_code = Column(String)  # ステータスコード（00-03）
    status_text = Column(String)  # ステータステキスト
    last_update = Column(DateTime, default=datetime.utcnow)  # 最終更新時刻
    is_active = Column(Boolean, default=True)  # アクティブ状態


class DeviceHistory(Base):
    """デバイスの履歴データ"""
    __tablename__ = "device_history"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, index=True)  # デバイスID
    device_addr = Column(String, index=True)  # MACアドレス
    battery = Column(Float)  # バッテリー残量 (%)
    red = Column(Boolean, default=False)  # 赤ライト
    yellow = Column(Boolean, default=False)  # 黄ライト
    green = Column(Boolean, default=False)  # 緑ライト
    status_code = Column(String)  # ステータスコード（00-03）
    status_text = Column(String)  # ステータステキスト
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)  # 記録時刻

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_addr": self.device_addr,
            "battery": self.battery,
            "red": self.red,
            "yellow": self.yellow,
            "green": self.green,
            "status_code": self.status_code,
            "status_text": self.status_text,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class DeviceRegistration(Base):
    """デバイス登録情報"""
    __tablename__ = "device_registration"

    id = Column(Integer, primary_key=True, index=True)
    device_addr = Column(String, unique=True, index=True, nullable=False)  # MACアドレス
    name = Column(String, nullable=False)  # 設備名
    location = Column(String, default="")  # 設置場所
    description = Column(String, default="")  # 説明
    index = Column(Integer, default=999)  # 表示順序
    is_enabled = Column(Boolean, default=True)  # 有効/無効
    created_at = Column(DateTime, default=datetime.utcnow)  # 作成日時
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新日時
