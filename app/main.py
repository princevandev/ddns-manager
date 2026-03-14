from __future__ import annotations

from datetime import datetime
import secrets
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette import status
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal
from .models import Machine, Domain, IPHistory, Config
from .auth import verify_credentials, require_login
from .config import SESSION_SECRET
from .cloudflare import upsert_record, test_token, get_zone_id

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def utc_iso(dt: datetime) -> str:
    """返回带 Z 后缀的 UTC ISO 时间字符串"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_cf_token(db: Session) -> str | None:
    """从数据库获取 Cloudflare API token"""
    config = db.get(Config, "cloudflare_token")
    return config.value if config else None


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not verify_credentials(username, password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    request.session["user"] = username
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    require_login(request)
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/machines/{machine_id}", response_class=HTMLResponse)
def machine_detail(request: Request, machine_id: int):
    require_login(request)
    return templates.TemplateResponse("machine_detail.html", {"request": request, "machine_id": machine_id})


@app.get("/domains", response_class=HTMLResponse)
def domain_management(request: Request):
    require_login(request)
    return templates.TemplateResponse("domains.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    require_login(request)
    return templates.TemplateResponse("settings.html", {"request": request})


# API
@app.get("/api/machines")
def api_list_machines(request: Request, db: Session = Depends(get_db)):
    require_login(request)
    machines = db.query(Machine).all()
    payload = []
    for machine in machines:
        # 获取最后上报时间
        last_report = (
            db.query(IPHistory)
            .filter(IPHistory.machine_id == machine.id)
            .order_by(IPHistory.reported_at.desc())
            .first()
        )
        payload.append(
            {
                "id": machine.id,
                "name": machine.name,
                "token": machine.token,
                "report_interval": machine.report_interval,
                "ip_type": machine.ip_type,
                "created_at": utc_iso(machine.created_at),
                "last_ipv4": machine.last_ipv4,
                "last_ipv6": machine.last_ipv6,
                "last_reported": utc_iso(last_report.reported_at) if last_report else None,
                "domains": [
                    {
                        "id": d.id,
                        "domain_name": d.domain_name,
                        "zone_id": d.zone_id,
                        "record_id": d.record_id,
                        "last_ip": d.last_ip,
                        "last_updated": utc_iso(d.last_updated) if d.last_updated else None,
                        "enabled": d.enabled,
                    }
                    for d in machine.domains
                ],
            }
        )
    return payload


@app.get("/api/machines/{machine_id}")
def api_get_machine(request: Request, machine_id: int, db: Session = Depends(get_db)):
    require_login(request)
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return {
        "id": machine.id,
        "name": machine.name,
        "token": machine.token,
        "report_interval": machine.report_interval,
        "ip_type": machine.ip_type,
        "created_at": utc_iso(machine.created_at),
        "last_ipv4": machine.last_ipv4,
        "last_ipv6": machine.last_ipv6,
        "domains": [
            {
                "id": d.id,
                "domain_name": d.domain_name,
                "zone_id": d.zone_id,
                "record_id": d.record_id,
                "last_ip": d.last_ip,
                "last_updated": utc_iso(d.last_updated) if d.last_updated else None,
                "enabled": d.enabled,
            }
            for d in machine.domains
        ],
    }


@app.get("/api/machines/{machine_id}/history")
def api_machine_history(request: Request, machine_id: int, db: Session = Depends(get_db)):
    require_login(request)
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # 只返回与机器 ip_type 匹配的历史记录
    ip_type = machine.ip_type or "ipv4"
    history = (
        db.query(IPHistory)
        .filter(IPHistory.machine_id == machine_id, IPHistory.ip_type == ip_type)
        .order_by(IPHistory.reported_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "ip": item.ip,
            "ip_type": item.ip_type,
            "reported_at": utc_iso(item.reported_at),
        }
        for item in history
    ]


@app.post("/api/machines")
def api_create_machine(request: Request, db: Session = Depends(get_db), name: str = Form(...), ip_type: str = Form("ipv4")):
    require_login(request)
    if ip_type not in ("ipv4", "ipv6"):
        ip_type = "ipv4"
    token = secrets.token_urlsafe(32)
    machine = Machine(name=name, token=token, ip_type=ip_type)
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return {
        "id": machine.id,
        "name": machine.name,
        "token": machine.token,
        "ip_type": machine.ip_type,
        "created_at": utc_iso(machine.created_at),
    }


@app.delete("/api/machines/{machine_id}")
def api_delete_machine(request: Request, machine_id: int, db: Session = Depends(get_db)):
    require_login(request)
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    db.delete(machine)
    db.commit()
    return {"status": "ok"}


@app.patch("/api/machines/{machine_id}")
def api_update_machine(
    request: Request,
    machine_id: int,
    db: Session = Depends(get_db),
    report_interval: int | None = Form(None),
    ip_type: str | None = Form(None),
):
    """更新机器属性"""
    require_login(request)
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    if report_interval is not None:
        machine.report_interval = report_interval if report_interval > 0 else None
    
    if ip_type is not None and ip_type in ("ipv4", "ipv6"):
        machine.ip_type = ip_type
    
    db.commit()
    return {
        "id": machine.id,
        "name": machine.name,
        "report_interval": machine.report_interval,
        "ip_type": machine.ip_type,
    }


@app.get("/api/machines/{machine_id}/config")
def api_get_machine_config(machine_id: int, request: Request, db: Session = Depends(get_db)):
    """上报端获取配置（包括实际上报间隔）"""
    require_login(request)
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # 获取实际上报间隔：机器配置 > 全局默认
    if machine.report_interval:
        interval = machine.report_interval
    else:
        default_interval = db.get(Config, "default_report_interval")
        interval = int(default_interval.value) if default_interval else 3600
    
    return {
        "report_interval": interval,
    }


@app.get("/api/domains")
def api_list_domains(request: Request, db: Session = Depends(get_db)):
    require_login(request)
    domains = db.query(Domain).all()
    return [
        {
            "id": d.id,
            "machine_id": d.machine_id,
            "domain_name": d.domain_name,
            "zone_id": d.zone_id,
            "record_id": d.record_id,
            "last_ip": d.last_ip,
            "last_updated": utc_iso(d.last_updated) if d.last_updated else None,
            "enabled": d.enabled,
        }
        for d in domains
    ]


@app.post("/api/domains")
async def api_add_domain(
    request: Request,
    db: Session = Depends(get_db),
    machine_id: int = Form(...),
    domain_name: str = Form(...),
    zone_id: str = Form(""),
):
    require_login(request)
    
    cf_token = get_cf_token(db)
    
    # 如果没有提供 zone_id，自动查询
    if not zone_id and cf_token:
        zone_id = await get_zone_id(cf_token, domain_name)
        if not zone_id:
            raise HTTPException(status_code=400, detail="Could not find zone for this domain. Please provide zone_id manually.")
    
    domain = Domain(machine_id=machine_id, domain_name=domain_name, zone_id=zone_id)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return {
        "id": domain.id,
        "machine_id": domain.machine_id,
        "domain_name": domain.domain_name,
        "zone_id": domain.zone_id,
        "record_id": domain.record_id,
        "enabled": domain.enabled,
    }


@app.delete("/api/domains/{domain_id}")
def api_delete_domain(request: Request, domain_id: int, db: Session = Depends(get_db)):
    require_login(request)
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.delete(domain)
    db.commit()
    return {"status": "ok"}


@app.get("/api/settings")
def api_get_settings(request: Request, db: Session = Depends(get_db)):
    require_login(request)
    cf_token = db.get(Config, "cloudflare_token")
    default_interval = db.get(Config, "default_report_interval")
    return {
        "cloudflare_token": cf_token.value if cf_token else "",
        "default_report_interval": int(default_interval.value) if default_interval else 3600,
    }


@app.post("/api/settings")
def api_save_settings(
    request: Request,
    db: Session = Depends(get_db),
    cloudflare_token: str = Form(""),
    default_report_interval: int = Form(3600),
):
    require_login(request)
    
    # Cloudflare token
    existing = db.get(Config, "cloudflare_token")
    if existing:
        existing.value = cloudflare_token
    else:
        db.add(Config(key="cloudflare_token", value=cloudflare_token))
    
    # Default report interval
    interval_config = db.get(Config, "default_report_interval")
    if interval_config:
        interval_config.value = str(default_report_interval)
    else:
        db.add(Config(key="default_report_interval", value=str(default_report_interval)))
    
    db.commit()
    return {"status": "ok"}


@app.post("/api/cloudflare/test")
async def api_cf_test(request: Request, db: Session = Depends(get_db)):
    require_login(request)
    token = get_cf_token(db)
    ok, message = await test_token(token)
    if ok:
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail=message)


@app.post("/api/report")
async def api_report(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    token = data.get("token")
    ipv4 = data.get("ipv4")
    ipv6 = data.get("ipv6")
    ip = data.get("ip")  # 兼容旧版
    report_interval = data.get("report_interval")
    
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    
    # 兼容旧版：如果只有ip参数，当作ipv6处理
    if not ipv4 and not ipv6 and ip:
        ipv6 = ip
    
    if not ipv4 and not ipv6:
        raise HTTPException(status_code=400, detail="ipv4 or ipv6 required")

    machine = db.query(Machine).filter(Machine.token == token).first()
    if not machine:
        raise HTTPException(status_code=401, detail="invalid token")

    # 更新上报间隔
    if report_interval and isinstance(report_interval, int) and report_interval > 0:
        machine.report_interval = report_interval

    # 更新 IP 并记录历史
    if ipv4:
        machine.last_ipv4 = ipv4
        db.add(IPHistory(machine_id=machine.id, ip=ipv4, ip_type="ipv4"))
    if ipv6:
        machine.last_ipv6 = ipv6
        db.add(IPHistory(machine_id=machine.id, ip=ipv6, ip_type="ipv6"))
    
    db.commit()

    cf_token = get_cf_token(db)
    if not cf_token:
        return {"status": "ok", "updated": [], "warning": "Cloudflare token not configured"}

    # 自动同步（使用 IPv6 优先）
    target_ip = ipv6 or ipv4
    updated_domains = []
    for domain in machine.domains:
        if not domain.enabled:
            continue
        if domain.last_ip == target_ip:
            continue
        
        zone_id = domain.zone_id
        if not zone_id:
            zone_id = await get_zone_id(cf_token, domain.domain_name)
            if zone_id:
                domain.zone_id = zone_id
            else:
                continue
        
        try:
            result = await upsert_record(cf_token, zone_id, domain.domain_name, target_ip, domain.record_id)
            domain.record_id = result.record_id
            domain.last_ip = target_ip
            domain.last_updated = datetime.utcnow()
            updated_domains.append(domain.domain_name)
        except Exception as exc:
            return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})

    db.commit()
    return {"status": "ok", "updated": updated_domains}


@app.post("/api/sync/{machine_id}")
async def api_sync_machine(machine_id: int, request: Request, db: Session = Depends(get_db)):
    """手动触发同步：用机器配置的 IP 类型更新所有绑定的域名"""
    require_login(request)
    
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # 根据机器配置的 ip_type 获取目标 IP
    ip_type = machine.ip_type or "ipv4"
    if ip_type == "ipv4":
        ip = machine.last_ipv4
    else:
        ip = machine.last_ipv6
    
    if not ip:
        raise HTTPException(status_code=400, detail=f"No {ip_type} address reported")
    
    cf_token = get_cf_token(db)
    if not cf_token:
        raise HTTPException(status_code=400, detail="Cloudflare token not configured")
    
    updated_domains = []
    errors = []
    for domain in machine.domains:
        if not domain.enabled:
            continue
        
        # 自动获取 zone_id
        zone_id = domain.zone_id
        if not zone_id:
            zone_id = await get_zone_id(cf_token, domain.domain_name)
            if zone_id:
                domain.zone_id = zone_id
            else:
                errors.append(f"{domain.domain_name}: could not find zone")
                continue
        
        try:
            result = await upsert_record(cf_token, zone_id, domain.domain_name, ip, domain.record_id)
            domain.record_id = result.record_id
            domain.last_ip = ip
            domain.last_updated = datetime.utcnow()
            updated_domains.append(domain.domain_name)
        except Exception as exc:
            errors.append(f"{domain.domain_name}: {str(exc)}")
    
    db.commit()
    
    if errors:
        return {"status": "partial", "updated": updated_domains, "errors": errors}
    return {"status": "ok", "updated": updated_domains, "ip": ip}


@app.get("/health")
def health():
    return {"status": "ok"}