"""
数据库会话管理
实现异步数据库连接和会话管理
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings


# 全局引擎实例
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    获取数据库引擎实例
    使用单例模式确保只创建一个引擎
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        
        # 配置连接池参数
        pool_config = {
            "pool_size": 20,  # 连接池大小
            "max_overflow": 10,  # 最大溢出连接数
            "pool_timeout": 30,  # 连接超时时间（秒）
            "pool_recycle": 3600,  # 连接回收时间（秒）
            "pool_pre_ping": True,  # 连接前检查连接是否有效
        }
        
        # 测试环境使用 NullPool
        if settings.app_env == "test":
            pool_config = {"poolclass": NullPool}
        else:
            pool_config["poolclass"] = QueuePool
        
        _engine = create_async_engine(
            settings.database_url,
            echo=False,  # 关闭 SQL 日志
            **pool_config
        )
    
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    获取会话工厂
    """
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # 提交后不过期对象
            autocommit=False,
            autoflush=False,
        )
    
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    用于依赖注入
    
    使用示例:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库连接
    应在应用启动时调用
    """
    # 初始化引擎和会话工厂
    get_engine()
    get_session_maker()


async def close_db() -> None:
    """
    关闭数据库连接
    应在应用关闭时调用
    """
    global _engine, _async_session_maker
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
