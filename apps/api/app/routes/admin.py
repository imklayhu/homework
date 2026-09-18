import json
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlmodel import Session, select, func
from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.models import AnalyticsEvent
from app.services.analytics import build_metrics
from app.services.admin import make_session, verify_password, verify_session

router = APIRouter(prefix="/api/admin", tags=["admin"])
COOKIE = "framewise_admin"

class LoginBody(BaseModel):
    username: str
    password: str

def require_admin(request: Request, settings: Settings = Depends(get_settings)) -> None:
    if not verify_session(request.cookies.get(COOKIE), settings.admin_session_secret.get_secret_value()):
        raise AppError("ADMIN_UNAUTHORIZED", "请先登录管理员账号。", 401)

@router.post("/login")
def login(body: LoginBody, response: Response, settings: Settings = Depends(get_settings)):
    configured = settings.admin_password.get_secret_value() if settings.admin_password else ""
    if body.username != settings.admin_username or not verify_password(body.password, configured):
        raise AppError("ADMIN_LOGIN_FAILED", "账号或密码错误。", 401)
    response.set_cookie(COOKIE, make_session(body.username, settings.admin_session_secret.get_secret_value()), httponly=True, samesite="lax", max_age=43200)
    return {"authenticated": True}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"authenticated": False}

@router.post("/events", status_code=204)
def event(request: Request, name: str, properties: dict | None = None, session: Session = Depends(get_session)):
    session.add(AnalyticsEvent(name=name, properties_json=json.dumps(properties or {}, ensure_ascii=False), session_id=request.headers.get("x-session-id")))
    session.commit()

@router.get("/metrics")
def metrics(days: int = 30, _: None = Depends(require_admin), session: Session = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=30)
    rows = session.exec(select(AnalyticsEvent.name, func.count(AnalyticsEvent.id)).where(AnalyticsEvent.created_at >= since).group_by(AnalyticsEvent.name)).all()
    counts = {name: count for name, count in rows}
    result = build_metrics(session, days)
    result["window_days"] = max(1, min(days, 90))
    return result
