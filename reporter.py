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
    report_interval = int(os.getenv("DDNS_REPORT_INTERVAL", "3600"))

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


def get_ipv6_address(interface_name: str) -> str:
    try:
        result = subprocess.run(
            ["ip", "-6", "addr", "show", "dev", interface_name],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to run ip command: {exc}")

    candidates = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("inet6"):
            continue
        match = re.search(r"inet6\s+([0-9a-fA-F:]+)/", line)
        if not match:
            continue
        ip = match.group(1)
        if ip.lower().startswith("fe80"):
            continue
        if "scope global" in line or "scope global dynamic" in line:
            candidates.append(ip)
    if not candidates:
        raise RuntimeError("No global IPv6 address found")
    return candidates[0]


def report(manager_url: str, token: str, ip: str) -> None:
    url = manager_url.rstrip("/") + "/api/report"
    resp = requests.post(url, json={"token": token, "ip": ip}, timeout=10)
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
            ip = get_ipv6_address(config["interface_name"])
            report(config["manager_url"], config["machine_token"], ip)
            print(f"Reported IP: {ip}")
            backoff = 5
            time.sleep(interval)
        except Exception as exc:
            print(f"Report error: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)


if __name__ == "__main__":
    main()