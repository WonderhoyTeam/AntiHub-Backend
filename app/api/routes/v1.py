"""
OpenAI兼容的API端点
支持API key或JWT token认证
用户通过我们的key/token调用，我们再用plug-in key调用plug-in-api
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps_flexible import get_user_flexible
from app.api.deps import get_plugin_api_service
from app.models.user import User
from app.services.plugin_api_service import PluginAPIService
from app.schemas.plugin_api import ChatCompletionRequest


router = APIRouter(prefix="/v1", tags=["OpenAI兼容API"])


@router.get(
    "/models",
    summary="获取模型列表",
    description="获取可用的AI模型列表（OpenAI兼容）"
)
async def list_models(
    current_user: User = Depends(get_user_flexible),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """
    获取模型列表
    支持API key或JWT token认证
    """
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
    description="使用plug-in-api进行聊天补全（OpenAI兼容）"
)
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_user_flexible),
    service: PluginAPIService = Depends(get_plugin_api_service)
):
    """
    聊天补全
    支持两种认证方式：
    1. API key认证 - 用于程序调用
    2. JWT token认证 - 用于playground网页聊天
    
    我们使用用户对应的plug-in key调用plug-in-api
    """
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