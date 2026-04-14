#!/usr/bin/env python3
"""Academic Paper Pusher - Main entry script (Phase 2).

This script orchestrates the pipeline:
1. Fetch papers from multiple sources (arXiv, OpenAlex, Semantic Scholar)
2. Parse and deduplicate papers
3. Save to database
4. Generate summaries using LLM
5. Send email reports to subscribers
6. Support scheduled/automated execution
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.database import db_manager
from src.fetchers import ArXivFetcher, OpenAlexFetcher, SemanticScholarFetcher
from src.parsers import PaperParser, PDFParser
from src.summarizers import create_summarizer, SummaryResult
from src.pipelines import DailyReportPipeline, TemplateRenderer, create_scheduler


# ==================== 日志配置 ====================
class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器."""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    BOLD_COLORS = {
        'DEBUG': '\033[1;36m',
        'INFO': '\033[1;32m',
        'WARNING': '\033[1;33m',
        'ERROR': '\033[1;31m',
        'CRITICAL': '\033[1;35m',
    }
    RESET = '\033[0m'

    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.BOLD_COLORS:
            record.levelname = f"{self.BOLD_COLORS[levelname]}{levelname:<8}{self.RESET}"
        return super().format(record)


def setup_logging(log_level="INFO"):
    """配置日志系统."""
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # 创建彩色格式化器
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # 添加处理器
    root_logger.addHandler(console_handler)

    # 配置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

    return root_logger


# 初始化日志
logger = setup_logging(settings.log_level)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Academic Paper Pusher - Generate daily research paper reports (Phase 2)"
    )

    parser.add_argument(
        "keywords",
        nargs="*",
        help="Search keywords (e.g., 'medical image segmentation')",
    )

    # Data source options
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["arxiv", "openalex", "semantic_scholar", "all"],
        default=["arxiv"],
        help="Data sources to fetch from (default: arxiv)",
    )

    parser.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Date range in YYYYMMDD format (e.g., 20260411 20260412)",
    )

    parser.add_argument(
        "--last-24h",
        action="store_true",
        help="Fetch papers from the last 24 hours",
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        help="arXiv categories (e.g., cs.CV cs.LG)",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=settings.arxiv_max_results,
        help=f"Maximum number of results per source (default: {settings.arxiv_max_results})",
    )

    # LLM options
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "bigmodel", "zhipu"],
        default=settings.llm_provider,
        help=f"LLM provider (default: {settings.llm_provider})",
    )

    parser.add_argument(
        "--model",
        default=settings.llm_model,
        help=f"LLM model name (default: {settings.llm_model})",
    )

    # Output options
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: output/DAILY_REPORT_YYYY-MM-DD.md)",
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "html", "text", "all"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Do not merge different versions of the same paper",
    )

    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Keywords to exclude from results",
    )

    # Database options
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables",
    )

    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database operations",
    )

    # Email options
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send report via email",
    )

    parser.add_argument(
        "--email",
        type=str,
        help="Email address to send report to (for testing)",
    )

    # Scheduler options
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in scheduled mode (daemon)",
    )

    parser.add_argument(
        "--schedule-time",
        type=str,
        default="02:00",
        help="Daily run time in HH:MM format (default: 02:00)",
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon",
    )

    # Pipeline options
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Run full daily pipeline (fetch, summarize, send)",
    )

    return parser.parse_args()


def init_database():
    """Initialize database tables."""
    logger.info("=" * 60)
    logger.info("🗄️  初始化数据库")
    logger.info("=" * 60)
    db_manager.create_tables()
    logger.info(f"✅ 数据库已初始化: {db_manager.database_url}")
    logger.info("=" * 60)


def run_single_fetch(args):
    """Run single paper fetch and report generation.

    Args:
        args: Parsed command line arguments
    """
    keywords = args.keywords if args.keywords else ["llm"]
    keywords_str = " ".join(keywords)

    logger.info("=" * 60)
    logger.info("🔍 学术论文推送助手 (Phase 2)")
    logger.info("=" * 60)
    logger.info(f"📝 搜索关键词: {keywords_str}")
    logger.info(f"📡 数据源: {', '.join(args.sources)}")
    logger.info(f"🤖 LLM 提供商: {args.provider}")
    logger.info(f"🧠 LLM 模型: {args.model}")
    logger.info("=" * 60)

    # Initialize fetchers
    fetchers = {
        "arxiv": ArXivFetcher(
            api_url=settings.arxiv_api_url,
            max_results=args.max_results,
        ),
        "openalex": OpenAlexFetcher(max_results=args.max_results),
        "semantic_scholar": SemanticScholarFetcher(max_results=args.max_results),
    }

    # Select sources
    sources_to_fetch = args.sources
    if "all" in sources_to_fetch:
        sources_to_fetch = ["arxiv", "openalex", "semantic_scholar"]

    # Fetch papers
    logger.info("📥 开始获取论文...")
    all_papers = []
    for source in sources_to_fetch:
        logger.info(f"  → 从 {source} 获取...")
        fetcher = fetchers[source]

        try:
            if source == "arxiv":
                if args.last_24h:
                    papers = fetcher.fetch_last_24h(keywords_str, categories=args.categories)
                elif args.date_range:
                    papers = fetcher.fetch(
                        keywords_str,
                        date_range=tuple(args.date_range),
                        categories=args.categories,
                    )
                else:
                    papers = fetcher.fetch(
                        keywords_str,
                        categories=args.categories,
                        max_results=args.max_results,
                    )
            else:
                # OpenAlex and Semantic Scholar don't support all options
                papers = fetcher.fetch(keywords_str, max_results=args.max_results)

            logger.info(f"     ✓ 获取到 {len(papers)} 篇论文")
            all_papers.extend(papers)

        except Exception as e:
            logger.error(f"     ✗ 获取失败: {e}")

    if not all_papers:
        logger.warning("⚠️  未找到匹配的论文")
        return 1

    logger.info(f"✓ 总共获取到 {len(all_papers)} 篇论文")

    # Parse and deduplicate
    logger.info("🔧 正在处理论文（去重、合并版本）...")
    parser = PaperParser()

    processed_papers = parser.parse_and_process(
        all_papers,
        merge_versions=not args.no_merge,
        filter_keywords=keywords,
        exclude_keywords=args.exclude,
    )

    logger.info(f"  ✓ 处理后剩余 {len(processed_papers)} 篇论文")

    # Generate LLM summaries
    if processed_papers:
        logger.info("🤖 正在使用 LLM 生成结构化中文摘要...")
        summarizer = create_summarizer(
            provider=args.provider,
            model=args.model,
        )

        # Initialize PDF parser
        pdf_parser = PDFParser()

        papers_to_keep = []
        skipped_count = 0

        for i, paper in enumerate(processed_papers, 1):
            try:
                # Try to download and parse PDF for introduction
                intro_text = None
                has_pdf = False

                if paper.pdf_url:
                    result = pdf_parser.parse_paper(paper.arxiv_id, paper.pdf_url)
                    intro_text = result.get("intro_text")
                    has_pdf = result.get("success", False)
                    if has_pdf:
                        logger.info(f"  [{i:2d}/{len(processed_papers)}] ✓ {paper.title[:50]}...")
                    else:
                        logger.warning(f"  [{i:2d}/{len(processed_papers)}] ✗ PDF 下载失败，跳过: {paper.title[:50]}...")
                        skipped_count += 1
                        continue

                # Call LLM to generate structured summary
                summary_result = summarizer.summarize_structured(
                    title=paper.title,
                    abstract=paper.abstract,
                    intro_text=intro_text,
                )

                if summary_result.success:
                    # Attach structured summary to paper
                    paper.summary_structured = summary_result.summary
                    paper.summary_content = summary_result.summary.abstract_translation
                    papers_to_keep.append(paper)

                    if not has_pdf:
                        logger.info(f"  [{i:2d}/{len(processed_papers)}] ... {paper.title[:50]}...")
                else:
                    logger.warning(f"  ⚠️  摘要生成失败: {paper.arxiv_id}: {summary_result.error}")
                    # Still keep the paper but without structured summary
                    papers_to_keep.append(paper)

            except Exception as e:
                logger.warning(f"  ⚠️  处理失败 {paper.arxiv_id}: {e}")
                # Still keep the paper
                papers_to_keep.append(paper)

        # Update processed_papers to only include successfully processed ones
        processed_papers = papers_to_keep

        logger.info(f"  ✓ 完成了 {len(processed_papers)} 篇论文的摘要生成")
        if skipped_count > 0:
            logger.warning(f"  ⚠️  跳过了 {skipped_count} 篇 PDF 下载失败的论文")

    # Save to database
    if not args.no_db:
        logger.info("💾 正在保存到数据库...")
        session = db_manager.get_session()

        try:
            from src.database import PaperCRUD

            saved_count = 0
            for paper in processed_papers:
                try:
                    PaperCRUD.upsert_paper(
                        session,
                        arxiv_id=paper.arxiv_id,
                        title=paper.title,
                        abstract=paper.abstract,
                        source=paper.source,
                        published_date=paper.published_date,
                        updated_date=paper.updated_date,
                    )
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"  ✗ 保存失败: {e}")

            session.commit()
            logger.info(f"  ✓ 保存了 {saved_count} 篇论文到数据库")

        except Exception as e:
            session.rollback()
            logger.error(f"  ✗ 数据库保存失败: {e}")
        finally:
            session.close()

    # Generate report
    logger.info("📝 正在生成报告...")
    renderer = TemplateRenderer()

    report_date = datetime.now().strftime("%Y-%m-%d")
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    markdown = renderer.render_markdown(
        processed_papers,
        keywords,
        report_date,
        generation_time,
    )

    html = renderer.render_html_email(
        processed_papers,
        keywords,
        report_date,
        generation_time,
    )

    text = renderer.render_summary_text(
        processed_papers,
        keywords,
    )

    # Output report
    logger.info("💾 正在保存报告...")

    if args.format in ["markdown", "all"]:
        output_path = args.output or Path(settings.output_dir) / f"DAILY_REPORT_{report_date}.md"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(markdown, encoding="utf-8")
        logger.info(f"  ✓ Markdown: {output_path}")

    if args.format in ["html", "all"]:
        output_path = args.output or Path(settings.output_dir) / f"DAILY_REPORT_{report_date}.html"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html, encoding="utf-8")
        logger.info(f"  ✓ HTML: {output_path}")

    if args.format in ["text", "all"]:
        output_path = args.output or Path(settings.output_dir) / f"DAILY_REPORT_{report_date}.txt"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(text, encoding="utf-8")
        logger.info(f"  ✓ Text: {output_path}")

    # Send email if requested
    if args.send_email or args.email:
        logger.info("📧 正在发送邮件...")

        try:
            from src.pushers import EmailPusher

            pusher = EmailPusher()

            subject = f"学术日报 {report_date} - {keywords[0]}"
            recipients = [args.email] if args.email else [settings.smtp_from_email]

            results = pusher.send_report(
                recipients,
                subject,
                html,
                text,
            )

            if results.get("success"):
                logger.info(f"  ✓ 成功发送到 {len(results['success'])} 个邮箱")
                for email in results['success']:
                    logger.info(f"     → {email}")
            if results.get("failed"):
                logger.error(f"  ✗ 失败: {len(results['failed'])} 个邮箱")
                for item in results['failed']:
                    logger.error(f"     ✗ {item.get('email')}: {item.get('error')}")

        except Exception as e:
            logger.error(f"  ✗ 邮件发送失败: {e}")

    logger.info("=" * 60)
    logger.info("✨ 完成!")
    logger.info("=" * 60)

    return 0


def run_pipeline(args):
    """Run the full daily pipeline.

    Args:
        args: Parsed command line arguments
    """
    keywords = args.keywords if args.keywords else ["llm"]
    exclude = args.exclude if hasattr(args, "exclude") else None

    logger.info("=" * 60)
    logger.info("🚀 启动每日流水线")
    logger.info("=" * 60)
    logger.info(f"📝 关键词: {', '.join(keywords)}")
    if exclude:
        logger.info(f"🚫 排除: {', '.join(exclude)}")
    logger.info("=" * 60)

    pipeline = DailyReportPipeline()
    results = pipeline.run_daily_pipeline(keywords, exclude)

    logger.info("=" * 60)
    logger.info("📊 流水线结果:")
    logger.info(f"  获取论文: {results.get('papers_fetched', 0)} 篇")
    logger.info(f"  生成报告: {'是' if results.get('reports_generated') else '否'}")
    logger.info(f"  发送成功: {results.get('emails_sent', 0)} 个")
    logger.info(f"  发送失败: {results.get('emails_failed', 0)} 个")
    if results.get("errors"):
        logger.error(f"  错误: {', '.join(results['errors'])}")
    logger.info("=" * 60)

    return 0 if not results.get("errors") else 1


def run_scheduled(args):
    """Run in scheduled mode.

    Args:
        args: Parsed command line arguments
    """
    logger.info("=" * 60)
    logger.info("⏰ 启动定时调度模式")
    logger.info("=" * 60)

    # Parse schedule time
    hour, minute = map(int, args.schedule_time.split(":"))
    logger.info(f"🕐 每日运行时间: {args.schedule_time}")

    # Create scheduler
    scheduler = create_scheduler(daily_hour=hour, daily_minute=minute)

    # Define job function
    def daily_job():
        keywords = args.keywords if args.keywords else ["llm"]
        exclude = args.exclude if hasattr(args, "exclude") else None

        logger.info("⏰ 执行定时任务...")
        pipeline = DailyReportPipeline()
        pipeline.run_daily_pipeline(keywords, exclude)

    # Add job
    scheduler.add_daily_job(daily_job, hour=hour, minute=minute)

    # Start scheduler
    try:
        logger.info("✅ 调度器已启动，按 Ctrl+C 停止")
        logger.info("=" * 60)
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("🛑 用户停止调度器")
        logger.info("=" * 60)
        scheduler.shutdown()

    return 0


def main():
    """Main entry point."""
    args = parse_args()

    # Initialize database if requested
    if args.init_db:
        init_database()
        return 0

    # Run in different modes
    if args.schedule:
        return run_scheduled(args)
    elif args.pipeline:
        return run_pipeline(args)
    else:
        return run_single_fetch(args)


if __name__ == "__main__":
    sys.exit(main())
