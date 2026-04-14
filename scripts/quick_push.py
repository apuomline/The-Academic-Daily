#!/usr/bin/env python3
"""超简单推送脚本 - 只需输入邮箱地址。"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetchers import ArXivFetcher
from src.parsers import PaperParser
from src.pipelines import TemplateRenderer
from src.pushers import EmailPusher
from config import settings


def quick_push(email: str, keywords: list = None):
    """快速推送：只需输入邮箱地址。

    Args:
        email: 接收邮件的地址
        keywords: 搜索关键词（默认：llm）
    """
    if keywords is None:
        keywords = ["llm"]

    keywords_str = " ".join(keywords)
    max_results = 3

    print("=" * 60)
    print("📧 学术论文推送助手")
    print("=" * 60)
    print(f"📮 发送到: {email}")
    print(f"🔍 关键词: {keywords_str}")
    print(f"📊 论文数: {max_results}")
    print()

    # 检查邮件配置
    if not settings.email_enabled:
        print("❌ 错误：邮件功能未启用")
        print()
        print("请在 .env 文件中添加以下配置：")
        print()
        print("EMAIL_ENABLED=true")
        print("SMTP_HOST=smtp.qq.com")
        print("SMTP_PORT=587")
        print("SMTP_USERNAME=your-email@qq.com")
        print("SMTP_PASSWORD=your-authorization-code")
        print("SMTP_FROM_EMAIL=your-email@qq.com")
        return False

    # 1. 获取论文
    print("1️⃣  获取论文...")
    fetcher = ArXivFetcher(max_results=max_results)
    papers = fetcher.fetch(keywords_str)

    if not papers:
        print("   ❌ 未找到论文，请尝试其他关键词")
        return False

    print(f"   ✅ 找到 {len(papers)} 篇论文")

    # 2. 处理论文
    print("2️⃣  处理论文...")
    parser = PaperParser()
    processed = parser.parse_and_process(papers, merge_versions=True)
    print(f"   ✅ 处理后 {len(processed)} 篇")

    # 3. 生成邮件
    print("3️⃣ 生成邮件...")
    from datetime import datetime

    renderer = TemplateRenderer()
    html = renderer.render_html_email(
        processed,
        keywords,
        datetime.now().strftime("%Y-%m-%d"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    text = renderer.render_summary_text(processed, keywords)

    print("   ✅ 邮件已生成")

    # 4. 发送邮件
    print("4️⃣  发送邮件...")

    try:
        pusher = EmailPusher()

        subject = f"📚 学术日报 - {keywords[0]} ({datetime.now().strftime('%Y/%m/%d')})"

        results = pusher.send_report(
            [email],
            subject,
            html,
            text,
        )

        if results.get("success"):
            print(f"   ✅ 发送成功！")
            print()
            print("📧 请检查您的邮箱（可能在收件箱或垃圾箱）")
            return True

        if results.get("failed"):
            print(f"   ❌ 发送失败")
            for fail in results["failed"]:
                print(f"      错误: {fail.get('error')}")
            return False

    except Exception as e:
        print(f"   ❌ 发送失败: {e}")
        print()
        print("💡 提示：请检查 .env 文件中的邮件配置是否正确")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="超简单推送 - 只需输入邮箱地址",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 推送 llm 相关论文
  python scripts/quick_push.py your@email.com

  # 推送指定主题
  python scripts/quick_push.py your@email.com --keywords llm vision

  # 推送更多论文
  python scripts/quick_push.py your@email.com --max-results 5
        """
    )

    parser.add_argument("email", help="接收邮件的邮箱地址")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=["llm"],
        help="搜索关键词（默认：llm）",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="最大论文数（默认：3）",
    )

    args = parser.parse_args()

    success = quick_push(args.email, args.keywords)

    sys.exit(0 if success else 1)
