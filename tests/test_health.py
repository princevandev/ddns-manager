"""
健康检查测试
"""
import pytest
from httpx import AsyncClient


class TestHealth:
    """健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查接口"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self, client: AsyncClient):
        """测试健康检查不需要认证"""
        response = await client.get("/health")
        assert response.status_code == 200