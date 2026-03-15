"""
认证相关 API 测试
"""
import pytest
from httpx import AsyncClient


class TestAuth:
    """认证测试"""
    
    @pytest.mark.asyncio
    async def test_login_page(self, client: AsyncClient):
        """测试登录页面"""
        response = await client.get("/login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """测试登录成功"""
        response = await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=False)
        assert response.status_code == 302  # FastAPI 使用 302 重定向
        assert "session" in response.cookies
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """测试登录失败 - 错误密码"""
        response = await client.post("/login", data={
            "username": "admin",
            "password": "wrongpassword"
        }, follow_redirects=False)
        # 登录失败返回登录页面 (200) 而不是 401
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_protected_route_without_auth(self, client: AsyncClient):
        """测试未登录访问受保护路由"""
        response = await client.get("/api/machines", follow_redirects=False)
        assert response.status_code == 302  # FastAPI 使用 302 重定向
    
    @pytest.mark.asyncio
    async def test_logout(self, auth_client: AsyncClient):
        """测试登出"""
        response = await auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302  # FastAPI 使用 302 重定向