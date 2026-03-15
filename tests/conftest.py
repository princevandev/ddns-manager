"""
DDNS Manager 测试配置
"""
import os
import sys
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 在导入 app 之前设置环境变量
os.environ["DDNS_ADMIN_USERNAME"] = "admin"
os.environ["DDNS_ADMIN_PASSWORD"] = "admin123"
os.environ["DDNS_DB_PATH"] = ":memory:"

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Base, Machine, Domain, IPHistory, Config
from app.db import SessionLocal


# 创建内存数据库引擎
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def get_test_db():
    """测试数据库依赖"""
    try:
        db = TestSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
async def client(db_session):
    """创建测试客户端"""
    from app.main import app
    from app.main import get_db
    
    # 覆盖数据库依赖
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(client):
    """已登录的测试客户端"""
    # 登录获取 cookie
    await client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    })
    yield client


@pytest.fixture
def sample_machine_data():
    """示例机器数据"""
    return {
        "name": "test-server",
        "ip_type": "ipv6"
    }


@pytest.fixture
def sample_domain_data():
    """示例域名数据"""
    return {
        "machine_id": 1,
        "domain_name": "test.example.com",
        "zone_id": "test-zone-id"
    }