#!/bin/bash
# Git 仓库配置脚本（读取 git_config.ini）
# 用法: ./git_setup.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

# 配置文件路径
CONFIG_FILE="git_config.ini"

# 从配置文件读取值的函数
get_config() {
    local section=$1
    local key=$2
    local default=$3

    if [ -f "$CONFIG_FILE" ]; then
        # 使用 sed 和 grep 解析 ini 文件
        # 方法：1) 找到 section 开始位置；2) 在该 section 中查找 key
        local value
        value=$(sed -n "/^\[$section\]/,/^\[/p" "$CONFIG_FILE" | grep "^${key}[ ]*=" | cut -d'=' -f2 | tr -d ' ')
        echo "${value:-$default}"
    else
        echo "$default"
    fi
}

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "配置文件不存在: $CONFIG_FILE"
    print_info "请先创建并编辑配置文件，参考 git_config.ini.example"
    exit 1
fi

echo "=========================================="
echo "    Git 仓库配置 (读取配置文件)"
echo "=========================================="
echo ""
print_info "使用配置文件: $CONFIG_FILE"
echo ""

# 1. 读取配置
GIT_NAME=$(get_config "git" "user_name" "")
GIT_EMAIL=$(get_config "git" "user_email" "")
MAIN_BRANCH=$(get_config "git" "main_branch" "main")
GITHUB_USER=$(get_config "github" "github_username" "")
REPO_NAME=$(get_config "github" "repository_name" "")
CONNECTION=$(get_config "github" "connection" "https")
REMOTE_URL=$(get_config "github" "remote_url" "")

# 2. 验证必需配置
if [ -z "$GIT_NAME" ] || [ "$GIT_NAME" = "Your Name" ]; then
    print_error "请在 $CONFIG_FILE 中配置 git.user_name"
    exit 1
fi

if [ -z "$GIT_EMAIL" ] || [ "$GIT_EMAIL" = "your.email@example.com" ]; then
    print_error "请在 $CONFIG_FILE 中配置 git.user_email"
    exit 1
fi

if [ -z "$GITHUB_USER" ] || [ "$GITHUB_USER" = "your_username" ]; then
    print_error "请在 $CONFIG_FILE 中配置 github.github_username"
    exit 1
fi

if [ -z "$REPO_NAME" ] || [ "$REPO_NAME" = "your-repo-name" ]; then
    print_error "请在 $CONFIG_FILE 中配置 github.repository_name"
    exit 1
fi

# 3. 显示配置信息
print_info "配置信息："
echo "  用户: $GIT_NAME <$GIT_EMAIL>"
echo "  主分支: $MAIN_BRANCH"
echo "  GitHub: $GITHUB_USER/$REPO_NAME"
echo "  连接方式: $CONNECTION"
echo ""

# 4. 初始化仓库
if [ -d .git ]; then
    print_warning "Git 仓库已存在，跳过初始化"
else
    print_info "初始化 Git 仓库..."
    git init
    print_success "仓库初始化完成"
fi

# 5. 配置用户信息
print_info "配置 Git 用户信息..."
git config user.name "$GIT_NAME"
git config user.email "$GIT_EMAIL"
print_success "用户信息配置完成"

# 6. 创建 .gitignore
if [ ! -f .gitignore ]; then
    print_info "创建 .gitignore 文件..."

    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
*.egg-info/
dist/
build/

# 项目特定
cache/
*.log
.env
.DS_Store

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF

    print_success ".gitignore 创建完成"
else
    print_info ".gitignore 已存在，跳过"
fi

# 7. 配置远程仓库
print_info "配置 GitHub 远程仓库..."

# 如果没有手动指定 URL，则自动生成
if [ -z "$REMOTE_URL" ]; then
    if [ "$CONNECTION" = "ssh" ]; then
        REMOTE_URL="git@github.com:${GITHUB_USER}/${REPO_NAME}.git"
    else
        REMOTE_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
    fi
fi

# 检查是否已有 origin
if git remote get-url origin >/dev/null 2>&1; then
    CURRENT_URL=$(git remote get-url origin)
    if [ "$CURRENT_URL" != "$REMOTE_URL" ]; then
        git remote set-url origin "$REMOTE_URL"
        print_success "更新远程仓库 URL"
    else
        print_info "远程仓库已配置"
    fi
else
    git remote add origin "$REMOTE_URL"
    print_success "添加远程仓库: $REMOTE_URL"
fi

# 8. 首次提交
if ! git rev-parse HEAD >/dev/null 2>&1; then
    print_info "创建首次提交..."
    git add -A
    git commit -m "feat: 初始化项目" 2>/dev/null || true
    print_success "首次提交完成"
else
    print_info "已有提交历史，跳过首次提交"
fi

# 9. 设置主分支名称
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]; then
    git branch -M "$MAIN_BRANCH"
    print_success "主分支设置为: $MAIN_BRANCH"
else
    print_info "主分支已是: $MAIN_BRANCH"
fi

# 10. 推送到 GitHub
echo ""
print_warning "即将推送到 GitHub: $REMOTE_URL"
read -p "是否现在推送？[Y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] || [ -z "$REPLY" ]; then
    print_info "推送到 GitHub..."

    # 检查是否设置了上游分支
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
        git push
    else
        git push -u origin "$MAIN_BRANCH"
    fi

    print_success "推送完成！"
else
    print_info "跳过推送"
    print_info "稍后可手动运行: git push -u origin $MAIN_BRANCH"
fi

echo ""
echo "=========================================="
print_success "配置完成！"
echo "=========================================="
echo ""
echo "后续使用同步脚本:"
echo "  ./git_sync.sh              # Bash 版本"
echo "  python3 git_sync.py        # Python 版本"
echo ""
