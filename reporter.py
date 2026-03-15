#!/usr/bin/env python3
import os
import time
import logging
import requests
import subprocess
import re
import ipaddress


def setup_logging() -> None:
    """配置日志格式"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_config() -> dict:
    """从环境变量读取配置"""
    manager_url = os.getenv("DDNS_MANAGER_URL")
    machine_token = os.getenv("DDNS_MACHINE_TOKEN")
    interface_name = os.getenv("DDNS_INTERFACE_NAME", "auto")
    report_interval = int(os.getenv("DDNS_REPORT_INTERVAL", "60"))

    if not manager_url or not machine_token:
        raise RuntimeError(
            "Required environment variables: DDNS_MANAGER_URL, DDNS_MACHINE_TOKEN"
        )

    return {
        "manager_url": manager_url,
        "machine_token": machine_token,
        "interface_name": interface_name,
        "report_interval": report_interval,
    }


def is_private_ipv4(ip: str) -> bool:
    """判断 IPv4 是否为私有地址（局域网地址）"""
    try:
        addr = ipaddress.IPv4Address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ipaddress.AddressValueError:
        return True


def is_private_ipv6(ip: str) -> bool:
    """判断 IPv6 是否为私有地址"""
    try:
        addr = ipaddress.IPv6Address(ip)
        # 排除链路本地、唯一本地地址等
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ipaddress.AddressValueError:
        return True


def get_all_interfaces() -> list[str]:
    """获取所有网卡名称"""
    try:
        result = subprocess.run(
            ["ip", "link", "show"],
            capture_output=True,
            text=True,
        )
        interfaces = []
        for line in result.stdout.splitlines():
            match = re.match(r'^\d+:\s+([^:@]+)', line)
            if match:
                iface = match.group(1).strip()
                # 跳过 lo 和 docker/veth 等虚拟网卡
                if iface != 'lo' and not iface.startswith(('veth', 'br-', 'docker')):
                    interfaces.append(iface)
        return interfaces
    except Exception as e:
        logging.error(f"Failed to get interfaces: {e}")
        return []


def get_ipv4_address(interface_name: str) -> str | None:
    """从网卡获取 IPv4 地址"""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", interface_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
    except Exception as e:
        logging.debug(f"Failed to get IPv4 from {interface_name}: {e}")
        return None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("inet"):
            continue
        match = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
        if match:
            ip = match.group(1)
            # 只返回公网 IP
            if not is_private_ipv4(ip):
                logging.debug(f"Got public IPv4 from {interface_name}: {ip}")
                return ip
    return None


def get_ipv6_address(interface_name: str) -> str | None:
    """从网卡获取 IPv6 地址"""
    try:
        result = subprocess.run(
            ["ip", "-6", "addr", "show", "dev", interface_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
    except Exception as e:
        logging.debug(f"Failed to get IPv6 from {interface_name}: {e}")
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
        # 跳过私有地址
        if is_private_ipv6(ip):
            continue
        # 优先选择全局地址
        if "scope global" in line:
            candidates.insert(0, ip)
        else:
            candidates.append(ip)
    
    if candidates:
        logging.debug(f"Got public IPv6 from {interface_name}: {candidates[0]}")
    return candidates[0] if candidates else None


def check_interface_exists(interface_name: str) -> bool:
    """检查网卡是否存在"""
    try:
        result = subprocess.run(
            ["ip", "link", "show", "dev", interface_name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Failed to check interface: {e}")
        return False


def auto_detect_ips() -> tuple[str | None, str | None]:
    """自动检测所有网卡的公网 IP"""
    interfaces = get_all_interfaces()
    logging.debug(f"Found interfaces: {interfaces}")
    
    ipv4 = None
    ipv6 = None
    
    for iface in interfaces:
        if not ipv4:
            ipv4 = get_ipv4_address(iface)
            if ipv4:
                logging.debug(f"Found IPv4 on {iface}: {ipv4}")
        
        if not ipv6:
            ipv6 = get_ipv6_address(iface)
            if ipv6:
                logging.debug(f"Found IPv6 on {iface}: {ipv6}")
        
        # 都找到了就停止
        if ipv4 and ipv6:
            break
    
    return ipv4, ipv6


def report(manager_url: str, token: str, ipv4: str | None, ipv6: str | None, interval: int) -> None:
    """上报 IP 地址"""
    url = manager_url.rstrip("/") + "/api/report"
    payload = {"token": token, "report_interval": interval}
    if ipv4:
        payload["ipv4"] = ipv4
    if ipv6:
        payload["ipv6"] = ipv6
    
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Report failed: {resp.status_code} {resp.text}")


def main() -> None:
    setup_logging()
    
    config = get_config()
    interval = config["report_interval"]
    backoff = 5
    auto_mode = config["interface_name"].lower() == "auto"

    # 非 auto 模式检查网卡是否存在
    if not auto_mode and not check_interface_exists(config["interface_name"]):
        raise RuntimeError(f"Interface '{config['interface_name']}' does not exist")

    logging.info(f"DDNS Reporter started")
    logging.info(f"Manager: {config['manager_url']}")
    mode_str = "auto-detect" if auto_mode else f"interface {config['interface_name']}"
    logging.info(f"Mode: {mode_str}")
    logging.info(f"Interval: {interval}s")

    while True:
        try:
            if auto_mode:
                # 自动检测模式
                ipv4, ipv6 = auto_detect_ips()
            else:
                # 指定网卡模式
                ipv4 = get_ipv4_address(config["interface_name"])
                ipv6 = get_ipv6_address(config["interface_name"])
            
            # 上报（允许只上报其中一个，或都为空）
            report(config["manager_url"], config["machine_token"], ipv4, ipv6, interval)
            
            ips = []
            if ipv4:
                ips.append(f"IPv4: {ipv4}")
            if ipv6:
                ips.append(f"IPv6: {ipv6}")
            if ips:
                logging.info(f"Reported: {', '.join(ips)}")
            else:
                logging.warning("Reported: No public IP found")
            
            backoff = 5
            time.sleep(interval)
        except Exception as exc:
            logging.error(f"Report error: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)


if __name__ == "__main__":
    main()