"""
OIDC Provider 配置和数据模型
定义 OpenID Connect 提供商的配置结构和用户信息映射
"""
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class OIDCProviderType(str, Enum):
    """OIDC 提供商类型"""
    LINUX_DO = "linux_do"
    GITHUB = "github"
    GOOGLE = "google"
    POCKETID = "pocketid"
    GENERIC = "generic"


@dataclass
class OIDCProviderConfig:
    """
    OIDC 提供商配置

    定义 OAuth2/OIDC 提供商的所有必需端点和认证信息
    """
    # 提供商标识
    provider_id: str
    provider_name: str
    provider_type: OIDCProviderType

    # OAuth2/OIDC 端点
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str

    # 客户端凭证
    client_id: str
    client_secret: str
    redirect_uri: str

    # 可选配置
    scope: str = "openid profile email"
    response_type: str = "code"

    # 用户信息字段映射 (provider_field -> standard_field)
    user_info_mapping: Dict[str, str] = field(default_factory=dict)

    # 额外的请求参数
    extra_authorize_params: Dict[str, str] = field(default_factory=dict)
    extra_token_params: Dict[str, str] = field(default_factory=dict)

    # 令牌认证方式
    use_basic_auth: bool = True  # True: Basic Auth, False: Body params

    # 自定义 Headers
    token_headers: Dict[str, str] = field(default_factory=dict)
    userinfo_headers: Dict[str, str] = field(default_factory=dict)

    def get_user_info_claim(self, claim_name: str, default: str = None) -> str:
        """
        获取映射后的用户信息字段名

        Args:
            claim_name: 标准字段名 (如 'username', 'email')
            default: 默认字段名

        Returns:
            提供商的实际字段名
        """
        return self.user_info_mapping.get(claim_name, default or claim_name)


@dataclass
class OIDCUserInfo:
    """
    标准化的 OIDC 用户信息

    将不同提供商的用户信息标准化为统一格式
    """
    # 必需字段
    sub: str  # Subject - 用户唯一标识符
    provider: str  # 提供商标识

    # 标准 OIDC 声明
    username: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None

    # 扩展字段
    trust_level: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_provider_data(
        cls,
        provider_data: Dict[str, Any],
        provider_config: OIDCProviderConfig
    ) -> "OIDCUserInfo":
        """
        从提供商数据创建标准化用户信息

        Args:
            provider_data: 提供商返回的原始用户数据
            provider_config: 提供商配置（包含字段映射）

        Returns:
            标准化的用户信息对象
        """
        mapping = provider_config.user_info_mapping

        # 获取必需字段
        sub = str(provider_data.get(mapping.get("sub", "id")))

        # 映射可选字段
        return cls(
            sub=sub,
            provider=provider_config.provider_id,
            username=provider_data.get(mapping.get("username", "username")),
            email=provider_data.get(mapping.get("email", "email")),
            email_verified=provider_data.get(mapping.get("email_verified", "email_verified")),
            name=provider_data.get(mapping.get("name", "name")),
            given_name=provider_data.get(mapping.get("given_name", "given_name")),
            family_name=provider_data.get(mapping.get("family_name", "family_name")),
            picture=provider_data.get(mapping.get("picture", "avatar_url")),
            locale=provider_data.get(mapping.get("locale", "locale")),
            trust_level=provider_data.get(mapping.get("trust_level", "trust_level"), 0),
            raw_data=provider_data
        )

    def to_oauth_user_create_data(self) -> Dict[str, Any]:
        """
        转换为 OAuthUserCreate 所需的数据格式

        Returns:
            用户创建数据字典
        """
        return {
            "oauth_id": f"{self.provider}:{self.sub}",
            "username": self.username or self.name or f"{self.provider}_{self.sub}",
            "avatar_url": self.picture,
            "trust_level": self.trust_level
        }
