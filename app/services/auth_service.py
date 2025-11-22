"""
认证服务
提供用户认证、JWT 令牌管理、会话管理等功能
"""
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password,
    create_access_token,
    verify_access_token,
    extract_token_jti,
    get_token_remaining_seconds,
)
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenBlacklistedError,
    UserNotFoundError,
    AccountDisabledError,
    AccountSilencedError,
)
from app.repositories.user_repository import UserRepository
from app.cache.redis_client import RedisClient
from app.models.user import User
from app.schemas.token import TokenPayload


class AuthService:
    """认证服务类"""
    
    def __init__(self, db: AsyncSession, redis: RedisClient):
        """
        初始化认证服务
        
        Args:
            db: 数据库会话
            redis: Redis 客户端
        """
        self.db = db
        self.redis = redis
        self.user_repo = UserRepository(db)
    
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> User:
        """
        验证用户名和密码
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            验证成功的 User 对象
            
        Raises:
            InvalidCredentialsError: 用户名或密码错误
            AccountDisabledError: 账号已被禁用
        """
        # 获取用户
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise InvalidCredentialsError(
                message="用户名或密码错误",
                details={"username": username}
            )
        
        # 检查密码
        if not user.password_hash:
            raise InvalidCredentialsError(
                message="该账号未设置密码,请使用 OAuth 登录"
            )
        
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError(
                message="用户名或密码错误"
            )
        
        # 检查账号状态
        if not user.is_active:
            raise AccountDisabledError(
                message="账号已被禁用",
                details={"user_id": user.id}
            )
        
        return user
    
    async def create_user_token(
        self,
        user: User,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        为用户创建 JWT 访问令牌
        
        Args:
            user: 用户对象
            additional_claims: 额外的声明数据
            
        Returns:
            JWT 令牌字符串
        """
        token = create_access_token(
            user_id=user.id,
            username=user.username,
            additional_claims=additional_claims
        )
        return token
    
    async def verify_token(self, token: str) -> TokenPayload:
        """
        验证 JWT 令牌
        
        Args:
            token: JWT 令牌字符串
            
        Returns:
            令牌 payload
            
        Raises:
            InvalidTokenError: 令牌无效
            TokenExpiredError: 令牌已过期
            TokenBlacklistedError: 令牌已被加入黑名单
        """
        try:
            # 验证令牌
            payload = verify_access_token(token)
            if not payload:
                raise InvalidTokenError(message="令牌无效")
            
            # 检查令牌是否在黑名单中
            jti = payload.get("jti")
            if jti and await self.is_token_blacklisted(jti):
                raise TokenBlacklistedError(
                    message="令牌已失效",
                    details={"jti": jti}
                )
            
            return TokenPayload(**payload)
            
        except Exception as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError(message="令牌已过期")
            raise InvalidTokenError(
                message="令牌无效",
                details={"error": str(e)}
            )
    
    async def get_current_user(self, token: str) -> User:
        """
        根据令牌获取当前用户
        
        Args:
            token: JWT 令牌字符串
            
        Returns:
            User 对象
            
        Raises:
            InvalidTokenError: 令牌无效
            UserNotFoundError: 用户不存在
            AccountDisabledError: 账号已被禁用
        """
        # 验证令牌
        payload = await self.verify_token(token)
        
        # 获取用户
        user_id = int(payload.sub)
        user = await self.user_repo.get_by_id(user_id)
        
        if not user:
            raise UserNotFoundError(
                message="用户不存在",
                details={"user_id": user_id}
            )
        
        # 检查账号状态
        if not user.is_active:
            raise AccountDisabledError(
                message="账号已被禁用",
                details={"user_id": user.id}
            )
        
        return user
    
    # ==================== 会话管理 ====================
    
    async def create_session(
        self,
        user_id: int,
        token: str,
        ttl: int = 86400  # 24小时
    ) -> bool:
        """
        创建用户会话
        
        Args:
            user_id: 用户 ID
            token: JWT 令牌
            ttl: 会话有效期(秒)
            
        Returns:
            创建成功返回 True
        """
        session_data = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.utcnow().isoformat()
        }
        return await self.redis.create_session(user_id, session_data, ttl)
    
    async def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户会话
        
        Args:
            user_id: 用户 ID
            
        Returns:
            会话数据,不存在返回 None
        """
        return await self.redis.get_session(user_id)
    
    async def delete_session(self, user_id: int) -> bool:
        """
        删除用户会话
        
        Args:
            user_id: 用户 ID
            
        Returns:
            删除成功返回 True
        """
        return await self.redis.delete_session(user_id)
    
    # ==================== 令牌黑名单管理 ====================
    
    async def blacklist_token(self, token: str) -> bool:
        """
        将令牌加入黑名单
        
        Args:
            token: JWT 令牌字符串
            
        Returns:
            添加成功返回 True
        """
        # 提取 JTI
        jti = extract_token_jti(token)
        if not jti:
            return False
        
        # 获取令牌剩余有效时间
        remaining_seconds = get_token_remaining_seconds(token)
        if not remaining_seconds or remaining_seconds <= 0:
            # 令牌已过期,无需加入黑名单
            return True
        
        # 加入黑名单
        return await self.redis.blacklist_token(jti, remaining_seconds)
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        检查令牌是否在黑名单中
        
        Args:
            jti: JWT ID
            
        Returns:
            在黑名单中返回 True
        """
        return await self.redis.is_token_blacklisted(jti)
    
    # ==================== 登录登出流程 ====================
    
    async def login(
        self,
        username: str,
        password: str
    ) -> tuple[str, User]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            (JWT 令牌, User 对象)
        """
        # 验证用户
        user = await self.authenticate_user(username, password)
        
        # 更新最后登录时间
        await self.user_repo.update_last_login(user.id)
        
        # 创建令牌
        token = await self.create_user_token(user)
        
        # 创建会话
        await self.create_session(user.id, token)
        
        return token, user
    
    async def logout(self, user_id: int, token: str) -> bool:
        """
        用户登出
        
        Args:
            user_id: 用户 ID
            token: JWT 令牌
            
        Returns:
            登出成功返回 True
        """
        # 删除会话
        await self.delete_session(user_id)
        
        # 将令牌加入黑名单
        await self.blacklist_token(token)
        
        return True