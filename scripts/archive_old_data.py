"""
古いデータをアーカイブするスクリプト
データを削除せずに別のデータベースファイルに移動します
"""
import sys
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models import DeviceHistory

def archive_old_data(months_to_keep=3):
    """指定月数より古いデータをアーカイブファイルに移動"""
    db = SessionLocal()

    try:
        # タイムゾーン設定
        jst = pytz.timezone('Asia/Tokyo')
        utc = pytz.UTC

        # アーカイブ対象の日付を計算
        cutoff_date = datetime.now(jst) - timedelta(days=months_to_keep * 30)
        cutoff_date_utc = cutoff_date.astimezone(utc).replace(tzinfo=None)

        print("=" * 70)
        print("データアーカイブ（データは削除されません）")
        print("=" * 70)
        print()
        print(f"保持期間: {months_to_keep}ヶ月")
        print(f"アーカイブ対象: {cutoff_date.strftime('%Y年%m月%d日')}（日本時間）より古いデータ")
        print()

        # アーカイブ対象のレコード数を確認
        count = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp < cutoff_date_utc
        ).count()

        print(f"アーカイブ対象レコード数: {count:,}件")

        if count == 0:
            print("アーカイブ対象のデータがありません。")
            return

        # アーカイブファイル名を生成
        project_root = Path(__file__).parent.parent
        archive_dir = project_root / 'archive'
        archive_dir.mkdir(exist_ok=True)

        archive_filename = f"lighttower_archive_{cutoff_date.strftime('%Y%m')}.db"
        archive_path = archive_dir / archive_filename

        print()
        print(f"アーカイブ先: {archive_path}")
        print()

        # 確認
        confirm = input(f"{count:,}件のデータをアーカイブしますか？ (yes/no): ")

        if confirm.lower() != 'yes':
            print("キャンセルしました。")
            return

        # メインDBからアーカイブ対象データを取得
        archive_data = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp < cutoff_date_utc
        ).all()

        # アーカイブDBに接続（存在しない場合は作成）
        archive_conn = sqlite3.connect(archive_path)
        archive_cursor = archive_conn.cursor()

        # テーブルを作成（存在しない場合）
        archive_cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                device_addr VARCHAR(12) NOT NULL,
                battery FLOAT,
                red BOOLEAN,
                yellow BOOLEAN,
                green BOOLEAN,
                status_code VARCHAR(2),
                status_text VARCHAR(50),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # アーカイブDBにデータを挿入
        print("アーカイブファイルにデータを書き込み中...")
        for record in archive_data:
            archive_cursor.execute('''
                INSERT INTO device_history
                (device_id, device_addr, battery, red, yellow, green, status_code, status_text, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.device_id,
                record.device_addr,
                record.battery,
                record.red,
                record.yellow,
                record.green,
                record.status_code,
                record.status_text,
                record.timestamp,
                record.created_at
            ))

        archive_conn.commit()
        archive_conn.close()

        print(f"✓ {count:,}件のデータをアーカイブファイルに書き込みました")

        # メインDBからデータを削除
        print("メインデータベースから古いデータを削除中...")
        deleted = db.query(DeviceHistory).filter(
            DeviceHistory.timestamp < cutoff_date_utc
        ).delete(synchronize_session=False)

        db.commit()

        print(f"✓ メインデータベースから {deleted:,}件のデータを削除しました")

        # データベースファイルサイズを表示
        main_db_file = project_root / 'lighttower.db'
        if main_db_file.exists():
            main_size = os.path.getsize(main_db_file)
            main_size_mb = main_size / (1024 * 1024)
            print(f"✓ メインDBサイズ: {main_size_mb:.2f} MB")

        archive_size = os.path.getsize(archive_path)
        archive_size_mb = archive_size / (1024 * 1024)
        print(f"✓ アーカイブDBサイズ: {archive_size_mb:.2f} MB")

        print()
        print("=" * 70)
        print("✅ アーカイブ完了")
        print("=" * 70)
        print()
        print("アーカイブされたデータ:")
        print(f"  保存場所: {archive_path}")
        print(f"  データ件数: {count:,}件")
        print()
        print("次のステップ:")
        print("  1. python scripts\\optimize_database.py を実行してDB最適化")
        print("  2. Webアプリを再起動")
        print()
        print("アーカイブデータの確認:")
        print(f"  DB Browser for SQLiteなどでファイルを開いてください")
        print(f"  パス: {archive_path}")

    except Exception as e:
        print(f"エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='古いデータをアーカイブ')
    parser.add_argument('--months', type=int, default=3,
                        help='メインDBに保持する月数（デフォルト: 3ヶ月）')

    args = parser.parse_args()

    archive_old_data(args.months)
