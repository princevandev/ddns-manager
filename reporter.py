#!/usr/bin/env python3
import os
import time
import requests
import subprocess
import re


def get_config() -> dict:
    """从环境变量读取配置"""
    manager_url = os.getenv("DDNS_MANAGER_URL")
    machine_token = os.getenv("DDNS_MACHINE_TOKEN")
    interface_name = os.getenv("DDNS_INTERFACE_NAME")
    report_interval = int(os.getenv("DDNS_REPORT_INTERVAL", "60"))

    if not manager_url or not machine_token or not interface_name:
        raise RuntimeError(
            "Required environment variables: DDNS_MANAGER_URL, DDNS_MACHINE_TOKEN, DDNS_INTERFACE_NAME"
        )

    return {
        "manager_url": manager_url,
        "machine_token": machine_token,
        "interface_name": interface_name,
        "report_interval": report_interval,
    }


def get_public_ipv4() -> str | None:
    """通过外部服务获取公网 IPv4 地址"""
    services = [
        "https://api.ipify.org",
        "https://api4.ipify.org",
        "https://ipv4.icanhazip.com",
        "https://v4.ident.me",
    ]
    for service in services:
        try:
            resp = requests.get(service, timeout=5)
            if resp.status_code == 200:
                ip = resp.text.strip()
                # 验证是有效的 IPv4
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                    return ip
        except Exception:
            continue
    return None


def get_ipv6_address(interface_name: str) -> str | None:
    """获取 IPv6 地址"""
    try:
        result = subprocess.run(
            ["ip", "-6", "addr", "show", "dev", interface_name],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    candidates = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("inet6"):
            continue
        match = re.search(r"inet6\s+([0-9a-fA-F:]+)/", line)
        if not match:
            continue
        ip = match.group(1)
        # 跳过链路本地地址
        if ip.lower().startswith("fe80"):
            continue
        # 优先选择全局地址
        if "scope global" in line:
            candidates.insert(0, ip)
        else:
            candidates.append(ip)
    
    return candidates[0] if candidates else None


def report(manager_url: str, token: str, ipv4: str | None, ipv6: str | None, interval: int) -> None:
    """上报 IP 地址"""
    url = manager_url.rstrip("/") + "/api/report"
    payload = {"token": token, "report_interval": interval}
    if ipv4:
        payload["ipv4"] = ipv4
    if ipv6:
        payload["ipv6"] = ipv6
    
    if not ipv4 and not ipv6:
        raise RuntimeError("No IP address to report")
    
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Report failed: {resp.status_code} {resp.text}")


def main() -> None:
    config = get_config()
    interval = config["report_interval"]
    backoff = 5

    print(f"DDNS Reporter started")
    print(f"Manager: {config['manager_url']}")
    print(f"Interface: {config['interface_name']}")
    print(f"Interval: {interval}s")

    while True:
        try:
            ipv4 = get_public_ipv4()  # 获取公网 IPv4
            ipv6 = get_ipv6_address(config["interface_name"])
            
            if not ipv4 and not ipv6:
                print("No IP address found, retrying...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
            
            report(config["manager_url"], config["machine_token"], ipv4, ipv6, interval)
            
            ips = []
            if ipv4:
                ips.append(f"IPv4: {ipv4}")
            if ipv6:
                ips.append(f"IPv6: {ipv6}")
            print(f"Reported: {', '.join(ips)}")
            
            backoff = 5
            time.sleep(interval)
        except Exception as exc:
            print(f"Report error: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)


if __name__ == "__main__":
    main()