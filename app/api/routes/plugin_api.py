"""
Plug-in API相关的路由
提供用户管理plug-in API密钥和代理请求的端点
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, get_plugin_api_service
from app.models.user import User
from app.services.plugin_api_service import PluginAPIService
from app.schemas.plugin_api import (
    PluginAPIKeyCreate,
    PluginAPIKeyResponse,
    CreatePluginUserRequest,
    CreatePluginUserResponse,
    OAuthAuthorizeRequest,
    OAuthCallbackRequest,
    UpdateCookiePreferenceRequest,
    UpdateAccountStatusRequest,
    ChatCompletionRequest,
    PluginAPIResponse,
)


router = APIRouter(prefix="/plugin-api", tags=["Plug-in API"])


# ==================== 密钥管理 ====================
# 注意：用户注册时会自动创建plug-in-api账号，无需手动保存密钥

@router.get(
    "/key",
    response_model=PluginAPIKeyResponse,
    summary="获取plug-in API密钥信息",
    description="获取用户的plug-in API密钥信息（不返回实际密钥）"
)
async def get_api_key_info(
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取用户的plug-in API密钥信息"""
    try:
        key_record = await service.repo.get_by_user_id(current_user.id)
        if not key_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到API密钥"
            )
        return PluginAPIKeyResponse.model_validate(key_record)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取API密钥信息失败"
        )


# ==================== OAuth相关 ====================

@router.post(
    "/oauth/authorize",
    summary="获取OAuth授权URL",
    description="获取plug-in-api的OAuth授权URL"
)
async def get_oauth_authorize_url(
    request: OAuthAuthorizeRequest,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取OAuth授权URL"""
    try:
        result = await service.get_oauth_authorize_url(
            user_id=current_user.id,
            is_shared=request.is_shared
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取OAuth授权URL失败"
        )


@router.post(
    "/oauth/callback",
    summary="提交OAuth回调",
    description="手动提交OAuth回调URL"
)
async def submit_oauth_callback(
    request: OAuthCallbackRequest,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """提交OAuth回调"""
    try:
        result = await service.submit_oauth_callback(
            user_id=current_user.id,
            callback_url=request.callback_url
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交OAuth回调失败"
        )


# ==================== 账号管理 ====================

@router.get(
    "/accounts",
    summary="获取账号列表",
    description="获取用户在plug-in-api中的所有账号"
)
async def get_accounts(
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取账号列表"""
    try:
        result = await service.get_accounts(current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取账号列表失败"
        )


@router.get(
    "/accounts/{cookie_id}",
    summary="获取账号信息",
    description="获取指定账号的详细信息"
)
async def get_account(
    cookie_id: str,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取账号信息"""
    try:
        result = await service.get_account(current_user.id, cookie_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取账号信息失败"
        )


@router.put(
    "/accounts/{cookie_id}/status",
    summary="更新账号状态",
    description="启用或禁用指定账号"
)
async def update_account_status(
    cookie_id: str,
    request: UpdateAccountStatusRequest,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """更新账号状态"""
    try:
        result = await service.update_account_status(
            user_id=current_user.id,
            cookie_id=cookie_id,
            status=request.status
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新账号状态失败"
        )


@router.delete(
    "/accounts/{cookie_id}",
    summary="删除账号",
    description="删除指定账号"
)
async def delete_account(
    cookie_id: str,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """删除账号"""
    try:
        result = await service.delete_account(
            user_id=current_user.id,
            cookie_id=cookie_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除账号失败"
        )


@router.get(
    "/accounts/{cookie_id}/quotas",
    summary="获取账号配额",
    description="获取指定账号的配额信息"
)
async def get_account_quotas(
    cookie_id: str,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取账号配额信息"""
    try:
        result = await service.get_account_quotas(
            user_id=current_user.id,
            cookie_id=cookie_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取账号配额失败"
        )


@router.put(
    "/accounts/{cookie_id}/quotas/{model_name}/status",
    summary="更新模型配额状态",
    description="禁用或启用指定cookie的指定模型"
)
async def update_model_quota_status(
    cookie_id: str,
    model_name: str,
    request: UpdateAccountStatusRequest,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """更新模型配额状态"""
    try:
        result = await service.update_model_quota_status(
            user_id=current_user.id,
            cookie_id=cookie_id,
            model_name=model_name,
            status=request.status
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型配额状态失败"
        )


# ==================== 配额管理 ====================

@router.get(
    "/quotas/user",
    summary="获取用户配额池",
    description="获取用户的共享配额池信息"
)
async def get_user_quotas(
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取用户共享配额池"""
    try:
        result = await service.get_user_quotas(current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户配额池失败"
        )


@router.get(
    "/quotas/shared-pool",
    summary="获取共享池配额",
    description="获取共享池的总配额信息"
)
async def get_shared_pool_quotas(
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取共享池配额"""
    try:
        result = await service.get_shared_pool_quotas(current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取共享池配额失败"
        )


@router.get(
    "/quotas/consumption",
    summary="获取配额消耗记录",
    description="获取用户的配额消耗历史记录"
)
async def get_quota_consumption(
    limit: Optional[int] = Query(None, description="限制返回数量"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取配额消耗记录"""
    try:
        result = await service.get_quota_consumption(
            user_id=current_user.id,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配额消耗记录失败"
        )


# ==================== OpenAI兼容接口 ====================

@router.get(
    "/models",
    summary="获取模型列表",
    description="获取可用的AI模型列表"
)
async def get_models(
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取模型列表"""
    try:
        result = await service.get_models(current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败"
        )


@router.post(
    "/chat/completions",
    summary="聊天补全",
    description="使用plug-in-api进行聊天补全"
)
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """聊天补全"""
    try:
        # 如果是流式请求
        if request.stream:
            async def generate():
                async for chunk in service.proxy_stream_request(
                    user_id=current_user.id,
                    method="POST",
                    path="/v1/chat/completions",
                    json_data=request.model_dump()
                ):
                    yield chunk
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        else:
            # 非流式请求
            result = await service.proxy_request(
                user_id=current_user.id,
                method="POST",
                path="/v1/chat/completions",
                json_data=request.model_dump()
            )
            return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天补全失败"
        )


# ==================== 用户设置 ====================

@router.get(
    "/preference",
    summary="获取用户信息和Cookie优先级",
    description="获取用户在plug-in-api中的完整信息，包括Cookie优先级设置"
)
async def get_cookie_preference(
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """获取用户信息和Cookie优先级设置"""
    try:
        # 从plug-in-api获取用户信息
        result = await service.get_user_info(current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户信息失败"
        )


@router.put(
    "/preference",
    summary="更新Cookie优先级",
    description="更新用户的Cookie使用优先级设置"
)
async def update_cookie_preference(
    request: UpdateCookiePreferenceRequest,
    current_user: User = Depends(get_current_user),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """更新Cookie优先级"""
    try:
        # 获取plugin_user_id
        key_record = await service.repo.get_by_user_id(current_user.id)
        if not key_record or not key_record.plugin_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未找到plug-in用户ID"
            )
        
        result = await service.update_cookie_preference(
            user_id=current_user.id,
            plugin_user_id=key_record.plugin_user_id,
            prefer_shared=request.prefer_shared
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新Cookie优先级失败"
        )