#!/usr/bin/env python3
"""发送测试邮件的脚本。"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetchers import ArXivFetcher
from src.parsers import PaperParser
from src.pipelines import TemplateRenderer
from src.pushers import EmailPusher
from config import settings


def send_test_email(
    to_email: str,
    keywords: list = None,
    max_results: int = 3,
):
    """发送测试邮件。

    Args:
        to_email: 接收邮件的地址
        keywords: 搜索关键词
        max_results: 最大论文数
    """
    if keywords is None:
        keywords = ["llm"]

    keywords_str = " ".join(keywords)

    print(f"📧 发送测试邮件到: {to_email}")
    print(f"🔍 搜索关键词: {keywords_str}")
    print(f"📊 最多获取: {max_results} 篇论文\n")

    # 1. 获取论文
    print("1️⃣  正在获取论文...")
    fetcher = ArXivFetcher(max_results=max_results)
    papers = fetcher.fetch(keywords_str)
    print(f"   ✓ 获取到 {len(papers)} 篇论文")

    if not papers:
        print("   ✗ 未找到论文，请尝试其他关键词")
        return False

    # 2. 处理论文
    print("\n2️⃣  正在处理论文...")
    parser = PaperParser()
    processed = parser.parse_and_process(papers, merge_versions=True)
    print(f"   ✓ 处理后剩余 {len(processed)} 篇论文")

    # 3. 生成报告
    print("\n3️⃣  正在生成报告...")
    renderer = TemplateRenderer()

    from datetime import datetime
    report_date = datetime.now().strftime("%Y-%m-%d")
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = renderer.render_html_email(
        processed,
        keywords,
        report_date,
        generation_time,
    )

    text = renderer.render_summary_text(
        processed,
        keywords,
    )

    print("   ✓ 报告生成完成")

    # 4. 发送邮件
    print("\n4️⃣  正在发送邮件...")

    try:
        pusher = EmailPusher()

        subject = f"📚 学术日报测试 - {keywords[0]} ({report_date})"

        results = pusher.send_report(
            [to_email],
            subject,
            html,
            text,
        )

        if results.get("success"):
            print(f"   ✓ 邮件发送成功！")
            for email in results["success"]:
                print(f"      → {email}")

        if results.get("failed"):
            print(f"   ✗ 部分邮件发送失败")
            for fail in results["failed"]:
                print(f"      → {fail.get('email')}: {fail.get('error')}")

        return len(results.get("failed", [])) == 0

    except Exception as e:
        print(f"   ✗ 邮件发送失败: {e}")
        print("\n💡 提示：请检查 .env 文件中的邮件配置")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="发送测试邮件")
    parser.add_argument("--email", required=True, help="接收邮件的地址")
    parser.add_argument("--keywords", nargs="+", default=["llm"], help="搜索关键词")
    parser.add_argument("--max-results", type=int, default=3, help="最大论文数")

    args = parser.parse_args()

    success = send_test_email(
        to_email=args.email,
        keywords=args.keywords,
        max_results=args.max_results,
    )

    sys.exit(0 if success else 1)
