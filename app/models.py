"""
データベースモデル定義
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, UniqueConstraint
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


class DailyOperationRate(Base):
    """日次稼働率の集計データ（毎朝6:00に前日分を計算して保存）"""
    __tablename__ = "daily_operation_rate"
    __table_args__ = (
        UniqueConstraint('device_addr', 'target_date', name='uq_daily_op_device_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_addr = Column(String, index=True, nullable=False)
    target_date = Column(Date, index=True, nullable=False)
    running_minutes_regular = Column(Float, default=0.0)    # 定時内(8:00-翌2:00)の稼働分数
    window_minutes_regular = Column(Float, default=1080.0)  # 定時内ウィンドウ=18h=1080min
    running_minutes_overtime = Column(Float, default=0.0)   # 含残業(8:00-翌5:00)の稼働分数
    window_minutes_overtime = Column(Float, default=1260.0) # 含残業ウィンドウ=21h=1260min
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyGreenAppleCount(Base):
    """日次GREEN APPLE収穫量の集計データ（毎朝6:00に前日分を計算して保存）"""
    __tablename__ = "daily_green_apple_count"
    __table_args__ = (
        UniqueConstraint('target_date', 'location', name='uq_daily_apple_date_location'),
    )

    id = Column(Integer, primary_key=True, index=True)
    target_date = Column(Date, index=True, nullable=False)
    location = Column(String, default="", index=True)  # ""=全体, それ以外=設置場所別
    apple_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
