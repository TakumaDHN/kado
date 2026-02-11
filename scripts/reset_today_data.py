"""
本日6:00以降の稼働データをリセットするスクリプト
"""
import sys
import os
from datetime import datetime, timedelta
import pytz

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models import DeviceHistory

def reset_today_data():
    """本日6:00以降のDeviceHistoryデータを削除"""
    db = SessionLocal()

    try:
        # タイムゾーン設定
        jst = pytz.timezone('Asia/Tokyo')
        utc = pytz.UTC

        # 現在時刻（日本時間）
        now_jst = datetime.now(jst)
        today_date = now_jst.date()

        # 今日の6:00（日本時間）を計算
        start_time_jst = jst.localize(datetime.combine(today_date, datetime.min.time()).replace(hour=6))

        # 現在時刻が6:00より前なら、前日の6:00から
        if now_jst.hour < 6:
            start_time_jst = start_time_jst - timedelta(days=1)

        # UTCに変換（データベース検索用）
        start_time_utc = start_time_jst.astimezone(utc).replace(tzinfo=None)

        print(f"=== 稼働データリセット ===")
        print(f"削除対象期間: {start_time_jst.strftime('%Y年%m月%d日 %H:%M:%S')}（日本時間）以降")
        print(f"現在時刻: {now_jst.strftime('%Y年%m月%d日 %H:%M:%S')}（日本時間）")
        print()

        # 削除対象のレコード数を確認
        count = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp >= start_time_utc
        ).count()

        print(f"削除対象レコード数: {count}件")

        if count == 0:
            print("削除対象のデータがありません。")
            return

        # 確認
        confirm = input(f"\n本当に {count}件 のデータを削除しますか？ (yes/no): ")

        if confirm.lower() != 'yes':
            print("キャンセルしました。")
            return

        # データを削除
        deleted = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp >= start_time_utc
        ).delete(synchronize_session=False)

        db.commit()

        print(f"\n✓ {deleted}件のデータを削除しました。")
        print("=== 完了 ===")

    except Exception as e:
        print(f"エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_today_data()
