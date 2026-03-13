import hashlib
from fastapi import Request, HTTPException
from starlette import status
from .config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_PASSWORD_HASH


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_credentials(username: str, password: str) -> bool:
    if username != ADMIN_USERNAME:
        return False
    if ADMIN_PASSWORD_HASH:
        return _hash_password(password) == ADMIN_PASSWORD_HASH
    return password == ADMIN_PASSWORD


def require_login(request: Request) -> None:
    if not request.session.get("user"):
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
