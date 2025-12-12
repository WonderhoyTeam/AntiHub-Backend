"""
OIDC Provider Registry
管理和提供预定义的 OIDC 提供商配置
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import OAuthError
from app.cache.redis_client import RedisClient
from app.schemas.oidc import OIDCProviderConfig, OIDCProviderType
from app.services.oidc_provider_service import OIDCProviderService


class OIDCProviderRegistry:
    """
    OIDC Provider 注册表

    提供预定义的 OIDC 提供商配置和服务实例
    """

    @staticmethod
    def get_linux_do_config() -> OIDCProviderConfig:
        """
        获取 Linux.do OIDC 提供商配置

        Returns:
            Linux.do 提供商配置
        """
        settings = get_settings()

        return OIDCProviderConfig(
            provider_id="linux_do",
            provider_name="Linux.do",
            provider_type=OIDCProviderType.LINUX_DO,
            authorization_endpoint=settings.oauth_authorization_endpoint,
            token_endpoint=settings.oauth_token_endpoint,
            userinfo_endpoint=settings.oauth_user_info_endpoint,
            client_id=settings.oauth_client_id,
            client_secret=settings.oauth_client_secret,
            redirect_uri=settings.oauth_redirect_uri,
            scope="openid profile email",
            use_basic_auth=True,
            # Linux.do 用户信息字段映射
            user_info_mapping={
                "sub": "id",
                "username": "username",
                "name": "name",
                "email": "email",
                "picture": "avatar_url",
                "trust_level": "trust_level"
            }
        )

    @staticmethod
    def get_github_config() -> OIDCProviderConfig:
        """
        获取 GitHub OIDC 提供商配置

        Returns:
            GitHub 提供商配置
        """
        settings = get_settings()

        return OIDCProviderConfig(
            provider_id="github",
            provider_name="GitHub",
            provider_type=OIDCProviderType.GITHUB,
            authorization_endpoint=settings.github_authorize_url,
            token_endpoint=settings.github_token_url,
            userinfo_endpoint=settings.github_user_api_url,
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            redirect_uri=settings.github_redirect_uri,
            scope="read:user user:email",
            use_basic_auth=False,  # GitHub 使用 body params
            # GitHub 特定的 headers
            token_headers={"Accept": "application/json"},
            userinfo_headers={"Accept": "application/vnd.github.v3+json"},
            # GitHub 用户信息字段映射
            user_info_mapping={
                "sub": "id",
                "username": "login",
                "name": "name",
                "email": "email",
                "picture": "avatar_url",
                "trust_level": "trust_level"  # GitHub 没有 trust_level,默认为 0
            }
        )

    @staticmethod
    def get_provider_config(provider_id: str) -> OIDCProviderConfig:
        """
        根据提供商 ID 获取配置

        Args:
            provider_id: 提供商标识 (如 'linux_do', 'github')

        Returns:
            提供商配置

        Raises:
            OAuthError: 不支持的提供商
        """
        provider_configs = {
            "linux_do": OIDCProviderRegistry.get_linux_do_config,
            "github": OIDCProviderRegistry.get_github_config,
        }

        config_getter = provider_configs.get(provider_id)
        if not config_getter:
            raise OAuthError(
                message=f"不支持的 OAuth 提供商: {provider_id}",
                error_code="UNSUPPORTED_PROVIDER",
                details={"provider_id": provider_id}
            )

        return config_getter()

    @staticmethod
    def get_provider_service(
        provider_id: str,
        db: AsyncSession,
        redis: RedisClient
    ) -> OIDCProviderService:
        """
        创建 OIDC Provider 服务实例

        Args:
            provider_id: 提供商标识
            db: 数据库会话
            redis: Redis 客户端

        Returns:
            OIDC Provider 服务实例

        Raises:
            OAuthError: 不支持的提供商
        """
        config = OIDCProviderRegistry.get_provider_config(provider_id)
        return OIDCProviderService(db=db, redis=redis, provider_config=config)

    @staticmethod
    def get_supported_providers() -> Dict[str, str]:
        """
        获取所有支持的提供商列表

        Returns:
            提供商 ID 到名称的映射
        """
        return {
            "linux_do": "Linux.do",
            "github": "GitHub",
        }
