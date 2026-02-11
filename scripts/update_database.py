"""
データベースのステータステキストを更新するスクリプト
"Error" を "Stop" に変更します
"""
import sqlite3
from datetime import datetime
import os

# スクリプトのディレクトリを基準にデータベースパスを設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "lighttower.db")

def update_status_text():
    """データベース内の'Error'を'Stop'に更新し、ライトの状態を修正"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("\n[1/4] ステータステキストを更新中...")
        # DeviceStatusテーブルを更新
        cursor.execute("""
            UPDATE device_status
            SET status_text = 'Stop'
            WHERE status_text = 'Error'
        """)
        status_text_updated = cursor.rowcount
        print(f"  ✓ DeviceStatus: {status_text_updated}件")

        # DeviceHistoryテーブルを更新
        cursor.execute("""
            UPDATE device_history
            SET status_text = 'Stop'
            WHERE status_text = 'Error'
        """)
        history_text_updated = cursor.rowcount
        print(f"  ✓ DeviceHistory: {history_text_updated}件")

        print("\n[2/4] ライトの状態を修正中（status_codeに基づいて）...")
        # status_code "01" (Running) → green=1, red=0, yellow=0
        cursor.execute("""
            UPDATE device_status
            SET green = 1, red = 0, yellow = 0
            WHERE status_code = '01'
        """)
        running_updated = cursor.rowcount
        print(f"  ✓ Running (status_code=01): {running_updated}件")

        # status_code "02" (Stop - Yellow) → yellow=1, green=0, red=0
        cursor.execute("""
            UPDATE device_status
            SET yellow = 1, green = 0, red = 0
            WHERE status_code = '02'
        """)
        yellow_updated = cursor.rowcount
        print(f"  ✓ Stop Yellow (status_code=02): {yellow_updated}件")

        # status_code "03" (Stop - Red) → red=1, green=0, yellow=0
        cursor.execute("""
            UPDATE device_status
            SET red = 1, green = 0, yellow = 0
            WHERE status_code = '03'
        """)
        red_updated = cursor.rowcount
        print(f"  ✓ Stop Red (status_code=03): {red_updated}件")

        print("\n[3/4] 履歴テーブルのライトの状態を修正中...")
        # DeviceHistoryも同様に更新
        cursor.execute("""
            UPDATE device_history
            SET green = 1, red = 0, yellow = 0
            WHERE status_code = '01'
        """)
        cursor.execute("""
            UPDATE device_history
            SET yellow = 1, green = 0, red = 0
            WHERE status_code = '02'
        """)
        cursor.execute("""
            UPDATE device_history
            SET red = 1, green = 0, yellow = 0
            WHERE status_code = '03'
        """)
        print(f"  ✓ 履歴テーブルを更新しました")

        conn.commit()

        print("\n[4/4] 更新完了")
        print(f"  - 更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("データベース更新スクリプト")
    print("'Error' → 'Stop' に変更します")
    print("=" * 50)
    update_status_text()
