"""
古いデータをクリーンアップするスクリプト
データベースのパフォーマンスを改善します
"""
import sys
import os
from datetime import datetime, timedelta
import pytz

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models import DeviceHistory

def cleanup_old_data(days_to_keep=30):
    """指定日数より古いデータを削除"""
    db = SessionLocal()

    try:
        # タイムゾーン設定
        jst = pytz.timezone('Asia/Tokyo')
        utc = pytz.UTC

        # 保持期間の計算
        cutoff_date = datetime.now(jst) - timedelta(days=days_to_keep)
        cutoff_date_utc = cutoff_date.astimezone(utc).replace(tzinfo=None)

        print(f"=== データクリーンアップ ===")
        print(f"保持期間: {days_to_keep}日")
        print(f"削除対象: {cutoff_date.strftime('%Y年%m月%d日')}（日本時間）より古いデータ")
        print()

        # 削除対象のレコード数を確認
        count = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp < cutoff_date_utc
        ).count()

        print(f"削除対象レコード数: {count:,}件")

        if count == 0:
            print("削除対象のデータがありません。")
            return

        # 確認
        confirm = input(f"\n本当に {count:,}件 のデータを削除しますか？ (yes/no): ")

        if confirm.lower() != 'yes':
            print("キャンセルしました。")
            return

        # データを削除
        deleted = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp < cutoff_date_utc
        ).delete(synchronize_session=False)

        db.commit()

        print(f"\n✓ {deleted:,}件のデータを削除しました。")

        # データベースファイルサイズを表示
        db_file = os.path.join(os.path.dirname(__file__), '..', 'lighttower.db')
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            file_size_mb = file_size / (1024 * 1024)
            print(f"✓ データベースサイズ: {file_size_mb:.2f} MB")

        print("\n推奨: VACUUMコマンドでデータベースを最適化")
        print("SQLiteブラウザまたは以下のコマンドを実行:")
        print("  sqlite3 lighttower.db \"VACUUM;\"")
        print()
        print("=== 完了 ===")

    except Exception as e:
        print(f"エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='古いデータをクリーンアップ')
    parser.add_argument('--days', type=int, default=30,
                        help='保持する日数（デフォルト: 30日）')

    args = parser.parse_args()

    cleanup_old_data(args.days)
