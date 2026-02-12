"""
Webアプリケーション接続診断スクリプト（クライアント側）
"""
import socket
import sys

print("=" * 60)
print("Webアプリケーション接続診断")
print("=" * 60)
print()

# サーバーのIPアドレスを入力
server_ip = input("サーバーのIPアドレスを入力してください（例: 192.168.1.100）: ").strip()
server_port = 8000

print()
print(f"📋 接続情報:")
print(f"  - サーバー: {server_ip}")
print(f"  - ポート: {server_port}")
print()

# 1. Ping確認
print(f"🔍 Ping確認:")
import subprocess
try:
    result = subprocess.run(
        ["ping", "-n", "3", server_ip],
        capture_output=True,
        text=True,
        timeout=10
    )
    if "Reply from" in result.stdout or "からの応答" in result.stdout:
        print(f"  ✓ {server_ip} に到達可能")
    else:
        print(f"  ✗ {server_ip} に到達できません")
        print(f"  原因:")
        print(f"    - IPアドレスが間違っている")
        print(f"    - ネットワークが異なる（VLAN/セグメント）")
        print(f"    - サーバーPCがオフラインまたはネットワークに接続されていない")
except Exception as e:
    print(f"  ✗ Ping失敗: {e}")
print()

# 2. ポート接続確認
print(f"🔌 ポート {server_port} 接続確認:")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
result = sock.connect_ex((server_ip, server_port))
sock.close()

if result == 0:
    print(f"  ✓ ポート {server_port} に接続できました")
    print()
    print("=" * 60)
    print("✅ 診断完了: 接続可能です")
    print("=" * 60)
    print()
    print(f"ブラウザで以下のURLにアクセスしてください:")
    print(f"  http://{server_ip}:{server_port}")
    print()
    print("それでも表示されない場合:")
    print("  1. ブラウザのキャッシュをクリア（Ctrl+Shift+Delete）")
    print("  2. シークレットモード/プライベートブラウジングで試す")
    print("  3. 別のブラウザで試す")
else:
    print(f"  ✗ ポート {server_port} に接続できません")
    print()
    print("=" * 60)
    print("❌ 診断完了: 接続できません")
    print("=" * 60)
    print()
    print("考えられる原因:")
    print("  1. サーバーPCのファイアウォールでポート8000がブロックされている")
    print("  2. サーバーPCのWebアプリが起動していない")
    print("  3. ネットワークセグメントが異なる（VLAN設定）")
    print("  4. このPCのセキュリティソフトが送信接続をブロックしている")
    print()
    print("解決策:")
    print("  1. サーバーPCでファイアウォール規則を確認:")
    print("     PowerShell（管理者）で実行:")
    print("     New-NetFirewallRule -DisplayName \"ライトタワー監視システム\" \\")
    print("       -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any")
    print()
    print("  2. サーバーPCでWebアプリが起動しているか確認")
    print()
    print("  3. IT部門にネットワーク設定を確認")
    sys.exit(1)

# 3. HTTP接続確認
print()
print(f"🌐 HTTP接続確認:")
try:
    import urllib.request
    url = f"http://{server_ip}:{server_port}/health"
    print(f"  接続中: {url}")

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req, timeout=5)

    if response.status == 200:
        print(f"  ✓ HTTP接続成功（ステータス: {response.status}）")
        print()
        print("=" * 60)
        print("✅ すべての診断が成功しました")
        print("=" * 60)
        print()
        print(f"ブラウザで以下のURLにアクセスしてください:")
        print(f"  http://{server_ip}:{server_port}")
    else:
        print(f"  ! HTTP応答あり（ステータス: {response.status}）")
except urllib.error.URLError as e:
    print(f"  ! HTTP接続エラー: {e}")
    print(f"  ポート接続は成功しましたが、Webアプリが応答していません")
    print()
    print("サーバーPCでWebアプリが正常に起動しているか確認してください:")
    print("  uvicorn app.main:app --host 0.0.0.0 --port 8000")
except Exception as e:
    print(f"  ✗ エラー: {e}")

print()
