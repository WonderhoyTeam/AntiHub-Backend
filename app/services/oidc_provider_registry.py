"""
OIDC Provider Registry
管理和提供预定义的 OIDC 提供商配置
"""
from typing import Any, Dict, List, Optional
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
    def is_provider_enabled(provider_id: str) -> bool:
        """
        检查提供商是否已启用（已配置必要的凭据）

        Args:
            provider_id: 提供商标识

        Returns:
            如果提供商已配置则返回 True
        """
        settings = get_settings()
        if provider_id == "linux_do":
            return settings.linuxdo_enabled
        elif provider_id == "github":
            return settings.github_enabled
        elif provider_id == "pocketid":
            return settings.pocketid_enabled
        return False

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
            authorization_endpoint=settings.linuxdo_authorization_endpoint,
            token_endpoint=settings.linuxdo_token_endpoint,
            userinfo_endpoint=settings.linuxdo_user_info_endpoint,
            client_id=settings.linuxdo_client_id,
            client_secret=settings.linuxdo_client_secret,
            redirect_uri=settings.linuxdo_redirect_uri,
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
    def get_pocketid_config() -> OIDCProviderConfig:
        """
        获取 PocketID OIDC 提供商配置

        PocketID is a self-hosted OIDC provider with passkey support.
        Follows standard OIDC specification.

        Returns:
            PocketID 提供商配置
        """
        settings = get_settings()

        # PocketID base URL (e.g., https://pocketid.example.com)
        base_url = settings.pocketid_base_url.rstrip('/')

        return OIDCProviderConfig(
            provider_id="pocketid",
            provider_name="PocketID",
            provider_type=OIDCProviderType.POCKETID,
            # Standard OIDC endpoints
            authorization_endpoint=f"{base_url}/authorize",
            token_endpoint=f"{base_url}/token",
            userinfo_endpoint=f"{base_url}/userinfo",
            client_id=settings.pocketid_client_id,
            client_secret=settings.pocketid_client_secret,
            redirect_uri=settings.pocketid_redirect_uri,
            scope="openid profile email",
            use_basic_auth=True,  # Standard OIDC uses Basic Auth
            # PocketID user info mapping (standard OIDC claims)
            user_info_mapping={
                "sub": "sub",  # Standard OIDC subject identifier
                "username": "preferred_username",  # Or "email" if no username
                "name": "name",
                "email": "email",
                "email_verified": "email_verified",
                "picture": "picture",
                "trust_level": "trust_level"  # Custom claim, defaults to 0
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
            OAuthError: 不支持的提供商或提供商未启用
        """
        provider_configs = {
            "linux_do": OIDCProviderRegistry.get_linux_do_config,
            "github": OIDCProviderRegistry.get_github_config,
            "pocketid": OIDCProviderRegistry.get_pocketid_config,
        }

        config_getter = provider_configs.get(provider_id)
        if not config_getter:
            raise OAuthError(
                message=f"不支持的 OAuth 提供商: {provider_id}",
                error_code="UNSUPPORTED_PROVIDER",
                details={"provider_id": provider_id}
            )

        # Check if provider is enabled
        if not OIDCProviderRegistry.is_provider_enabled(provider_id):
            raise OAuthError(
                message=f"OAuth 提供商未配置: {provider_id}",
                error_code="PROVIDER_NOT_CONFIGURED",
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
        获取所有已启用的提供商列表

        Returns:
            提供商 ID 到名称的映射（仅包含已配置的提供商）
        """
        all_providers = {
            "linux_do": "Linux.do",
            "github": "GitHub",
            "pocketid": "PocketID",
        }
        return {
            provider_id: name
            for provider_id, name in all_providers.items()
            if OIDCProviderRegistry.is_provider_enabled(provider_id)
        }

    @staticmethod
    def get_provider_metadata(provider_id: str) -> Optional[Dict[str, Any]]:
        """
        获取提供商的详细元数据

        Args:
            provider_id: 提供商标识

        Returns:
            提供商元数据，如果提供商不存在或未启用则返回 None
        """
        # Check if provider is enabled first
        if not OIDCProviderRegistry.is_provider_enabled(provider_id):
            return None

        try:
            config = OIDCProviderRegistry.get_provider_config(provider_id)

            # Provider-specific descriptions
            descriptions = {
                "linux_do": "Linux.do community authentication",
                "github": "GitHub OAuth authentication",
                "pocketid": "Self-hosted OIDC with passkey support"
            }

            return {
                "id": config.provider_id,
                "name": config.provider_name,
                "type": config.provider_type.value,
                "enabled": True,
                "supports_refresh": True,
                "description": descriptions.get(provider_id, f"{config.provider_name} OAuth/OIDC authentication")
            }
        except Exception:
            return None

    @staticmethod
    def get_all_enabled_providers_metadata() -> List[Dict[str, Any]]:
        """
        获取所有已启用提供商的元数据列表

        Returns:
            已启用提供商的元数据列表
        """
        all_provider_ids = ["linux_do", "github", "pocketid"]
        result = []
        for provider_id in all_provider_ids:
            metadata = OIDCProviderRegistry.get_provider_metadata(provider_id)
            if metadata:
                result.append(metadata)
        return result
