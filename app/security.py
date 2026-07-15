"""可选的写接口 Token 校验。"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import API_TOKEN


def auth_required() -> bool:
    return bool(API_TOKEN)


async def require_api_token(x_api_token: str | None = Header(default=None, alias="X-API-Token")):
    # 没配置环境变量就直接放行，方便本地跑
    if not API_TOKEN:
        return
    if not x_api_token or x_api_token != API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="unauthorized: missing or invalid X-API-Token",
        )
