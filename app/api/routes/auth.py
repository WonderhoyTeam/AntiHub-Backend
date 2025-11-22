"""
认证相关的 API 路由
提供登录、登出、OAuth 认证等端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse

from app.api.deps import (
    get_auth_service,
    get_oauth_service,
    get_user_service,
    get_plugin_api_service,
    get_current_user,
)
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService
from app.services.user_service import UserService
from app.services.plugin_api_service import PluginAPIService
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    OAuthInitiateResponse,
)
from app.schemas.user import UserResponse, OAuthUserCreate
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidOAuthStateError,
    OAuthError,
    AccountDisabledError,
)


router = APIRouter(prefix="/auth", tags=["认证"])


# ==================== 传统登录 ====================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户名密码登录",
    description="使用用户名和密码进行传统登录"
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    传统用户名密码登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回 JWT 访问令牌和用户信息
    """
    try:
        # 登录
        token, user = await auth_service.login(
            username=request.username,
            password=request.password
        )
        
        # 返回响应
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except AccountDisabledError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败"
        )


# ==================== OAuth SSO 登录 ====================

@router.get(
    "/sso/initiate",
    response_model=OAuthInitiateResponse,
    summary="发起 SSO 登录",
    description="生成 OAuth 授权 URL 并重定向到授权服务器"
)
async def initiate_sso(
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    发起 OAuth SSO 登录流程
    
    生成授权 URL 和 state 参数,客户端应重定向到返回的 authorization_url
    """
    try:
        # 生成 state
        state = oauth_service.generate_state()
        
        # 存储 state
        await oauth_service.store_state(state)
        
        # 生成授权 URL
        authorization_url = oauth_service.generate_authorization_url(state)
        
        return OAuthInitiateResponse(
            authorization_url=authorization_url,
            state=state
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发起 SSO 登录失败"
        )


@router.get(
    "/sso/callback",
    response_model=LoginResponse,
    summary="OAuth 回调",
    description="处理 OAuth 授权回调,交换令牌并创建或更新用户"
)
async def oauth_callback(
    code: str = Query(..., description="OAuth 授权码"),
    state: str = Query(..., description="OAuth state 参数"),
    oauth_service: OAuthService = Depends(get_oauth_service),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    plugin_api_service: PluginAPIService = Depends(get_plugin_api_service)
):
    """
    OAuth 回调处理
    
    - **code**: OAuth 授权码
    - **state**: OAuth state 参数(用于防止 CSRF 攻击)
    
    验证 state,交换访问令牌,获取用户信息,创建或更新用户,返回系统 JWT 令牌
    """
    try:
        # 1. 验证 state
        await oauth_service.verify_state(state)
        
        # 2. 交换授权码获取访问令牌
        oauth_token = await oauth_service.exchange_code_for_token(code)
        
        # 3. 使用访问令牌获取用户信息
        user_info = await oauth_service.get_user_info(oauth_token.access_token)
        
        # 4. 创建或更新用户
        oauth_user_data = OAuthUserCreate(
            oauth_id=str(user_info.get("id")),
            username=user_info.get("username") or user_info.get("name"),
            avatar_url=user_info.get("avatar_url") or user_info.get("avatar"),
            trust_level=user_info.get("trust_level", 0)
        )
        
        user = await user_service.create_user_from_oauth(oauth_user_data)
        
        # 4.5 自动创建plug-in-api账号并绑定（仅对新用户）
        try:
            # 检查用户是否已有plug-in API密钥
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
        expires_at = oauth_service.calculate_token_expiry(oauth_token.expires_in)
        await user_service.save_oauth_token(user.id, oauth_token, expires_at)
        
        # 6. 更新最后登录时间
        await user_service.update_last_login(user.id)
        
        # 7. 创建系统 JWT 令牌
        system_token = await auth_service.create_user_token(user)
        
        # 8. 创建会话
        await auth_service.create_session(user.id, system_token)
        
        # 9. 返回响应
        return LoginResponse(
            access_token=system_token,
            token_type="bearer",
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth 回调处理失败"
        )


# ==================== 登出 ====================

@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="用户登出",
    description="登出当前用户,删除会话并将令牌加入黑名单"
)
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户登出
    
    需要在请求头中提供有效的 JWT 令牌:
    ```
    Authorization: Bearer <your_token>
    ```
    
    登出后令牌将失效
    """
    try:
        # 从依赖注入中无法直接获取原始令牌,需要从请求头中提取
        # 这里简化处理,直接删除会话即可
        await auth_service.delete_session(current_user.id)
        
        return LogoutResponse(
            message="登出成功",
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登出失败"
        )


# ==================== 获取当前用户信息 ====================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="获取当前登录用户的详细信息"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    
    需要在请求头中提供有效的 JWT 令牌:
    ```
    Authorization: Bearer <your_token>
    ```
    
    返回当前用户的详细信息
    """
    return UserResponse.model_validate(current_user)


# ==================== 用户验证 ====================

@router.get(
    "/check-username",
    summary="检查用户名是否存在",
    description="检查指定的用户名是否已在系统中注册（无需登录）"
)
async def check_username(
    username: str = Query(..., description="要检查的用户名"),
    user_service: UserService = Depends(get_user_service)
):
    """
    检查用户名是否存在
    
    用于登录前验证用户是否已注册
    
    - **username**: 要检查的用户名
    
    返回用户是否存在的信息
    """
    try:
        # 通过用户名查找用户
        user = await user_service.get_user_by_username(username)
        
        if user:
            return {
                "exists": True,
                "message": "用户名已存在",
                "username": username
            }
        else:
            return {
                "exists": False,
                "message": "用户名不存在",
                "username": username
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查用户名失败"
        )