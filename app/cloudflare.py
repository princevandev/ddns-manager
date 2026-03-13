from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import httpx

API_BASE = "https://api.cloudflare.com/client/v4"


@dataclass
class CFRecordResult:
    record_id: str
    ip: str
    record_type: str


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _record_type(ip: str) -> str:
    return "AAAA" if ":" in ip else "A"


async def test_token(token: str) -> tuple[bool, str]:
    if not token:
        return False, "Cloudflare API token is not set"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_BASE}/user/tokens/verify", headers=_headers(token))
        if resp.status_code != 200:
            return False, f"Cloudflare verify failed: {resp.status_code}"
        data = resp.json()
        if not data.get("success"):
            return False, "Cloudflare verify failed"
        return True, "ok"


async def get_zone_id(token: str, domain_name: str) -> str | None:
    """根据域名自动查询 zone id"""
    # 从域名提取根域名（如 test.example.com -> example.com）
    parts = domain_name.split(".")
    if len(parts) >= 2:
        root_domain = ".".join(parts[-2:])
    else:
        root_domain = domain_name

    async with httpx.AsyncClient(timeout=10) as client:
        # 尝试精确匹配
        resp = await client.get(
            f"{API_BASE}/zones",
            headers=_headers(token),
            params={"name": root_domain},
        )
        data = resp.json()
        if data.get("success") and data.get("result"):
            return data["result"][0]["id"]

        # 尝试模糊匹配
        resp = await client.get(
            f"{API_BASE}/zones",
            headers=_headers(token),
            params={"name": domain_name},
        )
        data = resp.json()
        if data.get("success") and data.get("result"):
            return data["result"][0]["id"]

        return None


async def upsert_record(
    token: str, zone_id: str, domain_name: str, ip: str, record_id: Optional[str]
) -> CFRecordResult:
    if not token:
        raise RuntimeError("Cloudflare API token is not set")

    record_type = _record_type(ip)
    async with httpx.AsyncClient(timeout=15) as client:
        if record_id:
            payload = {"type": record_type, "name": domain_name, "content": ip, "ttl": 1, "proxied": False}
            resp = await client.put(
                f"{API_BASE}/zones/{zone_id}/dns_records/{record_id}",
                headers=_headers(token),
                json=payload,
            )
            data = resp.json()
            if not data.get("success"):
                raise RuntimeError(f"Cloudflare update failed: {data}")
            return CFRecordResult(record_id=record_id, ip=ip, record_type=record_type)

        # 查询现有记录
        query_params = {"name": domain_name, "type": record_type}
        resp = await client.get(
            f"{API_BASE}/zones/{zone_id}/dns_records",
            headers=_headers(token),
            params=query_params,
        )
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Cloudflare lookup failed: {data}")
        results = data.get("result") or []
        if results:
            existing = results[0]
            record_id = existing.get("id")
            # 如果 IP 相同，跳过更新
            if existing.get("content") == ip:
                return CFRecordResult(record_id=record_id, ip=ip, record_type=record_type)
            # 更新记录
            payload = {"type": record_type, "name": domain_name, "content": ip, "ttl": 1, "proxied": False}
            resp = await client.put(
                f"{API_BASE}/zones/{zone_id}/dns_records/{record_id}",
                headers=_headers(token),
                json=payload,
            )
            data = resp.json()
            if not data.get("success"):
                raise RuntimeError(f"Cloudflare update failed: {data}")
            return CFRecordResult(record_id=record_id, ip=ip, record_type=record_type)

        # 创建新记录
        payload = {"type": record_type, "name": domain_name, "content": ip, "ttl": 1, "proxied": False}
        resp = await client.post(
            f"{API_BASE}/zones/{zone_id}/dns_records",
            headers=_headers(token),
            json=payload,
        )
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Cloudflare create failed: {data}")
        record_id = data.get("result", {}).get("id")
        return CFRecordResult(record_id=record_id, ip=ip, record_type=record_type)