# Git 自动同步脚本使用指南

本项目提供了基于配置文件的 Git 自动化同步工具。

## 文件说明

| 文件 | 说明 |
|------|------|
| `git_config.ini.example` | 配置文件模板 |
| `git_config.ini` | 你的实际配置文件（需创建） |
| `git_setup.sh` | 一键配置脚本（读取配置文件） |
| `git_sync.sh` | Bash 版本同步脚本 |
| `git_sync.py` | Python 版本同步脚本（功能更全） |

---

## 快速开始

### 步骤 1: 创建配置文件

```bash
# 复制示例配置文件
cp git_config.ini.example git_config.ini

# 编辑配置文件
vim git_config.ini
# 或使用其他编辑器: nano git_config.ini
```

### 步骤 2: 修改配置

编辑 `git_config.ini`，修改以下内容：

```ini
[git]
# 修改为你的名字和邮箱
user_name = Zhang San
user_email = zhangsan@example.com
main_branch = main

[github]
# 修改为你的 GitHub 信息
github_username = zhangsan
repository_name = my-project
connection = https

[options]
skip_hooks = false
verbose = true
```

### 步骤 3: 运行配置脚本

```bash
chmod +x git_setup.sh
./git_setup.sh
```

脚本会自动：
1. 初始化 Git 仓库
2. 配置用户信息
3. 创建 `.gitignore`
4. 配置远程仓库
5. 首次提交并推送

---

## 配置文件详解

### `[git]` 部分

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `user_name` | Git 提交者姓名 | `Zhang San` |
| `user_email` | Git 提交者邮箱 | `zhangsan@example.com` |
| `main_branch` | 主分支名称 | `main` 或 `master` |

### `[github]` 部分

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `github_username` | GitHub 用户名 | `zhangsan` |
| `repository_name` | 仓库名称 | `my-project` |
| `connection` | 连接方式 | `https` 或 `ssh` |
| `remote_url` | 完整仓库 URL（可选） | 留空则自动生成 |

### `[options]` 部分

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `skip_hooks` | 是否跳过 git hooks | `false` |
| `verbose` | 是否显示详细输出 | `true` |

---

## 日常使用

### Bash 版本

```bash
# 自动生成提交信息
./git_sync.sh

# 使用自定义提交信息
./git_sync.sh "feat: 添加新功能"
```

### Python 版本

```bash
# 自动生成提交信息
python3 git_sync.py

# 使用自定义提交信息
python3 git_sync.py "feat: 添加新功能"

# 预览模式（不实际提交）
python3 git_sync.py --dry-run

# 跳过 git hooks
python3 git_sync.py --skip-hooks

# 使用自定义配置文件
python3 git_sync.py --config /path/to/config.ini
```

---

## 提交信息规范

建议使用以下格式：

```
<类型>(<作用域>): <描述>
```

### 类型 (type)

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档更新 |
| `style` | 代码格式调整 |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具链相关 |
| `update` | 通用更新 |

### 示例

```bash
./git_sync.sh "feat(arxiv): 实现 arXiv API 抓取功能"
./git_sync.sh "fix(parser): 处理重复论文 ID"
./git_sync.sh "docs: 更新 README"
./git_sync.sh "refactor(summarizers): 重构 LLM 调用逻辑"
```

---

## HTTPS vs SSH

### HTTPS 方式

```ini
[github]
connection = https
```

- **优点**: 配置简单，防火墙友好
- **缺点**: 推送时需要输入 Personal Access Token

**获取 Personal Access Token**:
1. 访问 https://github.com/settings/tokens
2. 生成新 Token，勾选 `repo` 权限
3. 推送时使用 Token 作为密码

### SSH 方式

```ini
[github]
connection = ssh
```

- **优点**: 配置一次后免密推送
- **缺点**: 需要配置 SSH 密钥

**配置 SSH 密钥**:
```bash
# 生成密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 添加到 ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 复制公钥到 GitHub
cat ~/.ssh/id_ed25519.pub
# 然后访问: https://github.com/settings/keys
```

---

## 常见问题

### Q: 修改配置文件后需要重新运行 git_setup.sh 吗？

**A**: 不需要。`git_setup.sh` 主要用于首次配置。日常只需运行 `git_sync.py` 或 `git_sync.sh`。

### Q: 如何跳过某些文件？

**A**: 编辑 `.gitignore` 文件，添加要忽略的文件模式。

### Q: 如何撤销最后一次提交？

**A**:
```bash
git reset --soft HEAD~1  # 保留更改
git reset --hard HEAD~1  # 丢弃更改
```

### Q: 推送时提示认证失败？

**A**:
- **HTTPS**: 检查是否使用了 Personal Access Token（不是密码）
- **SSH**: 检查 SSH 密钥是否正确配置

### Q: 如何查看提交历史？

**A**:
```bash
git log --oneline --graph --all
```

---

## 目录结构

```
/home/apu/project/AgentCodes/001/
├── git_config.ini.example   # 配置模板
├── git_config.ini           # 你的配置（需创建）
├── git_setup.sh             # 配置脚本
├── git_sync.sh              # Bash 同步脚本
├── git_sync.py              # Python 同步脚本
└── GIT_SYNC.md              # 本文档
```
