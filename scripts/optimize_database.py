"""
データベース最適化スクリプト
VACUUMコマンドでデータベースファイルを最適化し、パフォーマンスを改善します
"""
import os
import sqlite3
from pathlib import Path

def optimize_database():
    """データベースを最適化（VACUUM）"""
    # データベースファイルのパス
    db_file = Path(__file__).parent.parent / 'lighttower.db'

    if not db_file.exists():
        print(f"エラー: データベースファイルが見つかりません: {db_file}")
        return

    # ファイルサイズを取得（最適化前）
    size_before = os.path.getsize(db_file)
    size_before_mb = size_before / (1024 * 1024)

    print("=" * 60)
    print("データベース最適化")
    print("=" * 60)
    print()
    print(f"データベースファイル: {db_file}")
    print(f"最適化前のサイズ: {size_before_mb:.2f} MB")
    print()

    try:
        # データベースに接続
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        print("最適化を実行中...")
        print("（大きなデータベースの場合、数分かかることがあります）")
        print()

        # VACUUMコマンドを実行
        cursor.execute("VACUUM")

        # ANALYZEコマンドも実行（クエリプランナーの最適化）
        cursor.execute("ANALYZE")

        conn.commit()
        conn.close()

        # ファイルサイズを取得（最適化後）
        size_after = os.path.getsize(db_file)
        size_after_mb = size_after / (1024 * 1024)
        size_reduced = size_before - size_after
        size_reduced_mb = size_reduced / (1024 * 1024)
        reduction_percent = (size_reduced / size_before * 100) if size_before > 0 else 0

        print("✓ 最適化が完了しました")
        print()
        print(f"最適化後のサイズ: {size_after_mb:.2f} MB")
        print(f"削減されたサイズ: {size_reduced_mb:.2f} MB ({reduction_percent:.1f}%)")
        print()
        print("=" * 60)
        print("✅ 完了")
        print("=" * 60)
        print()
        print("効果:")
        print("  - データベースクエリの高速化")
        print("  - ディスク使用量の削減")
        print("  - アプリケーション全体のパフォーマンス向上")
        print()
        print("推奨: 定期的（月1回程度）に実行してください")

    except Exception as e:
        print(f"エラー: 最適化に失敗しました")
        print(f"詳細: {e}")
        print()
        print("注意: データベースが使用中の場合は失敗します")
        print("Webアプリケーションを停止してから実行してください")

if __name__ == "__main__":
    optimize_database()
