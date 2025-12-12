"""
OIDC 认证路由
提供基于 OpenID Connect 的通用 OAuth 认证端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from app.api.deps import (
    get_db,
    get_redis,
    get_user_service,
    get_auth_service,
    get_plugin_api_service,
)
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.plugin_api_service import PluginAPIService
from app.services.oidc_provider_registry import OIDCProviderRegistry
from app.schemas.auth import LoginResponse, OAuthInitiateResponse, OAuthCallbackParams
from app.schemas.user import UserResponse, OAuthUserCreate
from app.core.config import get_settings
from app.core.exceptions import (
    InvalidOAuthStateError,
    OAuthError,
    AccountCreationDisabledError,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.redis_client import RedisClient


router = APIRouter(prefix="/auth/oidc", tags=["OIDC 认证"])


# ==================== OIDC 通用登录流程 ====================

@router.get(
    "/{provider}/login",
    response_model=OAuthInitiateResponse,
    summary="发起 OIDC 登录",
    description="通过指定的 OIDC 提供商发起登录流程"
)
async def initiate_oidc_login(
    provider: str = Path(..., description="提供商标识 (linux_do, github)"),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    发起 OIDC 登录流程

    支持的提供商:
    - linux_do: Linux.do
    - github: GitHub

    生成授权 URL 和 state 参数,客户端应重定向到返回的 authorization_url
    """
    try:
        # 获取 OIDC 服务实例
        oidc_service = OIDCProviderRegistry.get_provider_service(
            provider_id=provider,
            db=db,
            redis=redis
        )

        # 生成 state
        state = oidc_service.generate_state()

        # 存储 state
        await oidc_service.store_state(state)

        # 生成授权 URL
        authorization_url = oidc_service.generate_authorization_url(state)

        return OAuthInitiateResponse(
            authorization_url=authorization_url,
            state=state
        )

    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发起 OIDC 登录失败: {str(e)}"
        )


@router.post(
    "/{provider}/callback",
    response_model=LoginResponse,
    summary="OIDC 回调处理",
    description="处理 OIDC 授权回调,交换令牌并创建或更新用户"
)
async def oidc_callback(
    provider: str = Path(..., description="提供商标识 (linux_do, github)"),
    params: OAuthCallbackParams = None,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    plugin_api_service: PluginAPIService = Depends(get_plugin_api_service)
):
    """
    OIDC 回调处理

    处理流程:
    1. 验证 state 参数
    2. 交换授权码获取访问令牌
    3. 使用访问令牌获取用户信息
    4. 创建或更新用户
    5. 自动创建 plug-in API 账号(仅新用户)
    6. 返回系统 JWT 令牌
    """
    settings = get_settings()
    code = params.code
    state = params.state

    try:
        # 获取 OIDC 服务实例
        oidc_service = OIDCProviderRegistry.get_provider_service(
            provider_id=provider,
            db=db,
            redis=redis
        )

        # 1. 验证 state
        await oidc_service.verify_state(state)

        # 2. 交换授权码获取访问令牌
        oauth_token = await oidc_service.exchange_code_for_token(code)

        # 3. 使用访问令牌获取用户信息 (标准化格式)
        user_info = await oidc_service.get_user_info(oauth_token.access_token)

        # 4. 转换为 OAuthUserCreate 格式并创建/更新用户
        oauth_user_data = OAuthUserCreate(**user_info.to_oauth_user_create_data())
        user = await user_service.create_user_from_oauth(oauth_user_data)

        # 4.5 自动创建 plug-in-api 账号并绑定（仅对新用户）
        try:
            # 检查用户是否已有 plug-in API 密钥
            has_key = await plugin_api_service.repo.exists(user.id)
            if not has_key:
                result = await plugin_api_service.auto_create_and_bind_plugin_user(
                    user_id=user.id,
                    username=user.username,
                    prefer_shared=0  # 默认专属优先
                )
                print(f"✅ 自动创建plug-in账号成功: user_id={user.id}, plugin_user_id={result.plugin_user_id}")
        except Exception as e:
            # 记录错误但不影响登录流程
            print(f"❌ 自动创建plug-in账号失败: {e}")

        # 5. 保存 OAuth 令牌
        expires_at = oidc_service.calculate_token_expiry(oauth_token.expires_in)
        await user_service.save_oauth_token(user.id, oauth_token, expires_at)

        # 6. 更新最后登录时间
        await user_service.update_last_login(user.id)

        # 7. 创建系统令牌对（access + refresh）
        access_token, refresh_token = await auth_service.create_token_pair(user)

        # 8. 创建会话
        await auth_service.create_session(user.id, access_token)

        # 9. 返回响应
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_seconds,
            user=UserResponse.model_validate(user)
        )

    except InvalidOAuthStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except AccountCreationDisabledError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OIDC 回调处理失败: {str(e)}"
        )


@router.get(
    "/providers",
    summary="获取支持的 OIDC 提供商列表",
    description="返回所有可用的 OIDC 提供商"
)
async def list_providers():
    """
    获取支持的 OIDC 提供商列表

    返回所有配置的 OIDC 提供商及其显示名称
    """
    try:
        providers = OIDCProviderRegistry.get_supported_providers()
        return {
            "providers": [
                {"id": provider_id, "name": provider_name}
                for provider_id, provider_name in providers.items()
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提供商列表失败: {str(e)}"
        )
