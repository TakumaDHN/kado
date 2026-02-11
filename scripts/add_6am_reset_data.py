"""
本日6:00 JSTにすべての設備を休止状態（Not Working）にするデータを追加
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import pytz
from app.models import DeviceStatus, DeviceHistory, Base
from app.device_config import get_all_devices_from_db

# データベース接続
engine = create_engine('sqlite:///lighttower.db')
Session = sessionmaker(bind=engine)

def add_6am_reset_data():
    """本日6:00にすべての設備を休止状態にするデータを追加"""
    session = Session()

    try:
        # タイムゾーン設定
        jst = pytz.timezone('Asia/Tokyo')
        utc = pytz.UTC

        # 本日の6:00 JST
        now_jst = datetime.now(jst)
        today_6am_jst = jst.localize(datetime.combine(now_jst.date(), datetime.min.time())).replace(hour=6)
        today_6am_utc = today_6am_jst.astimezone(utc).replace(tzinfo=None)

        print("=== 本日6:00の休止状態データ追加開始 ===")
        print(f"対象時刻: {today_6am_jst.strftime('%Y-%m-%d %H:%M:%S JST')}")
        print(f"UTC時刻: {today_6am_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # すべてのデバイスを取得
        all_devices = get_all_devices_from_db(session)

        if not all_devices:
            print("登録されているデバイスがありません")
            return

        added_count = 0

        for device_addr, device_info in all_devices.items():
            # デバイスIDを生成
            device_id = int(device_addr[-4:], 16)
            device_name = device_info.get("name", "Unknown")

            # 既に同じ時刻のデータが存在するか確認
            existing = session.query(DeviceHistory).filter(
                DeviceHistory.device_addr == device_addr,
                DeviceHistory.timestamp == today_6am_utc
            ).first()

            if existing:
                print(f"  [SKIP] {device_name} ({device_addr}): 6:00のデータは既に存在します")
                continue

            # 休止状態のデータを追加
            history_entry = DeviceHistory(
                device_id=device_id,
                device_addr=device_addr,
                battery=100.0,  # デフォルト値
                red=False,
                yellow=False,
                green=False,
                status_code="00",
                status_text="Not Working",
                timestamp=today_6am_utc
            )
            session.add(history_entry)

            print(f"  [OK] {device_name} ({device_addr}): 休止状態データを追加")
            added_count += 1

        session.commit()

        print(f"\n=== 完了: {added_count}台のデバイスに6:00の休止状態データを追加しました ===")

        # 追加されたデータを確認
        print("\n追加されたデータ:")
        print("-" * 100)
        results = session.query(DeviceHistory).filter(
            DeviceHistory.timestamp == today_6am_utc
        ).all()

        for result in results:
            print(f"{result.timestamp} | {result.device_addr} | {result.status_text:15} | "
                  f"R:{result.red} Y:{result.yellow} G:{result.green} | Bat:{result.battery}%")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_6am_reset_data()
