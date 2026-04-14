# 推送功能配置和使用指南

## 推送方式概述

第二阶段支持**邮件推送**，有两种配置方式：

### 方式一：Resend API（推荐）

**优点**：
- 配置简单，只需 API Key
- 不需要管理邮件服务器
- 投递率高，进垃圾箱少
- 提供发送统计和日志

**获取 API Key**：
1. 访问 [resend.com](https://resend.com)
2. 注册账号
3. 在 Settings > API Keys 创建 API Key

### 方式二：SMTP

**适用场景**：
- 使用企业邮箱
- 使用 Gmail、QQ 邮箱等
- 已有邮件服务器

---

## 配置步骤

### 1. 使用 Resend API（推荐）

#### 步骤 1：获取 Resend API Key

```bash
# 访问 https://resend.com
# 注册并登录后，进入 Settings > API Keys
# 复制你的 API Key（格式：re_xxxxxxxxxxxx）
```

#### 步骤 2：配置 .env 文件

```bash
# 编辑 .env 文件
vim .env
```

添加以下配置：

```bash
# 邮件配置
EMAIL_ENABLED=true
RESEND_API_KEY=re_your-resend-api-key-here
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

#### 步骤 3：验证域名（Resend 要求）

```bash
# 在 Resend 控制台添加域名并配置 DNS 记录
# 按照提示添加以下 DNS 记录：
#
# TXT记录：@ -> resend._domainkey
# CNAME记录：resend._domainkey -> u123456.resend.com
```

### 2. 使用 SMTP（传统方式）

#### 使用 Gmail

```bash
# 1. 启用两步验证
# 2. 生成应用专用密码
#    Google Account > Security > 2-Step Verification > App passwords
#
# 配置 .env：
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # 16位应用密码
SMTP_FROM_EMAIL=your-email@gmail.com
```

#### 使用 QQ 邮箱

```bash
# 1. 开启 SMTP 服务
#    设置 > 账户 > POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
#
# 2. 获取授权码
#    设置 > 账户 > 生成授权码
#
# 配置 .env：
EMAIL_ENABLED=true
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your-email@qq.com
SMTP_PASSWORD=your-authorization-code
SMTP_FROM_EMAIL=your-email@qq.com
```

#### 使用企业邮箱

```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.your-company.com
SMTP_PORT=587
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=notifications@company.com
```

---

## 使用方法

### 方法 1：命令行发送测试邮件

```bash
# 激活虚拟环境
source venv/bin/activate

# 发送测试邮件（指定接收邮箱）
python main.py "llm" --send-email --email your@email.com --max-results 3
```

### 方法 2：使用数据库订阅（完整流程）

```bash
# 1. 初始化数据库
python main.py --init-db

# 2. 运行完整流水线（会查询数据库中的订阅并发送）
python main.py "llm" --pipeline --max-results 5
```

### 方法 3：添加订阅到数据库

#### 方式 A：使用 Python 脚本添加订阅

```python
# add_subscription.py
import sys
sys.path.insert(0, '/home/apu/project/AgentCodes/001')

from src.database import db_manager, SubscriptionCRUD
from sqlalchemy.orm import Session

# 创建会话
session = db_manager.get_session()

try:
    # 添加订阅
    subscription = SubscriptionCRUD.create_subscription(
        session,
        user_email="your@email.com",
        keywords=["llm", "deep learning"],
        exclude_keywords=["survey", "review"],
        push_time="08:00",
        timezone="Asia/Shanghai",
    )
    
    session.commit()
    print(f"订阅添加成功！ID: {subscription.id}")
    
except Exception as e:
    session.rollback()
    print(f"添加失败: {e}")
finally:
    session.close()
```

```bash
# 运行脚本
python add_subscription.py
```

#### 方式 B：使用 SQL 直接插入

```sql
INSERT INTO subscriptions (user_email, keywords, exclude_keywords, push_time, timezone, is_active)
VALUES (
    'your@email.com',
    '["llm", "deep learning"]',
    '["survey", "review"]',
    '08:00',
    'Asia/Shanghai',
    true
);
```

### 方法 4：定时自动推送

```bash
# 每天凌晨 2 点自动运行，发送给所有订阅者
python main.py "llm" --schedule --schedule-time 02:00
```

---

## 完整示例

### 示例 1：使用 Resend 发送日报

```bash
# 1. 配置 .env
cat >> .env << 'EOF'
EMAIL_ENABLED=true
RESEND_API_KEY=re_xxxxxxxxxxxxx
SMTP_FROM_EMAIL=daily-papers@yourdomain.com
EOF

# 2. 发送测试
python main.py "llm" --send-email --email test@example.com --max-results 3
```

### 示例 2：使用 Gmail SMTP

```bash
# 1. 配置 .env
cat >> .env << 'EOF'
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_EMAIL=your-email@gmail.com
EOF

# 2. 发送测试
python main.py "llm" --send-email --email your-email@gmail.com --max-results 3
```

### 示例 3：订阅 + 定时推送

```bash
# 1. 创建订阅脚本
cat > add_sub.py << 'SCRIPT'
import sys
sys.path.insert(0, '/home/apu/project/AgentCodes/001')
from src.database import db_manager, SubscriptionCRUD

session = db_manager.get_session()
sub = SubscriptionCRUD.create_subscription(
    session,
    user_email="user@example.com",
    keywords=["medical image", "segmentation"],
    exclude_keywords=["survey"],
)
session.commit()
print(f"订阅成功: {sub.id}")
session.close()
SCRIPT

python add_sub.py

# 2. 启动定时任务
python main.py "medical image" --schedule --schedule-time 09:00
```

---

## 故障排查

### 问题 1：邮件发送失败

**错误信息**：`Failed to send email via Resend`

**解决方法**：
1. 检查 API Key 是否正确
2. 检查域名是否已验证（Resend）
3. 查看 `paper_pusher.log` 日志文件

```bash
# 查看日志
tail -50 paper_pusher.log
```

### 问题 2：SMTP 认证失败

**错误信息**：`SMTP authentication error`

**解决方法**：
1. Gmail：确认使用应用专用密码，而非账号密码
2. QQ 邮箱：确认已开启 SMTP 服务并使用授权码
3. 企业邮箱：确认 SMTP 配置正确

### 问题 3：邮件进入垃圾箱

**解决方法**：
1. 在邮件客户端中标记为"不是垃圾"
2. 添加发件地址到联系人
3. 使用 Resend 等专业邮件服务

### 问题 4：数据库订阅不生效

**检查步骤**：

```bash
# 查看所有订阅
python << 'PYTHON'
import sys
sys.path.insert(0, '/home/apu/project/AgentCodes/001')
from src.database import db_manager, SubscriptionCRUD

session = db_manager.get_session()
subs = SubscriptionCRUD.get_active_subscriptions(session)

for sub in subs:
    print(f"邮箱: {sub.user_email}, 关键词: {sub.keywords}, 激活: {sub.is_active}")

session.close()
PYTHON
```

---

## 推送日志

所有推送记录都会保存到 `push_logs` 表：

```sql
-- 查看推送历史
SELECT 
    pl.created_at,
    s.user_email,
    pl.channel,
    pl.status,
    pl.error_msg
FROM push_logs pl
JOIN subscriptions s ON pl.subscription_id = s.id
ORDER BY pl.created_at DESC
LIMIT 20;
```

---

## 邮件模板

邮件使用 HTML 模板，位于 `templates/email.html`。

可自定义：
- 邮件样式
- 布局结构
- 页眉页脚
- 公司信息
