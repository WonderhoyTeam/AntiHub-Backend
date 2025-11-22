# 共享账号管理系统

基于 FastAPI 的共享账号管理系统，集成 Plug-in API 功能，支持传统用户名密码登录和 OAuth SSO 单点登录，提供完整的 AI 聊天服务和配额管理。

## 功能特性

### ✅ 已实现功能

- **用户认证**
  - 传统用户名密码登录
  - OAuth 2.0 SSO 单点登录（支持 Linux.do）
  - JWT 令牌认证
  - 会话管理
  - 令牌黑名单机制

- **用户管理**
  - 用户信息存储(PostgreSQL)
  - OAuth 令牌管理
  - 用户状态管理(激活/禁用/禁言)
  - 信任等级系统

- **Plug-in API 集成**
  - 自动账号创建：用户注册时自动创建 Plug-in API 账号
  - API 密钥安全存储：使用 Fernet 加密算法安全存储
  - 代理请求：所有 Plug-in API 请求通过后端代理
  - OpenAI 兼容接口：支持标准的 OpenAI API 格式
  - 完整功能支持：账号管理、配额管理、聊天补全等

- **AI 聊天服务**
  - OpenAI 兼容的聊天补全 API
  - 支持流式和非流式输出
  - 多模型支持（Gemini 等）
  - 智能 Cookie 选择和轮换

- **配额管理系统**
  - 用户共享配额池
  - 自动配额恢复机制
  - 配额消耗追踪和统计
  - 专属/共享 Cookie 优先级设置

- **安全特性**
  - bcrypt 密码哈希(rounds=12)
  - JWT 令牌(HS256,24小时有效期)
  - OAuth state 验证(防止 CSRF 攻击)
  - 令牌自动过期和刷新
  - API 密钥加密存储

- **缓存系统**
  - Redis 会话存储
  - 令牌黑名单
  - OAuth state 临时存储

## 技术栈

- **Web 框架**: FastAPI 0.104+
- **数据库**: PostgreSQL + SQLAlchemy 2.0 (异步)
- **缓存**: Redis
- **认证**: PyJWT + Passlib
- **HTTP 客户端**: httpx
- **数据库迁移**: Alembic
- **数据验证**: Pydantic

## 快速开始

### 1. 环境要求

- Python 3.10+
- PostgreSQL 12+
- Redis 6+
- Plug-in API 服务（可选，用于 AI 聊天功能）

### 2. 安装依赖

```bash
# 使用 uv 
uv sync
```

### 3. 配置环境变量

复制 `.env.example` 到 `.env` 并配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件,配置以下必需项:

```bash
# 应用配置
APP_ENV=development
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/shared_accounts

# Redis 配置
REDIS_URL=redis://localhost:6379/0
# 或带密码: redis://:password@localhost:6379/0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# OAuth 配置（Linux.do）
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
OAUTH_REDIRECT_URI=http://localhost:8008/api/auth/sso/callback
OAUTH_AUTHORIZATION_ENDPOINT=https://connect.linux.do/oauth2/authorize
OAUTH_TOKEN_ENDPOINT=https://connect.linux.do/oauth2/token
OAUTH_USER_INFO_ENDPOINT=https://connect.linux.do/api/user

# Plug-in API 配置（可选）
PLUGIN_API_BASE_URL=http://localhost:8045
PLUGIN_API_ADMIN_KEY=sk-admin-your-admin-key-here
PLUGIN_API_ENCRYPTION_KEY=your-encryption-key-here-min-32-chars
```

**重要**：`PLUGIN_API_ENCRYPTION_KEY` 必须是一个有效的 Fernet 密钥（32字节的URL安全base64编码）。可以使用以下 Python 代码生成：

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 4. 数据库迁移

```bash
# 运行数据库迁移
uv run alembic upgrade head
```

### 5. 启动服务

```bash
# 使用启动脚本（推荐）
chmod +x run.sh
./run.sh

# 或直接使用 uvicorn
uv run uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload

# 或使用 Python
uv run python app/main.py
```

服务将在 http://localhost:8008 启动

## API 文档

启动服务后访问:

- **Swagger UI**: http://localhost:8008/api/docs
- **ReDoc**: http://localhost:8008/api/redoc
- **OpenAPI JSON**: http://localhost:8008/api/openapi.json

**注意**：生产环境中 API 文档将被禁用。

## API 端点

### 认证相关

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/auth/login` | 用户名密码登录 |
| GET | `/api/auth/sso/initiate` | 发起 OAuth SSO 登录 |
| GET | `/api/auth/sso/callback` | OAuth 回调处理 |
| POST | `/api/auth/logout` | 用户登出 |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 健康检查

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 系统健康状态检查 |

### API 密钥管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/api-keys` | 获取用户的 API 密钥列表 |
| POST | `/api/api-keys` | 创建新的 API 密钥 |
| DELETE | `/api/api-keys/{key_id}` | 删除指定的 API 密钥 |

### Plug-in API 代理（需要配置 Plug-in API 服务）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/plugin-api/accounts` | 获取账号列表 |
| POST | `/api/plugin-api/oauth/authorize` | 获取 OAuth 授权 URL |
| GET | `/api/plugin-api/quotas/user` | 获取用户配额信息 |
| POST | `/api/plugin-api/chat/completions` | 聊天补全（OpenAI 兼容） |
| GET | `/api/plugin-api/models` | 获取可用模型列表 |

### OpenAI 兼容接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/v1/models` | 获取模型列表 |
| POST | `/v1/chat/completions` | 聊天补全（流式/非流式） |

### 使用统计

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/usage/stats` | 获取使用统计信息 |
| GET | `/api/usage/logs` | 获取使用日志 |

## 使用示例

### 传统登录

```bash
curl -X POST "http://localhost:8008/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

### OAuth SSO 登录

```bash
# 1. 获取授权 URL
curl "http://localhost:8008/api/auth/sso/initiate"

# 2. 用户在浏览器中访问返回的 authorization_url
# 3. 授权后会重定向到 callback URL 并自动完成登录
```

### 获取当前用户信息

```bash
curl "http://localhost:8008/api/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 登出

```bash
curl -X POST "http://localhost:8008/api/auth/logout" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 创建 API 密钥

```bash
curl -X POST "http://localhost:8008/api/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的API密钥",
    "description": "用于测试的密钥"
  }'
```

### AI 聊天（需要配置 Plug-in API）

```bash
# 流式聊天
curl -X POST "http://localhost:8008/api/plugin-api/chat/completions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-high",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "stream": true
  }'

# OpenAI 兼容格式
curl -X POST "http://localhost:8008/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-high",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "stream": false
  }'
```

### 获取配额信息

```bash
curl "http://localhost:8008/api/plugin-api/quotas/user" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 项目结构

```
antigv-backend/
├── alembic/                      # 数据库迁移脚本
│   ├── versions/                 # 迁移版本文件
│   ├── env.py                    # Alembic 环境配置
│   └── script.py.mako            # 迁移脚本模板
├── app/
│   ├── api/                      # API 路由
│   │   ├── deps.py               # 依赖注入
│   │   ├── deps_flexible.py      # 灵活依赖注入
│   │   └── routes/               # 路由端点
│   │       ├── auth.py           # 认证路由
│   │       ├── health.py         # 健康检查
│   │       ├── plugin_api.py     # Plug-in API 代理
│   │       ├── api_keys.py       # API 密钥管理
│   │       ├── usage.py          # 使用统计
│   │       └── v1.py             # OpenAI 兼容接口
│   ├── cache/                    # Redis 缓存
│   │   └── redis_client.py       # Redis 客户端
│   ├── core/                     # 核心模块
│   │   ├── config.py             # 配置管理
│   │   ├── security.py           # 安全功能
│   │   └── exceptions.py         # 异常定义
│   ├── db/                       # 数据库
│   │   ├── base.py               # Base 类
│   │   └── session.py            # 会话管理
│   ├── models/                   # 数据模型
│   │   ├── user.py               # 用户模型
│   │   ├── api_key.py            # API 密钥模型
│   │   ├── oauth_token.py        # OAuth 令牌模型
│   │   ├── plugin_api_key.py     # Plug-in API 密钥模型
│   │   └── usage_log.py          # 使用日志模型
│   ├── repositories/             # 数据仓储层
│   │   ├── user_repository.py    # 用户仓储
│   │   ├── api_key_repository.py # API 密钥仓储
│   │   ├── oauth_token_repository.py # OAuth 令牌仓储
│   │   └── plugin_api_key_repository.py # Plug-in API 密钥仓储
│   ├── schemas/                  # Pydantic Schemas
│   │   ├── user.py               # 用户 Schema
│   │   ├── auth.py               # 认证 Schema
│   │   ├── api_key.py            # API 密钥 Schema
│   │   ├── token.py              # 令牌 Schema
│   │   └── plugin_api.py         # Plug-in API Schema
│   ├── services/                 # 业务逻辑层
│   │   ├── auth_service.py       # 认证服务
│   │   ├── user_service.py       # 用户服务
│   │   ├── oauth_service.py      # OAuth 服务
│   │   └── plugin_api_service.py # Plug-in API 服务
│   ├── utils/                    # 工具模块
│   │   └── encryption.py         # 加密工具
│   └── main.py                   # 应用入口
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git 忽略文件
├── .python-version               # Python 版本
├── alembic.ini                   # Alembic 配置
├── pyproject.toml                # 项目配置和依赖
├── uv.lock                       # uv 锁定文件
├── run.sh                        # 启动脚本
├── generate_encryption_key.py    # 加密密钥生成工具
├── PLUGIN_API_INTEGRATION.md     # Plug-in API 集成文档
├── plug-in-API.md               # Plug-in API 使用文档
└── README.md                     # 项目文档
```

## 开发指南

### 数据库迁移

```bash
# 创建新的迁移
uv run alembic revision --autogenerate -m "描述信息"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1

# 查看迁移历史
uv run alembic history

# 查看当前版本
uv run alembic current
```

### 代码风格

项目使用类型注解和文档字符串，请保持一致的代码风格：

- 使用 Python 3.10+ 类型注解
- 所有公共函数和类都需要文档字符串
- 遵循 PEP 8 代码规范
- 使用异步编程模式（async/await）

### 环境配置

#### 开发环境
```bash
APP_ENV=development
LOG_LEVEL=DEBUG
```

#### 生产环境
```bash
APP_ENV=production
LOG_LEVEL=INFO
# 确保使用强密码和安全的 JWT 密钥
# 配置适当的 CORS 源
# 禁用 API 文档
```

### Plug-in API 集成开发

如果要添加新的 Plug-in API 代理端点：

1. 在 `app/services/plugin_api_service.py` 中添加服务方法
2. 在 `app/api/routes/plugin_api.py` 中添加路由
3. 在 `app/schemas/plugin_api.py` 中添加相应的 Schema
4. 更新 API 文档

详细集成说明请参考 [`PLUGIN_API_INTEGRATION.md`](PLUGIN_API_INTEGRATION.md)。

### 测试

```bash
# 运行测试（如果有的话）
uv run pytest

# 运行特定测试
uv run pytest tests/test_auth.py
```

### 部署

#### Docker 部署（推荐）

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install uv && uv sync

EXPOSE 8008

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
```

#### 传统部署

```bash
# 安装依赖
uv sync

# 设置环境变量
export APP_ENV=production

# 运行数据库迁移
uv run alembic upgrade head

# 启动服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8008 --workers 4
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查 `DATABASE_URL` 配置
   - 确保 PostgreSQL 服务正在运行
   - 验证数据库用户权限

2. **Redis 连接失败**
   - 检查 `REDIS_URL` 配置
   - 确保 Redis 服务正在运行
   - 验证 Redis 密码（如果有的话）

3. **OAuth 登录失败**
   - 检查 OAuth 客户端 ID 和密钥
   - 验证回调 URL 配置
   - 确保 OAuth 服务器可访问

4. **Plug-in API 功能异常**
   - 检查 `PLUGIN_API_BASE_URL` 配置
   - 验证管理员密钥和加密密钥
   - 确保 Plug-in API 服务正在运行

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看特定级别日志
grep "ERROR" logs/app.log
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 问题报告

报告问题时请包含：

- 详细的问题描述
- 复现步骤
- 环境信息（操作系统、Python 版本等）
- 相关的错误日志

## 相关文档

- [Plug-in API 集成文档](PLUGIN_API_INTEGRATION.md)
- [Plug-in API 使用文档](plug-in-API.md)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)