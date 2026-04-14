#!/usr/bin/env python3
"""添加订阅到数据库的脚本。"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import db_manager, SubscriptionCRUD


def add_subscription(
    email: str,
    keywords: list,
    exclude_keywords: list = None,
    push_time: str = "08:00",
    timezone: str = "Asia/Shanghai",
):
    """添加订阅。

    Args:
        email: 邮箱地址
        keywords: 关注关键词列表
        exclude_keywords: 排除关键词列表
        push_time: 推送时间 (HH:MM 格式)
        timezone: 时区
    """
    session = db_manager.get_session()

    try:
        subscription = SubscriptionCRUD.create_subscription(
            session,
            user_email=email,
            keywords=keywords,
            exclude_keywords=exclude_keywords or [],
            push_time=push_time,
            timezone=timezone,
        )

        session.commit()

        print(f"✓ 订阅添加成功！")
        print(f"  ID: {subscription.id}")
        print(f"  邮箱: {email}")
        print(f"  关键词: {', '.join(keywords)}")
        if exclude_keywords:
            print(f"  排除: {', '.join(exclude_keywords)}")
        print(f"  推送时间: {push_time} {timezone}")

        return subscription.id

    except Exception as e:
        session.rollback()
        print(f"✗ 添加失败: {e}")
        return None

    finally:
        session.close()


def list_subscriptions():
    """列出所有活跃订阅。"""
    from src.database import SubscriptionCRUD

    session = db_manager.get_session()

    try:
        subscriptions = SubscriptionCRUD.get_active_subscriptions(session)

        if not subscriptions:
            print("没有找到活跃的订阅")
            return

        print(f"\n共有 {len(subscriptions)} 个活跃订阅：\n")

        for sub in subscriptions:
            print(f"ID: {sub.id}")
            print(f"  邮箱: {sub.user_email}")
            print(f"  关键词: {', '.join(sub.keywords)}")
            if sub.exclude_keywords:
                print(f"  排除: {', '.join(sub.exclude_keywords)}")
            print(f"  推送时间: {sub.push_time or '未设置'} ({sub.timezone})")
            print(f"  创建时间: {sub.created_at}")
            print()

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="订阅管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 添加订阅命令
    add_parser = subparsers.add_parser("add", help="添加订阅")
    add_parser.add_argument("--email", required=True, help="邮箱地址")
    add_parser.add_argument("--keywords", nargs="+", required=True, help="关注关键词")
    add_parser.add_argument("--exclude", nargs="*", default=[], help="排除关键词")
    add_parser.add_argument("--time", default="08:00", help="推送时间 (HH:MM)")
    add_parser.add_argument("--timezone", default="Asia/Shanghai", help="时区")

    # 列出订阅命令
    subparsers.add_parser("list", help="列出所有订阅")

    args = parser.parse_args()

    if args.command == "add":
        add_subscription(
            email=args.email,
            keywords=args.keywords,
            exclude_keywords=args.exclude,
            push_time=args.time,
            timezone=args.timezone,
        )
    elif args.command == "list":
        list_subscriptions()
    else:
        parser.print_help()
