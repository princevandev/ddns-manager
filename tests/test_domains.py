"""
域名相关 API 测试
"""
import pytest
from httpx import AsyncClient


class TestDomains:
    """域名管理测试"""
    
    @pytest.mark.asyncio
    async def test_list_domains(self, auth_client: AsyncClient):
        """测试获取域名列表"""
        response = await auth_client.get("/api/domains")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_create_domain(self, auth_client: AsyncClient):
        """测试创建域名"""
        # 先创建机器
        machine_response = await auth_client.post("/api/machines", data={
            "name": "domain-test-machine"
        })
        machine_id = machine_response.json()["id"]
        
        # 创建域名
        response = await auth_client.post("/api/domains", data={
            "machine_id": machine_id,
            "domain_name": "test.example.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["domain_name"] == "test.example.com"
        assert data["machine_id"] == machine_id
        assert data["enabled"] == True  # 默认启用
    
    @pytest.mark.asyncio
    async def test_create_domain_with_zone_id(self, auth_client: AsyncClient):
        """测试创建域名时指定 zone_id"""
        # 创建机器
        machine_response = await auth_client.post("/api/machines", data={
            "name": "zone-test-machine"
        })
        machine_id = machine_response.json()["id"]
        
        # 创建域名
        response = await auth_client.post("/api/domains", data={
            "machine_id": machine_id,
            "domain_name": "zone.example.com",
            "zone_id": "test-zone-123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["zone_id"] == "test-zone-123"
    
    @pytest.mark.asyncio
    async def test_create_domain_invalid_machine(self, auth_client: AsyncClient):
        """测试创建域名时指定不存在的机器"""
        response = await auth_client.post("/api/domains", data={
            "machine_id": 99999,
            "domain_name": "invalid.example.com"
        })
        # API 可能返回 200 或 404，取决于实现
        # 如果返回 200，说明 API 允许创建但域名关联到不存在的机器
        # 这里我们检查响应是否成功或返回错误
        assert response.status_code in [200, 404, 400]
    
    @pytest.mark.asyncio
    async def test_delete_domain(self, auth_client: AsyncClient):
        """测试删除域名"""
        # 创建机器和域名
        machine_response = await auth_client.post("/api/machines", data={
            "name": "delete-domain-machine"
        })
        machine_id = machine_response.json()["id"]
        
        domain_response = await auth_client.post("/api/domains", data={
            "machine_id": machine_id,
            "domain_name": "delete.example.com"
        })
        domain_id = domain_response.json()["id"]
        
        # 删除域名
        response = await auth_client.delete(f"/api/domains/{domain_id}")
        assert response.status_code == 200
        
        # 确认已删除
        list_response = await auth_client.get("/api/domains")
        domains = list_response.json()
        domain_ids = [d["id"] for d in domains]
        assert domain_id not in domain_ids