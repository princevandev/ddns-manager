"""
设置相关 API 测试
"""
import pytest
from httpx import AsyncClient


class TestSettings:
    """设置测试"""
    
    @pytest.mark.asyncio
    async def test_get_settings(self, auth_client: AsyncClient):
        """测试获取设置"""
        response = await auth_client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "default_report_interval" in data
    
    @pytest.mark.asyncio
    async def test_update_settings(self, auth_client: AsyncClient):
        """测试更新设置"""
        response = await auth_client.post("/api/settings", data={
            "default_report_interval": 1800
        })
        assert response.status_code == 200
        data = response.json()
        assert data["default_report_interval"] == 1800
        
        # 验证设置已保存
        get_response = await auth_client.get("/api/settings")
        assert get_response.json()["default_report_interval"] == 1800
    
    @pytest.mark.asyncio
    async def test_cloudflare_test_without_token(self, auth_client: AsyncClient):
        """测试 Cloudflare 连接（未配置 token）"""
        response = await auth_client.post("/api/cloudflare/test")
        # 未配置 token 应该返回错误或警告
        assert response.status_code in [200, 400]