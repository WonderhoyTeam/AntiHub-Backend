# Antigravity API 使用文档

## 目录

- [认证说明](#认证说明)
- [用户管理API](#用户管理api)
- [OAuth相关API](#oauth相关api)
- [账号管理API](#账号管理api)
- [配额管理API](#配额管理api)
- [OpenAI兼容接口](#openai兼容接口)
- [配额机制说明](#配额机制说明)

---

## 认证说明

### API Key类型

1. **管理员API Key**: 配置在`config.json`中，用于用户管理
2. **用户API Key**: 创建用户时生成（`sk-xxx`格式），用于日常操作

### 认证方式

所有API请求需在请求头中携带API Key：

```http
Authorization: Bearer sk-xxx
```

---

## 用户管理API

### 1. 创建用户（管理员）

```http
POST /api/users
Authorization: Bearer {管理员API Key}
Content-Type: application/json

{
  "name": "用户名称",
  "prefer_shared": 0
}
```

**参数说明**：
- `name` (可选): 用户名称
- `prefer_shared` (可选): Cookie优先级，0=专属优先（默认），1=共享优先

**响应**：
```json
{
  "success": true,
  "message": "用户创建成功",
  "data": {
    "user_id": "uuid-xxx",
    "api_key": "sk-xxx",
    "name": "用户名称",
    "prefer_shared": 0,
    "created_at": "2025-11-21T14:00:00.000Z"
  }
}
```

### 2. 获取所有用户（管理员）

```http
GET /api/users
Authorization: Bearer {管理员API Key}
```

### 3. 更新用户Cookie优先级

```http
PUT /api/users/{user_id}/preference
Authorization: Bearer {用户API Key}
Content-Type: application/json

{
  "prefer_shared": 1
}
```

**参数说明**：
- `prefer_shared`: 0=专属优先，1=共享优先

**响应**：
```json
{
  "success": true,
  "message": "Cookie优先级已更新为共享优先",
  "data": {
    "user_id": "uuid-xxx",
    "prefer_shared": 1
  }
}
```

### 4. 重新生成API Key（管理员）

```http
POST /api/users/{user_id}/regenerate-key
Authorization: Bearer {管理员API Key}
```

### 5. 更新用户状态（管理员）

```http
PUT /api/users/{user_id}/status
Authorization: Bearer {管理员API Key}
Content-Type: application/json

{
  "status": 0
}
```

**参数说明**：
- `status`: 0=禁用，1=启用

### 6. 删除用户（管理员）

```http
DELETE /api/users/{user_id}
Authorization: Bearer {管理员API Key}
```

---

## OAuth相关API

### 1. 获取OAuth授权URL

```http
POST /api/oauth/authorize
Authorization: Bearer {用户API Key}
Content-Type: application/json

{
  "is_shared": 0
}
```

**参数说明**：
- `is_shared`: 0=专属cookie，1=共享cookie

**响应**：
```json
{
  "success": true,
  "data": {
    "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
    "state": "uuid-state",
    "expires_in": 300
  }
}
```

**使用流程**：
1. 调用此接口获取`auth_url`
2. 在浏览器中打开`auth_url`进行授权
3. 授权成功后会自动回调并保存cookie

### 2. 手动提交OAuth回调

```http
POST /api/oauth/callback/manual
Authorization: Bearer {用户API Key}
Content-Type: application/json

{
  "callback_url": "完整的回调URL"
}
```

---

## 账号管理API

### 1. 获取账号列表

```http
GET /api/accounts
Authorization: Bearer {用户API Key}
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "cookie_id": "abc123",
      "user_id": "uuid-xxx",
      "is_shared": 0,
      "status": 1,
      "expires_at": 1732201200000,
      "created_at": "2025-11-21T14:00:00.000Z"
    }
  ]
}
```

### 2. 获取单个账号信息

```http
GET /api/accounts/{cookie_id}
Authorization: Bearer {用户API Key}
```

### 3. 更新账号状态

```http
PUT /api/accounts/{cookie_id}/status
Authorization: Bearer {用户API Key}
Content-Type: application/json

{
  "status": 0
}
```

**参数说明**：
- `status`: 0=禁用，1=启用

### 4. 删除账号

```http
DELETE /api/accounts/{cookie_id}
Authorization: Bearer {用户API Key}
```

### 5. 获取账号配额信息

```http
GET /api/accounts/{cookie_id}/quotas
Authorization: Bearer {用户API Key}
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "quota_id": "uuid-xxx",
      "cookie_id": "abc123",
      "model_name": "gemini-3-pro-high",
      "reset_time": "2025-11-21T17:18:08.000Z",
      "quota": "0.9800",
      "status": 1,
      "last_fetched_at": "2025-11-21T14:00:00.000Z"
    }
  ]
}
```

**字段说明**：
- `quota`: 剩余配额比例（0.0000-1.0000）
- `status`: 1=可用（quota>0），0=不可用（quota=0）

---

## 配额管理API

### 1. 获取用户共享配额池

```http
GET /api/quotas/user
Authorization: Bearer {用户API Key}
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "pool_id": "uuid-xxx",
      "user_id": "uuid-xxx",
      "model_name": "gemini-3-pro-high",
      "quota": "1.5000",
      "max_quota": "2.0000",
      "last_recovered_at": "2025-11-21T16:00:00.000Z",
      "last_updated_at": "2025-11-21T16:30:00.000Z"
    }
  ]
}
```

**字段说明**：
- `quota`: 当前可用配额（使用共享cookie时会扣减）
- `max_quota`: 配额上限（2 × 用户共享cookie数量）
- `last_recovered_at`: 最后恢复时间

### 2. 获取共享池配额

```http
GET /api/quotas/shared-pool
Authorization: Bearer {用户API Key}
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "model_name": "gemini-3-pro-high",
      "total_quota": "2.4500",
      "earliest_reset_time": "2025-11-22T01:18:08.000Z",
      "available_cookies": 5,
      "status": 1,
      "last_fetched_at": "2025-11-21T16:45:30.000Z"
    }
  ]
}
```

**字段说明**：
- `total_quota`: 所有共享cookie的配额总和
- `available_cookies`: 可用的共享cookie数量

### 3. 获取配额消耗记录

```http
GET /api/quotas/consumption?limit=100&start_date=2025-11-01&end_date=2025-11-30
Authorization: Bearer {用户API Key}
```

**参数说明**：
- `limit` (可选): 限制返回数量
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "log_id": "uuid-xxx",
      "user_id": "uuid-xxx",
      "cookie_id": "abc123",
      "model_name": "gemini-3-pro-high",
      "quota_before": "0.8500",
      "quota_after": "0.7200",
      "quota_consumed": "0.1300",
      "is_shared": 1,
      "consumed_at": "2025-11-21T14:00:00.000Z"
    }
  ]
}
```

**字段说明**：
- `quota_before`: 对话开始前的quota
- `quota_after`: 对话结束后的quota
- `quota_consumed`: 本次消耗（quota_before - quota_after）
- `is_shared`: 1=共享cookie，0=专属cookie

**注意**：
- 所有cookie的消耗都会记录
- 但只有共享cookie的消耗会从用户共享配额池扣除

### 4. 获取模型消耗统计

```http
GET /api/quotas/consumption/stats/{model_name}
Authorization: Bearer {用户API Key}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "total_requests": "150",
    "total_quota_consumed": "19.5000",
    "avg_quota_consumed": "0.1300",
    "last_used_at": "2025-11-21T14:00:00.000Z"
  }
}
```

### 5. 获取配额即将耗尽的模型（管理员）

```http
GET /api/quotas/low?threshold=0.1
Authorization: Bearer {管理员API Key}
```

**参数说明**：
- `threshold` (可选): 配额阈值，默认0.1（10%）

---

## OpenAI兼容接口

### 1. 获取模型列表

```http
GET /v1/models
Authorization: Bearer {用户API Key}
```

**响应**：
```json
{
  "object": "list",
  "data": [
    {
      "id": "gemini-3-pro-high",
      "object": "model",
      "created": 1732201200,
      "owned_by": "google"
    }
  ]
}
```

### 2. 聊天补全

**流式输出（推荐）**：

```http
POST /v1/chat/completions
Authorization: Bearer {用户API Key}
Content-Type: application/json

{
  "model": "gemini-3-pro-high",
  "messages": [
    {
      "role": "user",
      "content": "你好"
    }
  ],
  "stream": true,
  "temperature": 1.0,
  "max_tokens": 8096
}
```

**非流式输出**：

```http
POST /v1/chat/completions
Authorization: Bearer {用户API Key}
Content-Type: application/json

{
  "model": "gemini-3-pro-high",
  "messages": [
    {
      "role": "user",
      "content": "你好"
    }
  ],
  "stream": false
}
```

**参数说明**：
- `model` (必需): 模型名称
- `messages` (必需): 消息数组
- `stream` (可选): 是否流式输出，默认true
- `temperature` (可选): 温度参数，默认1.0
- `max_tokens` (可选): 最大输出token数
- `tools` (可选): 工具调用配置

---

## 配额机制说明

### Cookie配额（model_quotas表）

- **来源**: Google API返回的`remainingFraction`
- **范围**: 0.0000 - 1.0000
- **状态**: 
  - quota > 0 → status = 1（可用）
  - quota = 0 → status = 0（禁用）
- **更新**: 每次对话后自动更新
- **重置**: Google API自动重置（按`reset_time`）

### 用户共享配额池（user_shared_quota_pool表）

#### 初始化
- 用户创建时，共享配额池为空
- 上传共享cookie时自动初始化

#### 配额上限
```
max_quota = 2 × n
```
其中`n`为用户有效的共享cookie数量

#### 配额恢复
- **频率**: 每小时自动恢复
- **恢复量**: `2n × 0.2 = 0.4n`
- **上限**: 恢复后不超过`max_quota`
- **方式**: 定时任务（cron）

#### 配额扣减
- **时机**: 使用共享cookie对话时
- **扣减量**: `quota_before - quota_after`
- **注意**: 专属cookie不扣减配额池

### Cookie选择策略

#### 1. 优先级设置
```http
PUT /api/users/{user_id}/preference
{
  "prefer_shared": 0  // 0=专属优先, 1=共享优先
}
```

#### 2. 选择逻辑

**专属优先（prefer_shared=0）**：
```
可用cookie = [专属cookies...] + [共享cookies...]
```

**共享优先（prefer_shared=1）**：
```
可用cookie = [共享cookies...] + [专属cookies...]
```

#### 3. 过滤规则

1. Cookie的`status = 1`（启用）
2. 模型quota > 0
3. 如果是共享cookie，用户共享配额池quota > 0

#### 4. 选择方式

- **随机选择**: 从过滤后的列表中随机选一个
- **自动轮换**: 如果选中的cookie实时quota=0，自动重新选择
- **最多重试**: 5次

### 对话流程

```
1. 用户发送chat请求
   ↓
2. 根据优先级获取cookie列表
   ↓
3. 过滤可用cookie（status=1, quota>0, 共享配额池>0）
   ↓
4. 随机选择一个cookie
   ↓
5. 实时刷新该cookie的quota
   ↓
6. 如果quota=0，重新随机选择（最多5次）
   ↓
7. 使用选中的cookie发送请求
   ↓
8. 对话完成后：
   - 更新cookie的quota
   - 记录quota消耗
   - 如果是共享cookie，扣减用户配额池
```

### 配额恢复示例

**用户有3个共享cookie**：
- 配额上限: `2 × 3 = 6.0`
- 每小时恢复: `2 × 3 × 0.2 = 1.2`

**时间线**：
- 00:00 - quota = 6.0（满额）
- 00:30 - 使用2.5，quota = 3.5
- 01:00 - 恢复1.2，quota = 4.7
- 01:30 - 使用1.0，quota = 3.7
- 02:00 - 恢复1.2，quota = 4.9
- 02:30 - 使用0.5，quota = 4.4
- 03:00 - 恢复1.2，quota = 5.6
- 继续...最高恢复到6.0

### 最佳实践

1. **专属cookie**: 适合高频使用，不受配额池限制
2. **共享cookie**: 适合公共使用，配额池自动恢复
3. **配额监控**: 定期查看`/api/quotas/user`和`/api/quotas/shared-pool`
4. **合理设置优先级**: 根据使用场景选择专属优先或共享优先
5. **及时添加cookie**: 配额不足时添加更多共享cookie可提高上限和恢复速度

---

## 错误处理

### 常见错误码

- `400`: 请求参数错误
- `401`: API Key验证失败
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

### 错误响应格式

```json
{
  "error": "错误信息"
}
```

### 常见错误

**所有cookie配额已耗尽**：
```json
{
  "error": "已尝试5次，所有cookie的配额都已耗尽"
}
```

**用户共享配额不足**：
```json
{
  "error": "所有账号对模型 xxx 的配额已耗尽或用户共享配额不足"
}
```

**解决方案**：
1. 等待配额恢复（每小时自动）
2. 添加更多cookie
3. 使用专属cookie

---

## 完整使用示例

### 1. 创建用户并上传cookie

```bash
# 1. 创建用户（管理员操作）
curl -X POST http://localhost:8045/api/users \
  -H "Authorization: Bearer sk-admin-xxx" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试用户", "prefer_shared": 0}'

# 响应中获取 api_key

# 2. 获取OAuth授权URL
curl -X POST http://localhost:8045/api/oauth/authorize \
  -H "Authorization: Bearer sk-user-xxx" \
  -H "Content-Type: application/json" \
  -d '{"is_shared": 1}'

# 3. 在浏览器中打开返回的auth_url进行授权

# 4. 授权成功后自动保存cookie
```

### 2. 查看配额状态

```bash
# 查看用户共享配额池
curl http://localhost:8045/api/quotas/user \
  -H "Authorization: Bearer sk-user-xxx"

# 查看共享池总配额
curl http://localhost:8045/api/quotas/shared-pool \
  -H "Authorization: Bearer sk-user-xxx"
```

### 3. 发送聊天请求

```bash
curl -X POST http://localhost:8045/v1/chat/completions \
  -H "Authorization: Bearer sk-user-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-high",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": false
  }'
```

### 4. 查看消耗记录

```bash
curl "http://localhost:8045/api/quotas/consumption?limit=10" \
  -H "Authorization: Bearer sk-user-xxx"
```

---

## 许可证

MIT License