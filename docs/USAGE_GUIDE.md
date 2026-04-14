# 推送功能完整指南

## 📧 推送功能概述

第二阶段支持**邮件推送**，有两种配置方式：

### 方式对比

| 特性 | Resend API | SMTP |
|------|-----------|-----|
| 配置难度 | ⭐ 简单 | ⭐⭐ 中等 |
| 投递率 | ⭐⭐⭐⭐ 很高 | ⭐⭐⭐ 一般 |
| 成本 | 免费 3000封/月 | 免费 |
| 适用场景 | 生产环境 | 测试/个人 |

---

## 🚀 快速开始（3 步完成）

### 步骤 1：配置邮件

#### 选项 A：使用 QQ 邮箱（最简单）

```bash
# 1. 登录 QQ 邮箱网页版
# 2. 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
# 3. 开启"POP3/SMTP服务"
# 4. 点击"生成授权码"
# 5. 通过手机验证获取授权码（16位字符）

# 配置 .env
cat >> .env << 'EOF'
EMAIL_ENABLED=true
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your-email@qq.com
SMTP_PASSWORD=your-16-digit-auth-code
SMTP_FROM_EMAIL=your-email@qq.com
EOF
```

#### 选项 B：使用 Resend（推荐，专业）

```bash
# 1. 访问 https://resend.com 并注册
# 2. Settings > API Keys > Create API Key
# 3. 复制 API Key（格式：re_xxx）

# 配置 .env
cat >> .env << 'EOF'
EMAIL_ENABLED=true
RESEND_API_KEY=re_your-api-key-here
SMTP_FROM_EMAIL=noreply@yourdomain.com
EOF

# 4. 在 Resend 控制台添加并验证域名
```

### 步骤 2：初始化数据库

```bash
source venv/bin/activate
python main.py --init-db
```

### 步骤 3：添加订阅并发送

```bash
# 添加订阅
python scripts/add_subscription.py add \
  --email your@email.com \
  --keywords llm deeplearning \
  --exclude survey \
  --time 09:00

# 运行流水线
python main.py "llm" --pipeline --max-results 5
```

---

## 📋 完整使用示例

### 场景 1：给自己发送测试邮件

```bash
# 方式 1：使用 main.py
python main.py "llm" --send-email --email your@email.com --max-results 3

# 方式 2：使用专用脚本
python scripts/send_test_email.py --email your@email.com --keywords llm
```

### 场景 2：给多个同事订阅不同的主题

```bash
# 同事 A - 订阅 LLM
python scripts/add_subscription.py add \
  --email alice@company.com \
  --keywords llm transformer \
  --time 08:30

# 同事 B - 订阅计算机视觉
python scripts/add_subscription.py add \
  --email bob@company.com \
  --keywords vision segmentation \
  --time 09:00

# 同事 C - 订阅强化学习
python scripts/add_subscription.py add \
  --email charlie@company.com \
  --keywords reinforcement-learning \
  --exclude survey

# 查看所有订阅
python scripts/add_subscription.py list

# 运行完整流水线（会发送给所有订阅者）
python main.py "llm vision reinforcement" --pipeline --max-results 10
```

### 场景 3：定时每天早上 8 点推送

```bash
# 启动定时任务
python main.py "llm" --schedule --schedule-time 08:00
```

---

## 🛠️ 工具脚本说明

### 1. add_subscription.py - 订阅管理

```bash
# 添加订阅
python scripts/add_subscription.py add \
  --email user@example.com \
  --keywords llm deeplearning \
  --exclude survey review \
  --time 09:00 \
  --timezone Asia/Shanghai

# 列出所有订阅
python scripts/add_subscription.py list
```

### 2. send_test_email.py - 发送测试邮件

```bash
python scripts/send_test_email.py \
  --email test@example.com \
  --keywords llm \
  --max-results 3
```

### 3. view_logs.py - 查看推送日志

```bash
# 查看最近 20 条日志
python scripts/view_logs.py --limit 20

# 查看统计信息
python scripts/view_logs.py --stats
```

---

## 📊 数据库操作

### 查看 SQL 数据

```bash
# 打开数据库
sqlite3 papers.db

# 查看所有订阅
SELECT * FROM subscriptions;

# 查看推送日志
SELECT 
    pl.created_at,
    s.user_email,
    pl.channel,
    pl.status
FROM push_logs pl
JOIN subscriptions s ON pl.subscription_id = s.id
ORDER BY pl.created_at DESC
LIMIT 10;

# 退出
.quit
```

### 直接添加订阅

```sql
INSERT INTO subscriptions (
    user_email, 
    keywords, 
    exclude_keywords, 
    push_time, 
    timezone, 
    is_active
) VALUES (
    'your@email.com', 
    '["llm", "deeplearning"]', 
    '["survey", "review"]', 
    '08:00', 
    'Asia/Shanghai', 
    1
);
```

---

## ⚙️ 常见配置示例

### 示例 1：研究团队内部推送

```bash
# .env 配置（使用企业邮箱）
EMAIL_ENABLED=true
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=papers@company.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=Papers Bot <papers@company.com>

# 订阅配置
python scripts/add_subscription.py add \
  --email researcher1@company.com \
  --keywords llm vision \
  --time 08:00

python scripts/add_subscription.py add \
  --email researcher2@company.com \
  --keywords reinforcement \
  --time 09:00

python scripts/add_subscription.py add \
  --email team-lead@company.com \
  --keywords llm vision reinforcement \
  --time 10:00
```

### 示例 2：个人订阅多个主题

```bash
# 订阅不同主题
python scripts/add_subscription.py add \
  --email me@gmail.com \
  --keywords llm \
  --time 08:00

python scripts/add_subscription.py add \
  --email me@gmail.com \
  --keywords medical-image \
  --time 12:00

python scripts/add_subscription.py add \
  --email me@gmail.com \
  --keywords nlp \
  --time 18:00
```

---

## 🔍 故障排查

### 问题：邮件发送失败

**检查清单**：

```bash
# 1. 检查配置
grep -E "EMAIL|SMTP|RESEND" .env

# 2. 测试发送
python scripts/send_test_email.py --email your@email.com

# 3. 查看日志
tail -50 paper_pusher.log
```

### 问题：数据库表不存在

```bash
# 初始化数据库
python main.py --init-db

# 检查数据库
sqlite3 papers.db ".tables"
```

### 问题：订阅后没收到邮件

```bash
# 1. 检查订阅是否激活
python scripts/add_subscription.py list

# 2. 检查推送日志
python scripts/view_logs.py --limit 10

# 3. 检查邮箱垃圾箱
```

---

## 📈 推荐工作流

### 个人使用

```bash
# 1. 配置 QQ 邮箱
# 2. 添加订阅
python scripts/add_subscription.py add \
  --email me@qq.com \
  --keywords llm \
  --time 08:00

# 3. 定时推送
python main.py "llm" --schedule --schedule-time 08:00
```

### 团队使用

```bash
# 1. 使用 Resend 配置专业邮件
# 2. 为团队成员添加订阅
# 3. 运行定时任务
python main.py "research-topic" --schedule --schedule-time 09:00
```

### 测试开发

```bash
# 1. 发送测试邮件
python scripts/send_test_email.py --email test@domain.com

# 2. 查看日志统计
python scripts/view_logs.py --stats

# 3. 手动运行流水线
python main.py "test-keyword" --pipeline --max-results 3
```
