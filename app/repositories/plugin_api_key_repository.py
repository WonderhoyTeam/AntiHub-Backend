"""
Plug-in API密钥仓储层
处理plugin_api_keys表的数据库操作
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin_api_key import PluginAPIKey
from app.core.exceptions import UserNotFoundError


class PluginAPIKeyRepository:
    """Plug-in API密钥仓储类"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化仓储
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def get_by_user_id(self, user_id: int) -> Optional[PluginAPIKey]:
        """
        根据用户ID获取API密钥
        
        Args:
            user_id: 用户ID
            
        Returns:
            PluginAPIKey对象，不存在返回None
        """
        stmt = select(PluginAPIKey).where(PluginAPIKey.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, key_id: int) -> Optional[PluginAPIKey]:
        """
        根据ID获取API密钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            PluginAPIKey对象，不存在返回None
        """
        stmt = select(PluginAPIKey).where(PluginAPIKey.id == key_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(
        self,
        user_id: int,
        api_key: str,
        plugin_user_id: Optional[str] = None
    ) -> PluginAPIKey:
        """
        创建新的API密钥记录
        
        Args:
            user_id: 用户ID
            api_key: 加密后的API密钥
            plugin_user_id: plug-in-api系统中的用户ID
            
        Returns:
            创建的PluginAPIKey对象
        """
        plugin_api_key = PluginAPIKey(
            user_id=user_id,
            api_key=api_key,
            plugin_user_id=plugin_user_id,
            is_active=True
        )
        
        self.db.add(plugin_api_key)
        await self.db.commit()
        await self.db.refresh(plugin_api_key)
        
        return plugin_api_key
    
    async def update(
        self,
        user_id: int,
        **kwargs
    ) -> PluginAPIKey:
        """
        更新API密钥信息
        
        Args:
            user_id: 用户ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的PluginAPIKey对象
            
        Raises:
            UserNotFoundError: 密钥不存在
        """
        # 检查是否存在
        existing = await self.get_by_user_id(user_id)
        if not existing:
            raise UserNotFoundError(f"用户 {user_id} 的API密钥不存在")
        
        # 更新字段
        stmt = (
            update(PluginAPIKey)
            .where(PluginAPIKey.user_id == user_id)
            .values(**kwargs)
            .returning(PluginAPIKey)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.scalar_one()
    
    async def update_last_used(self, user_id: int) -> PluginAPIKey:
        """
        更新最后使用时间
        
        Args:
            user_id: 用户ID
            
        Returns:
            更新后的PluginAPIKey对象
        """
        return await self.update(user_id, last_used_at=datetime.utcnow())
    
    async def delete(self, user_id: int) -> bool:
        """
        删除API密钥
        
        Args:
            user_id: 用户ID
            
        Returns:
            删除成功返回True
        """
        stmt = delete(PluginAPIKey).where(PluginAPIKey.user_id == user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def exists(self, user_id: int) -> bool:
        """
        检查用户是否已有API密钥
        
        Args:
            user_id: 用户ID
            
        Returns:
            存在返回True
        """
        key = await self.get_by_user_id(user_id)
        return key is not None