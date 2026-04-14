#!/usr/bin/env python3
"""GitHub 自动同步脚本

用法:
    python git_sync.py                    # 自动生成提交信息
    python git_sync.py "fix:修复bug"      # 使用自定义提交信息
    python git_sync.py --dry-run          # 预览模式，不实际提交
    python git_sync.py --skip-hooks       # 跳过 git hooks
    python git_sync.py --config FILE      # 指定配置文件
"""

import argparse
import configparser
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional


class Colors:
    """终端颜色"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def print_info(msg: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ{Colors.NC} {msg}")


def print_success(msg: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓{Colors.NC} {msg}")


def print_warning(msg: str):
    """打印警告"""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {msg}")


def print_error(msg: str):
    """打印错误"""
    print(f"{Colors.RED}✗{Colors.NC} {msg}")


def run_command(cmd: list, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """运行 shell 命令"""
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
    else:
        result = subprocess.run(cmd)

    if check and result.returncode != 0:
        print_error(f"命令执行失败: {' '.join(cmd)}")
        if result.stderr:
            print_error(result.stderr)
        sys.exit(1)

    return result


class GitConfig:
    """Git 配置管理"""

    def __init__(self, config_file: str = "git_config.ini"):
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            self.config.read(self.config_file)
        else:
            print_warning(f"配置文件不存在: {self.config_file}")

    def get(self, section: str, key: str, default: str = "") -> str:
        """获取配置值"""
        try:
            return self.config.get(section, key, fallback=default)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """获取布尔配置值"""
        val = self.get(section, key, str(default)).lower()
        return val in ("true", "yes", "1", "on")


def check_git_repo() -> bool:
    """检查是否在 git 仓库中"""
    result = run_command(["git", "rev-parse", "--git-dir"], check=False)
    return result.returncode == 0


def get_remote_url() -> str:
    """获取远程仓库 URL"""
    result = run_command(["git", "remote", "get-url", "origin"], check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def get_current_branch() -> str:
    """获取当前分支名"""
    result = run_command(["git", "branch", "--show-current"])
    return result.stdout.strip()


def has_upstream() -> bool:
    """检查是否设置了上游分支"""
    result = run_command(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    return result.returncode == 0


def get_changed_files() -> list:
    """获取更改的文件列表"""
    result = run_command(["git", "status", "--short"])
    lines = result.stdout.strip().split('\n')
    return [line for line in lines if line]


def analyze_changes() -> dict:
    """分析更改类型"""
    changed_files = get_changed_files()

    stats = {
        "added": 0,
        "modified": 0,
        "deleted": 0,
        "renamed": 0,
        "total": len(changed_files),
        "files": changed_files
    }

    for line in changed_files:
        status = line[:2]
        if 'A' in status:
            stats["added"] += 1
        elif 'M' in status:
            stats["modified"] += 1
        elif 'D' in status:
            stats["deleted"] += 1
        elif 'R' in status:
            stats["renamed"] += 1

    return stats


def generate_commit_message(stats: dict, git_config: Optional[GitConfig] = None) -> str:
    """自动生成提交信息"""
    # 确定提交类型
    if stats["added"] > 0 and stats["modified"] == 0 and stats["deleted"] == 0:
        commit_type = "feat"
        type_name = "新增"
    elif stats["deleted"] > 0 and stats["modified"] == 0:
        commit_type = "remove"
        type_name = "删除"
    elif stats["renamed"] > 0:
        commit_type = "refactor"
        type_name = "重构"
    else:
        commit_type = "update"
        type_name = "更新"

    # 提取作用域（从第一个修改的文件）
    scope = ""
    if stats["files"]:
        first_file = stats["files"][0]
        parts = first_file.split()
        if len(parts) >= 2:
            file_path = parts[1]
            path_parts = file_path.split('/')
            if len(path_parts) > 1:
                scope = f"({path_parts[0]})"

    # 生成提交信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"{commit_type}{scope}: {type_name} {stats['total']} 个文件 [{timestamp}]"

    return commit_msg


def sync_to_github(
    commit_msg: str,
    dry_run: bool = False,
    skip_hooks: bool = False,
    config_file: str = "git_config.ini"
):
    """同步到 GitHub"""
    # 加载配置
    git_config = GitConfig(config_file)
    verbose = git_config.get_bool("options", "verbose", True)

    if verbose:
        print_info(f"使用配置文件: {config_file}")

    # 检查是否在 git 仓库中
    if not check_git_repo():
        print_error("当前目录不是 git 仓库")
        print_info("请先运行: ./git_setup.sh")
        sys.exit(1)

    # 检查远程仓库
    remote_url = get_remote_url()
    if not remote_url:
        print_error("未找到远程仓库 origin")
        print_info("请先运行: ./git_setup.sh 配置远程仓库")
        sys.exit(1)

    print_info(f"远程仓库: {remote_url}")

    # 获取当前分支
    current_branch = get_current_branch()
    print_info(f"当前分支: {current_branch}")

    # 分析更改
    stats = analyze_changes()

    if stats["total"] == 0:
        print_warning("没有需要提交的更改")
        sys.exit(0)

    # 显示更改
    print("")
    print_info("更改的文件：")
    for file_status in stats["files"][:10]:
        print(f"  {file_status}")
    if stats["total"] > 10:
        print(f"  ... 还有 {stats['total'] - 10} 个文件")

    print("")
    print(f"  新增: {stats['added']} | 修改: {stats['modified']} | 删除: {stats['deleted']} | 重命名: {stats['renamed']}")

    # 如果没有提供提交信息，自动生成
    if not commit_msg:
        commit_msg = generate_commit_message(stats, git_config)

    print("")
    print_info(f"提交信息: {commit_msg}")

    if dry_run:
        print_warning("预览模式，不会实际提交")
        return

    # 检查配置是否跳过 hooks
    if not skip_hooks:
        skip_hooks = git_config.get_bool("options", "skip_hooks", False)

    # 添加所有更改
    print("")
    print_info("添加文件到暂存区...")
    run_command(["git", "add", "-A"], capture=False)

    # 提交更改
    print_info("创建提交...")
    commit_cmd = ["git", "commit", "-m", commit_msg]
    if skip_hooks:
        commit_cmd.insert(2, "--no-verify")
    run_command(commit_cmd, capture=False)

    # 推送到远程仓库
    print_info("推送到远程仓库...")

    if has_upstream():
        push_cmd = ["git", "push"]
    else:
        main_branch = git_config.get("git", "main_branch", "main")
        print_info(f"首次推送，设置上游分支 ({main_branch})...")
        push_cmd = ["git", "push", "-u", "origin", main_branch]

    run_command(push_cmd, capture=False)

    print("")
    print_success("同步完成！")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitHub 自动同步脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python git_sync.py                    # 自动生成提交信息
    python git_sync.py "fix:修复bug"      # 使用自定义提交信息
    python git_sync.py --dry-run          # 预览模式，不实际提交
    python git_sync.py --skip-hooks       # 跳过 git hooks
    python git_sync.py --config custom.ini # 使用自定义配置文件
        """
    )

    parser.add_argument(
        "message",
        nargs="?",
        help="提交信息（可选，不提供则自动生成）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际提交和推送"
    )
    parser.add_argument(
        "--skip-hooks",
        action="store_true",
        help="跳过 git hooks（如 pre-commit）"
    )
    parser.add_argument(
        "--config",
        default="git_config.ini",
        help="配置文件路径（默认: git_config.ini）"
    )

    args = parser.parse_args()

    try:
        sync_to_github(
            commit_msg=args.message,
            dry_run=args.dry_run,
            skip_hooks=args.skip_hooks,
            config_file=args.config
        )
    except KeyboardInterrupt:
        print("")
        print_warning("操作已取消")
        sys.exit(1)
    except Exception as e:
        print_error(f"发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
