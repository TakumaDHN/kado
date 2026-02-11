"""
データベースバックアップスクリプト
"""
import os
import shutil
from datetime import datetime
import pytz

def backup_database():
    """データベースをバックアップ"""
    # プロジェクトルート
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_file = os.path.join(project_root, 'lighttower.db')
    backup_dir = os.path.join(project_root, 'backup')

    # バックアップディレクトリを作成
    os.makedirs(backup_dir, exist_ok=True)

    # データベースファイルの存在確認
    if not os.path.exists(db_file):
        print(f"エラー: データベースファイルが見つかりません: {db_file}")
        return

    # ファイルサイズを取得
    file_size = os.path.getsize(db_file)
    file_size_mb = file_size / (1024 * 1024)

    # 日本時間で日付を取得
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    date_str = now.strftime('%Y%m%d_%H%M%S')

    # バックアップファイル名
    backup_file = os.path.join(backup_dir, f'lighttower_backup_{date_str}.db')

    print(f"=== データベースバックアップ ===")
    print(f"元ファイル: {db_file}")
    print(f"ファイルサイズ: {file_size_mb:.2f} MB")
    print(f"バックアップ先: {backup_file}")
    print()

    try:
        # コピー実行
        shutil.copy2(db_file, backup_file)
        print(f"✓ バックアップが完了しました")
        print(f"✓ 保存先: {backup_file}")
        print()
        print("=== 別PCへの移行方法 ===")
        print(f"1. このファイルを別PCにコピー:")
        print(f"   {backup_file}")
        print()
        print("2. 別PCのプロジェクトディレクトリに配置:")
        print("   lighttower.db という名前にリネーム")
        print()
        print("=== 完了 ===")

    except Exception as e:
        print(f"エラー: バックアップに失敗しました")
        print(f"詳細: {e}")

if __name__ == "__main__":
    backup_database()
