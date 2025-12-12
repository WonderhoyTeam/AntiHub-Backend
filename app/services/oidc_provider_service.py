"""
通用 OIDC Provider 服务
实现标准的 OpenID Connect / OAuth 2.0 授权流程
"""
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    OAuthError,
    InvalidOAuthStateError,
    OAuthTokenExchangeError,
    OAuthUserInfoError,
)
from app.cache.redis_client import RedisClient
from app.repositories.oauth_token_repository import OAuthTokenRepository
from app.schemas.token import OAuthTokenData
from app.schemas.oidc import OIDCProviderConfig, OIDCUserInfo


class OIDCProviderService:
    """
    通用 OIDC Provider 服务类

    实现标准的 OpenID Connect / OAuth 2.0 流程，支持多种提供商
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: RedisClient,
        provider_config: OIDCProviderConfig
    ):
        """
        初始化 OIDC Provider 服务

        Args:
            db: 数据库会话
            redis: Redis 客户端
            provider_config: OIDC 提供商配置
        """
        self.db = db
        self.redis = redis
        self.config = provider_config
        self.token_repo = OAuthTokenRepository(db)

    # ==================== OAuth 授权流程 ====================

    def generate_state(self) -> str:
        """
        生成 OAuth state 参数

        Returns:
            随机 state 字符串
        """
        return secrets.token_urlsafe(32)

    async def store_state(
        self,
        state: str,
        data: Optional[Dict[str, Any]] = None,
        ttl: int = 600  # 10分钟
    ) -> bool:
        """
        存储 OAuth state

        Args:
            state: OAuth state 字符串
            data: 额外的状态数据
            ttl: 有效期(秒)

        Returns:
            存储成功返回 True
        """
        state_key = f"oidc:{self.config.provider_id}:state:{state}"
        return await self.redis.store_oauth_state(state_key, data, ttl)

    async def verify_state(self, state: str) -> Optional[Dict[str, Any]]:
        """
        验证 OAuth state
        验证后会自动删除 state

        Args:
            state: OAuth state 字符串

        Returns:
            state 有效则返回存储的数据,无效返回 None

        Raises:
            InvalidOAuthStateError: state 无效
        """
        state_key = f"oidc:{self.config.provider_id}:state:{state}"
        data = await self.redis.verify_oauth_state(state_key)
        if data is None:
            raise InvalidOAuthStateError(
                message=f"无效的 {self.config.provider_name} OAuth state",
                details={"state": state, "provider": self.config.provider_id}
            )
        return data

    def generate_authorization_url(
        self,
        state: str,
        redirect_uri: Optional[str] = None
    ) -> str:
        """
        生成 OAuth 授权 URL

        Args:
            state: OAuth state 参数
            redirect_uri: 回调地址(可选)

        Returns:
            授权 URL
        """
        params = {
            "client_id": self.config.client_id,
            "response_type": self.config.response_type,
            "state": state,
            "redirect_uri": redirect_uri or self.config.redirect_uri,
            "scope": self.config.scope,
        }

        # 添加额外的授权参数
        params.update(self.config.extra_authorize_params)

        base_url = self.config.authorization_endpoint
        return f"{base_url}?{urlencode(params)}"

    # ==================== 令牌交换 ====================

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: Optional[str] = None
    ) -> OAuthTokenData:
        """
        使用授权码交换访问令牌

        Args:
            code: OAuth 授权码
            redirect_uri: 回调地址(可选)

        Returns:
            OAuth 令牌数据

        Raises:
            OAuthTokenExchangeError: 令牌交换失败
        """
        try:
            async with httpx.AsyncClient() as client:
                # 准备请求参数
                data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri or self.config.redirect_uri,
                }

                # 添加额外的令牌参数
                data.update(self.config.extra_token_params)

                # 准备认证和 headers
                auth = None
                headers = dict(self.config.token_headers)

                if self.config.use_basic_auth:
                    # 使用 Basic Auth 传递 client_id 和 client_secret
                    auth = (self.config.client_id, self.config.client_secret)
                else:
                    # 将凭证放在请求体中
                    data["client_id"] = self.config.client_id
                    data["client_secret"] = self.config.client_secret

                # 发送令牌交换请求
                response = await client.post(
                    self.config.token_endpoint,
                    data=data,
                    auth=auth,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise OAuthTokenExchangeError(
                        message=f"{self.config.provider_name} OAuth 令牌交换失败",
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                            "provider": self.config.provider_id
                        }
                    )

                # 解析响应
                token_data = response.json()

                # 检查是否有错误
                if "error" in token_data:
                    raise OAuthTokenExchangeError(
                        message=f"{self.config.provider_name} OAuth 错误: {token_data.get('error_description', token_data.get('error'))}",
                        details=token_data
                    )

                return OAuthTokenData(
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "bearer"),
                    expires_in=token_data.get("expires_in"),
                    scope=token_data.get("scope")
                )

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                message=f"{self.config.provider_name} OAuth 令牌交换请求失败",
                details={"error": str(e), "provider": self.config.provider_id}
            )
        except Exception as e:
            if isinstance(e, OAuthTokenExchangeError):
                raise
            raise OAuthTokenExchangeError(
                message=f"{self.config.provider_name} OAuth 令牌交换失败",
                details={"error": str(e), "provider": self.config.provider_id}
            )

    # ==================== 用户信息获取 ====================

    async def get_user_info(self, access_token: str) -> OIDCUserInfo:
        """
        获取 OIDC 用户信息并标准化

        Args:
            access_token: OAuth 访问令牌

        Returns:
            标准化的用户信息对象

        Raises:
            OAuthUserInfoError: 获取用户信息失败
        """
        try:
            async with httpx.AsyncClient() as client:
                # 使用访问令牌请求用户信息
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    **self.config.userinfo_headers
                }

                response = await client.get(
                    self.config.userinfo_endpoint,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise OAuthUserInfoError(
                        message=f"获取 {self.config.provider_name} 用户信息失败",
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                            "provider": self.config.provider_id
                        }
                    )

                # 解析用户信息
                user_data = response.json()

                # 使用配置的映射标准化用户信息
                user_info = OIDCUserInfo.from_provider_data(
                    provider_data=user_data,
                    provider_config=self.config
                )

                return user_info

        except httpx.HTTPError as e:
            raise OAuthUserInfoError(
                message=f"获取 {self.config.provider_name} 用户信息请求失败",
                details={"error": str(e), "provider": self.config.provider_id}
            )
        except Exception as e:
            if isinstance(e, OAuthUserInfoError):
                raise
            raise OAuthUserInfoError(
                message=f"获取 {self.config.provider_name} 用户信息失败",
                details={"error": str(e), "provider": self.config.provider_id}
            )

    # ==================== 令牌刷新 ====================

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> OAuthTokenData:
        """
        使用刷新令牌获取新的访问令牌

        Args:
            refresh_token: OAuth 刷新令牌

        Returns:
            新的 OAuth 令牌数据

        Raises:
            OAuthTokenExchangeError: 令牌刷新失败
        """
        try:
            async with httpx.AsyncClient() as client:
                # 准备请求参数
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }

                # 准备认证和 headers
                auth = None
                headers = dict(self.config.token_headers)

                if self.config.use_basic_auth:
                    auth = (self.config.client_id, self.config.client_secret)
                else:
                    data["client_id"] = self.config.client_id
                    data["client_secret"] = self.config.client_secret

                # 发送刷新令牌请求
                response = await client.post(
                    self.config.token_endpoint,
                    data=data,
                    auth=auth,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise OAuthTokenExchangeError(
                        message=f"{self.config.provider_name} OAuth 令牌刷新失败",
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                            "provider": self.config.provider_id
                        }
                    )

                # 解析响应
                token_data = response.json()

                return OAuthTokenData(
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token") or refresh_token,
                    token_type=token_data.get("token_type", "bearer"),
                    expires_in=token_data.get("expires_in"),
                    scope=token_data.get("scope")
                )

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                message=f"{self.config.provider_name} OAuth 令牌刷新请求失败",
                details={"error": str(e), "provider": self.config.provider_id}
            )
        except Exception as e:
            if isinstance(e, OAuthTokenExchangeError):
                raise
            raise OAuthTokenExchangeError(
                message=f"{self.config.provider_name} OAuth 令牌刷新失败",
                details={"error": str(e), "provider": self.config.provider_id}
            )

    # ==================== 辅助方法 ====================

    def calculate_token_expiry(
        self,
        expires_in: Optional[int] = None
    ) -> datetime:
        """
        计算令牌过期时间

        Args:
            expires_in: 过期时间(秒),默认 3600

        Returns:
            过期时间
        """
        seconds = expires_in or 3600
        return datetime.utcnow() + timedelta(seconds=seconds)
