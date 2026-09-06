from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.api import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CloudGuard - Enterprise cloud security scanner API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from app.aws.exceptions import (
    CloudGuardAWSError,
    InvalidRoleArnError,
    AWSAuthenticationError,
    AWSAccessDeniedError,
    AWSConnectionError,
    AWSRegionError
)

@app.exception_handler(InvalidRoleArnError)
async def invalid_role_arn_exception_handler(request: Request, exc: InvalidRoleArnError):
    return JSONResponse(status_code=400, content={"detail": "Invalid AWS IAM Role ARN"})

@app.exception_handler(AWSAccessDeniedError)
async def aws_access_denied_exception_handler(request: Request, exc: AWSAccessDeniedError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.exception_handler(AWSAuthenticationError)
async def aws_authentication_exception_handler(request: Request, exc: AWSAuthenticationError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})

@app.exception_handler(AWSRegionError)
async def aws_region_exception_handler(request: Request, exc: AWSRegionError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(AWSConnectionError)
async def aws_connection_exception_handler(request: Request, exc: AWSConnectionError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})

@app.exception_handler(CloudGuardAWSError)
async def cloudguard_aws_exception_handler(request: Request, exc: CloudGuardAWSError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )

# Mount API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "message": "CloudGuard backend is running"
    }

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting up {settings.APP_NAME} v{settings.APP_VERSION}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application")
