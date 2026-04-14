#!/usr/bin/env python3
"""查看推送日志的脚本。"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import db_manager
from sqlalchemy import select, and_
from src.database.models import PushLog, Subscription


def view_recent_logs(limit: int = 20):
    """查看最近的推送日志。

    Args:
        limit: 显示的日志条数
    """
    session = db_manager.get_session()

    try:
        # 查询最近的日志
        from src.database.crud import PushLogCRUD

        logs = PushLogCRUD.get_recent_pushes(session, limit=limit)

        if not logs:
            print("没有找到推送日志")
            return

        print(f"\n最近 {len(logs)} 条推送记录：\n")
        print("-" * 80)

        for log in logs:
            # 获取订阅信息
            sub = session.get(Subscription, log.subscription_id)
            email = sub.user_email if sub else "Unknown"

            # 状态图标
            status_icon = "✓" if log.status == "success" else "✗"

            print(f"{status_icon} {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   邮箱: {email}")
            print(f"   渠道: {log.channel}")
            print(f"   日期: {log.report_date.strftime('%Y-%m-%d')}")
            print(f"   状态: {log.status}")
            if log.error_msg:
                print(f"   错误: {log.error_msg}")
            print()

    finally:
        session.close()


def view_stats():
    """查看推送统计信息。"""
    session = db_manager.get_session()

    try:
        # 统计各状态数量
        from sqlalchemy import func

        success_count = session.execute(
            select(func.count(PushLog.id)).where(PushLog.status == "success")
        ).scalar() or 0

        failed_count = session.execute(
            select(func.count(PushLog.id)).where(PushLog.status == "failed")
        ).scalar() or 0

        total_count = session.execute(select(func.count(PushLog.id))).scalar() or 0

        print(f"\n📊 推送统计：")
        print(f"   总推送数: {total_count}")
        print(f"   成功: {success_count}")
        print(f"   失败: {failed_count}")

        if total_count > 0:
            success_rate = (success_count / total_count) * 100
            print(f"   成功率: {success_rate:.1f}%")

        # 最近 24 小时的推送
        yesterday = datetime.now() - timedelta(days=1)
        recent_count = session.execute(
            select(func.count(PushLog.id)).where(PushLog.created_at >= yesterday)
        ).scalar() or 0

        print(f"   最近24小时: {recent_count}")

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="查看推送日志")
    parser.add_argument("--limit", type=int, default=20, help="显示条数")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")

    args = parser.parse_args()

    if args.stats:
        view_stats()
    else:
        view_recent_logs(args.limit)
