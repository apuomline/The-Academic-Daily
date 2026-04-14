#!/usr/bin/env python3
"""Test email sending functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pushers import EmailPusher
from config import settings

def test_email():
    """Test email sending."""
    print("📧 测试邮件发送功能")
    print("=" * 50)

    print(f"SMTP Host: {settings.smtp_host}")
    print(f"SMTP Port: {settings.smtp_port}")
    print(f"SMTP Username: {settings.smtp_username}")
    print(f"From Email: {settings.smtp_from_email}")
    print("=" * 50)

    try:
        pusher = EmailPusher()
        print("✓ EmailPusher 初始化成功")
    except Exception as e:
        print(f"✗ EmailPusher 初始化失败: {e}")
        return False

    # Test raw SMTP connection
    print("\n🔍 测试原始 SMTP 连接...")
    import smtplib
    import ssl

    server = None
    try:
        print(f"  尝试连接 {settings.smtp_host}:{settings.smtp_port}...")

        # Try approach 1: Direct SMTP_SSL
        print("  方式1: SMTP_SSL (直接 SSL 连接)")
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30)
        print("  ✓ SSL 连接成功")

        # Set debug level
        server.set_debuglevel(1)

        print("  尝试登录...")
        server.login(settings.smtp_username, settings.smtp_password)
        print("  ✓ 登录成功")

        server.quit()
        print("  ✓ 连接测试成功")

    except Exception as e:
        print(f"  ✗ 连接测试失败: {type(e).__name__}: {e}")
        if server:
            try:
                server.quit()
            except:
                pass
        return False

    # Test content
    html_content = """
    <html>
    <body>
        <h1>测试邮件</h1>
        <p>这是一封测试邮件，用于验证 SMTP 配置是否正确。</p>
        <p><strong>如果您收到此邮件，说明邮件发送功能正常！</strong></p>
        <hr>
        <p>发送时间: 2026-04-12</p>
    </body>
    </html>
    """

    text_content = """
    测试邮件

    这是一封测试邮件，用于验证 SMTP 配置是否正确。

    如果您收到此邮件，说明邮件发送功能正常！

    发送时间: 2026-04-12
    """

    recipient = settings.smtp_from_email
    print(f"\n📤 正在发送测试邮件到: {recipient}")

    try:
        result = pusher.send_report(
            [recipient],
            "【测试】学术日报推送系统测试",
            html_content,
            text_content,
        )

        print("\n" + "=" * 50)
        if result.get("success"):
            print(f"✓ 成功发送到 {len(result['success'])} 个邮箱")
            for email in result['success']:
                print(f"   - {email}")
        if result.get("failed"):
            print(f"✗ 失败 {len(result['failed'])} 个邮箱")
            for item in result['failed']:
                print(f"   - 邮箱: {item.get('email')}")
                print(f"     错误: {item.get('error')}")

        return len(result.get("success", [])) > 0

    except Exception as e:
        print(f"\n✗ 邮件发送异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_email()
    sys.exit(0 if success else 1)
