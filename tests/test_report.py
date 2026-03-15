"""
上报 API 测试
"""
import pytest
from httpx import AsyncClient


class TestReport:
    """上报测试"""
    
    @pytest.mark.asyncio
    async def test_report_ipv6(self, client: AsyncClient):
        """测试上报 IPv6 地址"""
        # 先通过 API 创建机器（需要登录）
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        machine_response = await client.post("/api/machines", data={
            "name": "report-test-machine"
        })
        token = machine_response.json()["token"]
        
        # 上报 IP
        response = await client.post("/api/report", json={
            "token": token,
            "ipv6": "2001:db8::1"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        
        # 验证 IP 已记录
        machine_id = machine_response.json()["id"]
        machine = (await client.get(f"/api/machines/{machine_id}")).json()
        assert machine["last_ipv6"] == "2001:db8::1"
    
    @pytest.mark.asyncio
    async def test_report_ipv4(self, client: AsyncClient):
        """测试上报 IPv4 地址"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        machine_response = await client.post("/api/machines", data={
            "name": "ipv4-report-machine"
        })
        token = machine_response.json()["token"]
        
        response = await client.post("/api/report", json={
            "token": token,
            "ipv4": "192.168.1.100"
        })
        assert response.status_code == 200
        
        machine_id = machine_response.json()["id"]
        machine = (await client.get(f"/api/machines/{machine_id}")).json()
        assert machine["last_ipv4"] == "192.168.1.100"
    
    @pytest.mark.asyncio
    async def test_report_both_ipv4_and_ipv6(self, client: AsyncClient):
        """测试同时上报 IPv4 和 IPv6"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        machine_response = await client.post("/api/machines", data={
            "name": "dual-stack-machine"
        })
        token = machine_response.json()["token"]
        
        response = await client.post("/api/report", json={
            "token": token,
            "ipv4": "192.168.1.100",
            "ipv6": "2001:db8::1"
        })
        assert response.status_code == 200
        
        machine_id = machine_response.json()["id"]
        machine = (await client.get(f"/api/machines/{machine_id}")).json()
        assert machine["last_ipv4"] == "192.168.1.100"
        assert machine["last_ipv6"] == "2001:db8::1"
    
    @pytest.mark.asyncio
    async def test_report_without_token(self, client: AsyncClient):
        """测试上报时缺少 token"""
        response = await client.post("/api/report", json={
            "ipv6": "2001:db8::1"
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_report_with_invalid_token(self, client: AsyncClient):
        """测试上报时使用无效 token"""
        response = await client.post("/api/report", json={
            "token": "invalid-token",
            "ipv6": "2001:db8::1"
        })
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_report_without_ip(self, client: AsyncClient):
        """测试上报时缺少 IP"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        machine_response = await client.post("/api/machines", data={
            "name": "no-ip-machine"
        })
        token = machine_response.json()["token"]
        
        response = await client.post("/api/report", json={
            "token": token
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_report_with_interval(self, client: AsyncClient):
        """测试上报时携带上报间隔"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        machine_response = await client.post("/api/machines", data={
            "name": "interval-machine"
        })
        token = machine_response.json()["token"]
        
        response = await client.post("/api/report", json={
            "token": token,
            "ipv6": "2001:db8::1",
            "report_interval": 120
        })
        assert response.status_code == 200
        
        machine_id = machine_response.json()["id"]
        machine = (await client.get(f"/api/machines/{machine_id}")).json()
        assert machine["report_interval"] == 120
    
    @pytest.mark.asyncio
    async def test_report_records_ip_history(self, client: AsyncClient):
        """测试上报会记录 IP 历史"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        machine_response = await client.post("/api/machines", data={
            "name": "history-record-machine",
            "ip_type": "ipv6"
        })
        token = machine_response.json()["token"]
        machine_id = machine_response.json()["id"]
        
        # 上报多次 IPv6
        await client.post("/api/report", json={
            "token": token,
            "ipv6": "2001:db8::1"
        })
        await client.post("/api/report", json={
            "token": token,
            "ipv6": "2001:db8::2"
        })
        
        # 检查历史记录（只返回 IPv6）
        history = (await client.get(f"/api/machines/{machine_id}/history")).json()
        assert len(history) >= 2
        # 所有记录都应该是 ipv6 类型
        for item in history:
            assert item["ip_type"] == "ipv6"

    @pytest.mark.asyncio
    async def test_report_history_filters_by_ip_type(self, client: AsyncClient):
        """测试 IP 历史根据机器 ip_type 过滤"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        
        # 创建 IPv4 机器
        ipv4_machine = await client.post("/api/machines", data={
            "name": "ipv4-history-machine",
            "ip_type": "ipv4"
        })
        ipv4_token = ipv4_machine.json()["token"]
        ipv4_machine_id = ipv4_machine.json()["id"]
        
        # 创建 IPv6 机器
        ipv6_machine = await client.post("/api/machines", data={
            "name": "ipv6-history-machine",
            "ip_type": "ipv6"
        })
        ipv6_token = ipv6_machine.json()["token"]
        ipv6_machine_id = ipv6_machine.json()["id"]
        
        # IPv4 机器上报
        await client.post("/api/report", json={
            "token": ipv4_token,
            "ipv4": "192.168.1.1"
        })
        
        # IPv6 机器上报
        await client.post("/api/report", json={
            "token": ipv6_token,
            "ipv6": "2001:db8::1"
        })
        
        # 检查 IPv4 机器的历史只有 IPv4 记录
        ipv4_history = (await client.get(f"/api/machines/{ipv4_machine_id}/history")).json()
        for item in ipv4_history:
            assert item["ip_type"] == "ipv4"
        
        # 检查 IPv6 机器的历史只有 IPv6 记录
        ipv6_history = (await client.get(f"/api/machines/{ipv6_machine_id}/history")).json()
        for item in ipv6_history:
            assert item["ip_type"] == "ipv6"

    @pytest.mark.asyncio
    async def test_report_both_ips_filters_by_machine_type(self, client: AsyncClient):
        """测试同时上报 IPv4 和 IPv6 时，历史根据机器类型过滤"""
        await client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        
        # 创建 IPv6 机器
        machine_response = await client.post("/api/machines", data={
            "name": "dual-filter-machine",
            "ip_type": "ipv6"
        })
        token = machine_response.json()["token"]
        machine_id = machine_response.json()["id"]
        
        # 同时上报 IPv4 和 IPv6
        await client.post("/api/report", json={
            "token": token,
            "ipv4": "192.168.1.100",
            "ipv6": "2001:db8::1"
        })
        
        # 历史应该只包含 IPv6 记录（因为机器类型是 ipv6）
        history = (await client.get(f"/api/machines/{machine_id}/history")).json()
        for item in history:
            assert item["ip_type"] == "ipv6"