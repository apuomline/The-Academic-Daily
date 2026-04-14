"""Simplified pipeline API routes.

These routes provide direct access to the existing CLI functionality.
"""

import logging
import markdown
from typing import Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.database import db_manager, PaperCRUD
from src.fetchers import ArXivFetcher
from src.parsers import PaperParser
from src.summarizers import create_summarizer
from src.pipelines import TemplateRenderer
from src.pushers import EmailPusher
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class FetchRequest(BaseModel):
    """Request model for fetch endpoint."""
    keywords: str
    min_papers: int = 10
    max_results: int = 100
    max_days_back: int = 30


class GenerateRequest(BaseModel):
    """Request model for generate endpoint."""
    keywords: str = "llm"
    limit: int = 10
    use_llm: bool = True


class SendRequest(BaseModel):
    """Request model for send endpoint."""
    recipient: Optional[str] = None


@router.post("/fetch")
async def fetch_papers(request: FetchRequest) -> dict:
    """Fetch papers from arXiv with automatic fallback if not enough papers.

    This will progressively extend the date range backwards until
    enough papers are found or max_days_back is reached.
    """
    logger.info(f"📥 开始获取论文: keywords='{request.keywords}', min_papers={request.min_papers}")

    try:
        # Use ArXiv fetcher with fallback
        fetcher = ArXivFetcher(
            api_url=settings.arxiv_api_url,
            max_results=request.max_results,
        )

        # Use fetch_with_fallback for automatic date range extension
        papers = fetcher.fetch_with_fallback(
            keywords=request.keywords,
            min_papers=request.min_papers,
            max_days_back=request.max_days_back,
            max_results=request.max_results,
        )

        # Save to database
        session = db_manager.get_session()
        try:
            saved_count = 0
            for paper in papers:
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

            session.commit()
            logger.info(f"✓ 保存了 {saved_count} 篇论文到数据库")

        except Exception as e:
            session.rollback()
            logger.error(f"✗ 保存论文失败: {e}")
            raise
        finally:
            session.close()

        logger.info(f"✅ 获取论文完成: 共 {len(papers)} 篇")

        return {
            "success": True,
            "papers_fetched": len(papers),
            "message": f"Fetched {len(papers)} papers",
        }

    except Exception as e:
        logger.error(f"✗ 获取论文失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/generate")
async def generate_report(request: GenerateRequest) -> dict:
    """Generate report from database papers with LLM structured summaries.

    This generates Markdown report with structured summaries from LLM.
    """
    logger.info(f"📝 开始生成报告: keywords='{request.keywords}', limit={request.limit}, use_llm={request.use_llm}")

    try:
        # Get papers from database - use search to filter by keywords
        session = db_manager.get_session()
        try:
            # Parse keywords from request - split by space like ArXiv fetcher does
            # This ensures consistency: "medical image" -> ["medical", "image"]
            keywords_list = request.keywords.strip().lower().split() if request.keywords else ["llm"]

            logger.info(f"🔍 使用关键词搜索数据库: {keywords_list}")

            papers = PaperCRUD.search_papers(
                session,
                keywords=keywords_list,
                limit=request.limit
            )
        finally:
            session.close()

        if not papers:
            logger.warning("⚠️ 数据库中没有找到匹配的论文")
            return {
                "success": False,
                "error": f"No papers found matching keywords: {request.keywords}",
            }

        logger.info(f"✓ 从数据库找到 {len(papers)} 篇匹配的论文")

        # Process with LLM
        summarizer = None
        if request.use_llm:
            logger.info(f"🤖 使用 LLM 生成摘要: {settings.llm_provider}/{settings.llm_model}")
            summarizer = create_summarizer(
                provider=settings.llm_provider,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                api_key=settings.get_api_key(),
                base_url=settings.get_base_url(),
            )

        processed_papers = []
        llm_success = 0
        llm_failed = 0

        for i, paper in enumerate(papers, 1):
            # Create a wrapper object that matches expected structure
            class ProcessedPaper:
                def __init__(self, p):
                    self.arxiv_id = p.arxiv_id or ""
                    self.title = p.title
                    self.abstract = p.abstract or ""
                    self.published = p.published_date.isoformat() if p.published_date else ""
                    self.updated = p.updated_date.isoformat() if p.updated_date else ""
                    self.display_date = p.published_date.strftime("%Y-%m-%d") if p.published_date else "未知"
                    self.version = "v1"
                    self.source = p.source
                    self.pdf_url = f"https://arxiv.org/pdf/{p.arxiv_id}.pdf" if p.arxiv_id else None
                    self.summary_content = None
                    self.summary_structured = None
                    self.authors = []

            processed = ProcessedPaper(paper)

            if request.use_llm and summarizer and paper.abstract:
                try:
                    result = summarizer.summarize_structured(
                        title=paper.title,
                        abstract=paper.abstract,
                        intro_text=None,
                    )

                    if result.success and result.summary:
                        processed.summary_structured = result.summary
                        processed.summary_content = result.summary.abstract_translation
                        llm_success += 1
                        logger.info(f"  [{i:2d}/{len(papers)}] ✓ {paper.arxiv_id}: {paper.title[:50]}...")
                    else:
                        processed.summary_content = paper.abstract
                        llm_failed += 1
                        logger.info(f"  [{i:2d}/{len(papers)}] ⚠ {paper.arxiv_id}: 使用原始摘要")
                except Exception as e:
                    logger.warning(f"  [{i:2d}/{len(papers)}] ✗ {paper.arxiv_id}: {e}")
                    processed.summary_content = paper.abstract
                    llm_failed += 1
            else:
                processed.summary_content = paper.abstract

            processed_papers.append(processed)

        logger.info(f"✓ LLM 摘要完成: 成功 {llm_success} 篇, 失败 {llm_failed} 篇")

        # Generate report using TemplateRenderer
        renderer = TemplateRenderer()
        report_date = datetime.now().strftime("%Y-%m-%d")
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Use the keywords from the request - split by space for consistency
        keywords_list = request.keywords.strip().split() if request.keywords else ["llm"]

        logger.info(f"📄 生成报告...")
        markdown = renderer.render_markdown(
            processed_papers,
            keywords_list,
            report_date,
            generation_time,
        )

        # Save report
        output_path = Path("output") / f"DAILY_REPORT_{report_date}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

        logger.info(f"✓ 报告已保存: {output_path}")
        logger.info(f"✅ 报告生成完成: 共 {len(processed_papers)} 篇论文")

        return {
            "success": True,
            "report_path": str(output_path),
            "papers_count": len(processed_papers),
            "llm_success": llm_success if request.use_llm else None,
            "llm_failed": llm_failed if request.use_llm else None,
            "message": f"Generated report with {len(processed_papers)} papers"
            + (f" ({llm_success} structured)" if request.use_llm else ""),
        }

    except Exception as e:
        logger.error(f"✗ 报告生成失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/send")
async def send_email(request: SendRequest) -> dict:
    """Send the latest generated report via email.

    This reads the most recently generated report and sends it as HTML email.
    """
    recipient = request.recipient or settings.smtp_from_email
    logger.info(f"📧 开始发送邮件: recipient='{recipient}'")

    try:
        # Check if email is configured
        if not settings.email_enabled:
            logger.warning("⚠️ 邮件服务未启用")
            return {
                "success": False,
                "error": "Email is not enabled",
            }

        # Find the latest report
        output_dir = Path("output")
        reports = list(output_dir.glob("DAILY_REPORT_*.md"))

        if not reports:
            logger.warning("⚠️ 没有找到已生成的报告，请先生成报告")
            return {
                "success": False,
                "error": "No report found. Please generate a report first using /api/pipeline/generate",
            }

        # Get the latest report by modification time
        latest_report = max(reports, key=lambda x: x.stat().st_mtime)
        logger.info(f"✓ 使用已生成的报告: {latest_report.name}")

        # Read the markdown content
        markdown_content = latest_report.read_text(encoding="utf-8")

        # Extract report date from filename for subject
        report_date_str = latest_report.stem.replace("DAILY_REPORT_", "")
        logger.info(f"📄 报告日期: {report_date_str}")

        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables'])
        html_body = md.convert(markdown_content)

        # Wrap in HTML email template
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.8;
            color: #2c3e50;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 24px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 20px;
            border-left: 4px solid #4CAF50;
            padding-left: 12px;
        }}
        h3 {{
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 18px;
        }}
        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}
        strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }}
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #ecf0f1;
        }}
        a {{
            color: #4CAF50;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        ul, ol {{
            padding-left: 25px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        blockquote {{
            border-left: 4px solid #4CAF50;
            padding-left: 15px;
            margin: 15px 0;
            color: #7f8c8d;
            font-style: italic;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_body}
        <div class="footer">
            <p>📚 学术论文推送助手 | 自动生成</p>
            <p>如有问题，请联系系统管理员</p>
        </div>
    </div>
</body>
</html>
        """

        # Plain text version (strip markdown syntax)
        text_content = markdown_content
        text_content = text_content.replace('**', '').replace('##', '').replace('###', '').replace('* ', '• ')
        text_content = text_content.replace('[', '').replace(']', '')

        # Send email
        logger.info(f"📮 正在发送邮件到 {recipient}...")
        pusher = EmailPusher()
        recipients = [request.recipient] if request.recipient else [settings.smtp_from_email]

        report_date_cn = report_date_str.replace("-", "年") + "日"
        subject = f"学术日报 {report_date_cn}"

        results = pusher.send_report(recipients, subject, html_content, text_content)

        success_count = len(results.get("success", []))

        if success_count > 0:
            logger.info(f"✓ 邮件发送成功: {success_count} 个收件人")
            for email in results.get("success", []):
                logger.info(f"  → {email}")

            return {
                "success": True,
                "message": f"Email sent successfully to {success_count} recipient(s)",
                "recipients": results.get("success", []),
                "report_file": str(latest_report),
            }
        else:
            logger.error(f"✗ 邮件发送失败")
            for fail in results.get("failed", []):
                logger.error(f"  ✗ {fail.get('email')}: {fail.get('error')}")
            return {
                "success": False,
                "error": "Failed to send email",
                "details": results.get("failed", []),
            }

    except Exception as e:
        logger.error(f"✗ 发送邮件失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/papers")
async def list_papers(
    limit: int = Query(20, description="Max papers to return"),
    keywords: str = Query("", description="Keywords to search for (space-separated)")
) -> dict:
    """List papers from database with optional keyword filtering.

    Args:
        limit: Maximum number of papers
        keywords: Space-separated keywords to filter papers

    Returns:
        List of papers
    """
    try:
        session = db_manager.get_session()
        try:
            # Parse keywords - split by space for consistency with fetch
            keywords_list = keywords.strip().lower().split() if keywords.strip() else None

            if keywords_list:
                # Search by keywords using AND logic
                papers = PaperCRUD.search_papers(
                    session,
                    keywords=keywords_list,
                    limit=limit
                )
                logger.info(f"📋 搜索论文: 关键词={keywords_list}, 结果={len(papers)} 篇")
            else:
                # Get recent papers if no keywords
                papers = PaperCRUD.get_recent_papers(session, limit=limit)

            papers_list = []
            for paper in papers:
                papers_list.append({
                    "id": paper.id,
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "abstract": paper.abstract[:200] + "..." if paper.abstract and len(paper.abstract) > 200 else paper.abstract,
                    "source": paper.source,
                    "published_date": paper.published_date.isoformat() if paper.published_date else None,
                })

            return {
                "success": True,
                "papers": papers_list,
                "total": len(papers_list),
            }

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Failed to list papers: {e}")
        return {
            "success": False,
            "papers": [],
            "error": str(e),
        }


@router.get("/status")
async def get_status() -> dict:
    """Get current pipeline status.

    Returns:
        Status information
    """
    try:
        session = db_manager.get_session()
        try:
            from src.database.models import Paper
            paper_count = session.query(Paper).count()
        finally:
            session.close()

        # Check for latest report
        output_dir = Path("output")
        reports = list(output_dir.glob("DAILY_REPORT_*.md"))
        latest_report = None
        if reports:
            latest_report = max(reports, key=lambda x: x.stat().st_mtime)
            report_time = datetime.fromtimestamp(latest_report.stat().st_mtime)
        else:
            report_time = None

        return {
            "success": True,
            "database_papers": paper_count,
            "latest_report": str(latest_report) if latest_report else None,
            "latest_report_time": report_time.isoformat() if report_time else None,
        }

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return {
            "success": False,
            "error": str(e),
        }
