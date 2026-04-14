#!/bin/bash
# GitHub 自动同步脚本
# 用法: ./git_sync.sh [commit_message]

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

# 检查是否在 git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "当前目录不是 git 仓库"
    print_info "请先运行: git init"
    exit 1
fi

# 检查远程仓库
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE" ]; then
    print_error "未找到远程仓库 origin"
    echo ""
    echo "请先添加远程仓库："
    echo "  git remote add origin https://github.com/用户名/仓库名.git"
    echo "  或"
    echo "  git remote add origin git@github.com:用户名/仓库名.git"
    exit 1
fi

print_info "远程仓库: $REMOTE"

# 获取当前分支
CURRENT_BRANCH=$(git branch --show-current)
print_info "当前分支: $CURRENT_BRANCH"

# 检查是否有未提交的更改
if git diff --quiet && git diff --cached --quiet; then
    print_warning "没有需要提交的更改"
    exit 0
fi

# 显示更改的文件
print_info "更改的文件："
git status --short

echo ""

# 自动生成提交信息或使用用户提供的
if [ -n "$1" ]; then
    COMMIT_MSG="$1"
else
    # 自动生成提交信息
    CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | wc -l)
    CHANGED_FILES_TOTAL=$(git status --short | wc -l)

    # 分析更改类型
    ADDED=$(git status --short | grep -c "^A" || true)
    MODIFIED=$(git status --short | grep -c "^ M" || true)
    DELETED=$(git status --short | grep -c "^ D" || true)

    MSG_TYPE="update"
    if [ "$ADDED" -gt 0 ] && [ "$MODIFIED" -eq 0 ] && [ "$DELETED" -eq 0 ]; then
        MSG_TYPE="add"
    elif [ "$DELETED" -gt 0 ] && [ "$MODIFIED" -eq 0 ]; then
        MSG_TYPE="remove"
    elif [ "$MODIFIED" -gt 0 ]; then
        MSG_TYPE="update"
    fi

    # 获取最近修改的文件
    MAIN_FILE=$(git diff --cached --name-only 2>/dev/null | head -1 || git status --short | head -1 | awk '{print $2}')
    if [ -n "$MAIN_FILE" ]; then
        # 提取文件所在的目录作为作用域
        SCOPE=$(echo "$MAIN_FILE" | cut -d'/' -f1)
        if [ "$SCOPE" = "$MAIN_FILE" ]; then
            SCOPE=""
        else
            SCOPE="($SCOPE)"
        fi
    fi

    # 生成提交信息
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    COMMIT_MSG="$MSG_TYPE $SCOPE: sync changes [$TIMESTAMP]"

    print_info "自动生成的提交信息: $COMMIT_MSG"
    echo ""
    read -p "是否使用此提交信息？[Y/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [ ! -z "$REPLY" ]; then
        read -p "请输入自定义提交信息: " COMMIT_MSG
    fi
fi

# 添加所有更改
print_info "添加文件到暂存区..."
git add -A

# 提交更改
print_info "创建提交..."
git commit -m "$COMMIT_MSG"

# 推送到远程仓库
print_info "推送到远程仓库..."

# 检查是否设置了上游分支
if git rev-parse --abbrev-ref --symbolic-full-name @{u} > /dev/null 2>&1; then
    # 已设置上游分支
    git push
else
    # 首次推送，设置上游分支
    print_info "首次推送，设置上游分支..."
    git push -u origin "$CURRENT_BRANCH"
fi

print_success "同步完成！"
echo ""
print_info "查看提交: git log -1 --stat"
