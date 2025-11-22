# Plug-in API 集成文档

## 概述

本系统已集成 plug-in-api 功能，用户注册时自动创建 plug-in-api 账号，无需手动配置。所有 plug-in-api 功能通过我们的后端代理，用户无需关心底层实现。

## 主要特性

1. **自动账号创建**：用户通过 OAuth 注册时，系统自动在 plug-in-api 创建对应账号
2. **API密钥安全存储**：plug-in-api 密钥使用加密算法安全存储，用户不可见
3. **代理请求**：所有对 plug-in-api 的请求通过我们的后端代理，用户无需直接接触密钥
4. **完整功能支持**：支持 plug-in-api 的所有功能，包括账号管理、配额管理、聊天补全等
5. **透明集成**：用户无需了解 plug-in-api 的存在，所有操作通过统一接口完成

## 配置说明

### 环境变量

在 `.env` 文件中添加以下配置：

```bash
# Plug-in API Configuration
PLUGIN_API_BASE_URL=http://localhost:8045  # plug-in-api服务地址
PLUGIN_API_ADMIN_KEY=sk-admin-xxx          # 管理员密钥（可选）
PLUGIN_API_ENCRYPTION_KEY=your-32-char-key # 用于加密存储用户密钥的密钥
```

**重要**：`PLUGIN_API_ENCRYPTION_KEY` 必须是一个有效的 Fernet 密钥（32字节的URL安全base64编码）。

可以使用以下 Python 代码生成：

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## 使用流程

### 1. 用户通过 OAuth 注册

用户通过 OAuth（如 Linux.do）注册登录时，系统会自动：
- 在我们的系统中创建用户账号
- 使用管理员权限在 plug-in-api 创建对应账号
- 将 plug-in-api 返回的 API 密钥加密存储到我们的数据库
- 用户无需任何额外操作

### 2. 获取 JWT 令牌

用户登录后获取 JWT 令牌，用于后续 API 调用。

### 3. 使用 Plug-in API 功能

用户通过我们的 API 直接使用 plug-in-api 的所有功能，系统会自动使用存储的密钥进行代理：

#### 获取 OAuth 授权 URL

```bash
POST /api/plugin-api/oauth/authorize
Authorization: Bearer <your_jwt_token>
Content-Type: application/json

{
  "is_shared": 0  # 0=专属cookie, 1=共享cookie
}
```

#### 查看账号列表

```bash
GET /api/plugin-api/accounts
Authorization: Bearer <your_jwt_token>
```

#### 查看配额信息

```bash
GET /api/plugin-api/quotas/user
Authorization: Bearer <your_jwt_token>
```

#### 聊天补全

```bash
POST /api/plugin-api/chat/completions
Authorization: Bearer <your_jwt_token>
Content-Type: application/json

{
  "model": "gemini-3-pro-high",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": true
}
```

## API 端点列表

### 密钥管理

- `GET /api/plugin-api/key` - 获取密钥信息（不返回实际密钥，仅管理用）

**注意**：用户注册时会自动创建 plug-in-api 账号，无需手动管理密钥。

### OAuth 相关

- `POST /api/plugin-api/oauth/authorize` - 获取 OAuth 授权 URL
- `POST /api/plugin-api/oauth/callback` - 提交 OAuth 回调

### 账号管理

- `GET /api/plugin-api/accounts` - 获取账号列表
- `GET /api/plugin-api/accounts/{cookie_id}` - 获取账号详情
- `PUT /api/plugin-api/accounts/{cookie_id}/status` - 更新账号状态
- `DELETE /api/plugin-api/accounts/{cookie_id}` - 删除账号
- `GET /api/plugin-api/accounts/{cookie_id}/quotas` - 获取账号配额

### 配额管理

- `GET /api/plugin-api/quotas/user` - 获取用户共享配额池
- `GET /api/plugin-api/quotas/shared-pool` - 获取共享池配额
- `GET /api/plugin-api/quotas/consumption` - 获取配额消耗记录

### OpenAI 兼容接口

- `GET /api/plugin-api/models` - 获取模型列表
- `POST /api/plugin-api/chat/completions` - 聊天补全（支持流式和非流式）

### 用户设置

- `PUT /api/plugin-api/preference` - 更新 Cookie 优先级

## 工作原理

### 用户注册流程

```
1. 用户发起 OAuth 登录
   ↓
2. OAuth 服务器验证并返回用户信息
   ↓
3. 我们的系统创建/更新用户账号
   ↓
4. 系统检查用户是否已有 plug-in API 密钥
   ↓
5. 如果没有，使用管理员权限调用 plug-in-api 创建用户
   ↓
6. plug-in-api 返回新用户的 API 密钥
   ↓
7. 系统加密存储该密钥到数据库
   ↓
8. 返回 JWT 令牌给用户
```

### API 代理流程

```
1. 用户调用我们的 API（携带 JWT）
   ↓
2. 系统验证 JWT 并获取用户 ID
   ↓
3. 从数据库获取并解密该用户的 plug-in API 密钥
   ↓
4. 使用该密钥代理请求到 plug-in-api
   ↓
5. 返回 plug-in-api 的响应给用户
   ↓
6. 更新密钥最后使用时间
```

## 安全性说明

1. **自动化管理**：用户无需手动管理 plug-in-api 密钥，降低泄露风险
2. **密钥加密**：plug-in-api 密钥在数据库中加密存储，使用 Fernet 对称加密
3. **密钥不可见**：用户永远不会看到自己的 plug-in-api 密钥
4. **JWT 认证**：所有 API 请求都需要有效的 JWT 令牌
5. **代理模式**：所有请求通过后端代理，前端不接触实际密钥
6. **审计追踪**：系统记录密钥的最后使用时间，便于审计
7. **管理员权限隔离**：管理员密钥仅用于创建用户，不用于日常操作

## 数据库结构

系统新增了 `plugin_api_keys` 表来存储用户的 API 密钥信息：

```sql
CREATE TABLE plugin_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key TEXT NOT NULL,  -- 加密存储
    plugin_user_id VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);
```

## 示例代码

### Python 示例

```python
import requests

# 1. OAuth 登录（自动创建 plug-in-api 账号）
# 用户通过浏览器完成 OAuth 流程
# 系统自动创建 plug-in-api 账号并绑定

# 2. 使用 JWT 令牌
jwt_token = "your_jwt_token_from_login"
headers = {"Authorization": f"Bearer {jwt_token}"}

# 3. 直接使用功能，无需配置密钥
# 获取账号列表
accounts = requests.get(
    "http://localhost:8000/api/plugin-api/accounts",
    headers=headers
).json()

# 4. 聊天补全
chat_response = requests.post(
    "http://localhost:8000/api/plugin-api/chat/completions",
    headers=headers,
    json={
        "model": "gemini-3-pro-high",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False
    }
)
```

## 故障排除

### 问题：自动创建 plug-in-api 账号失败

- 检查 `PLUGIN_API_ADMIN_KEY` 是否正确配置
- 确保 plug-in-api 服务正在运行且可访问
- 检查 `PLUGIN_API_BASE_URL` 是否正确
- 查看服务器日志了解具体错误

### 问题：代理请求失败

- 检查用户是否已完成注册流程
- 确保 plug-in-api 服务正在运行且可访问
- 检查数据库中是否存在该用户的密钥记录

### 问题：JWT 认证失败

- 确保请求头中包含有效的 JWT 令牌
- 检查令牌是否已过期

## 开发说明

### 添加新的代理端点

如需添加新的 plug-in-api 端点，在 `PluginAPIService` 中添加相应方法：

```python
async def new_endpoint(self, user_id: int, param: str) -> Dict[str, Any]:
    """新端点描述"""
    return await self.proxy_request(
        user_id=user_id,
        method="GET",
        path=f"/api/new-endpoint/{param}"
    )
```

然后在 `app/api/routes/plugin_api.py` 中添加路由。

## API 文档

启动服务后，访问以下地址查看完整 API 文档：

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 许可证

MIT License