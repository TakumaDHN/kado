"""
重複した履歴データをクリーンアップするスクリプト
同じタイムスタンプ・同じデバイス・同じステータスの重複エントリを削除
"""
import sqlite3
from datetime import datetime

def cleanup_duplicates():
    """重複した履歴エントリを削除"""
    conn = sqlite3.connect('lighttower.db')
    cursor = conn.cursor()

    print("=== 重複履歴データのクリーンアップ開始 ===\n")

    # クリーンアップ前のレコード数を取得
    cursor.execute("SELECT COUNT(*) FROM device_history")
    before_count = cursor.fetchone()[0]
    print(f"クリーンアップ前のレコード数: {before_count}")

    # 重複を削除（最小のIDを残して、それ以外を削除）
    # タイムスタンプ、デバイスアドレス、ライト状態が同じものを重複とみなす
    cursor.execute("""
        DELETE FROM device_history
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM device_history
            GROUP BY datetime(timestamp), device_addr, red, yellow, green, status_code, battery
        )
    """)

    deleted_count = cursor.rowcount
    conn.commit()

    # クリーンアップ後のレコード数を取得
    cursor.execute("SELECT COUNT(*) FROM device_history")
    after_count = cursor.fetchone()[0]

    print(f"削除したレコード数: {deleted_count}")
    print(f"クリーンアップ後のレコード数: {after_count}")

    # 最新10件を表示
    print("\n最新10件の履歴:")
    print("-" * 100)
    cursor.execute("""
        SELECT timestamp, device_addr, status_text, red, yellow, green, battery, status_code
        FROM device_history
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    for row in cursor.fetchall():
        timestamp = row[0]
        device_addr = row[1]
        status_text = row[2]
        red = row[3]
        yellow = row[4]
        green = row[5]
        battery = row[6]
        status_code = row[7]

        print(f"{timestamp} | {device_addr} | {status_text:15} | R:{red} Y:{yellow} G:{green} | Bat:{battery}% | Code:{status_code}")

    conn.close()
    print("\n=== クリーンアップ完了 ===")

if __name__ == "__main__":
    cleanup_duplicates()
