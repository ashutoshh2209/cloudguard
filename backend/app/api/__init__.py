from fastapi import APIRouter
from app.api.routes import (
    health,
    aws_connection,
    discovery,
    scans,
    dashboard,
    resources,
    reports,
    ai,
    auth,
    workspaces,
    findings,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(aws_connection.router, prefix="/aws", tags=["aws"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
