from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.middleware import HardeningMiddleware
from app.api import auth, profile, health, schemes, admin, discovery, user_features, notifications

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated Government Scheme Recommendation Agent API",
    version="1.0.0",
    debug=settings.DEBUG
)

# Hardening Middleware (Security Headers, Rate Limiting, JSON Logging)
app.add_middleware(HardeningMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handler for Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        loc = " -> ".join([str(x) for x in error.get("loc", [])])
        errors.append({"location": loc, "message": error.get("msg")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": errors}
    )

# Include Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(schemes.router)
app.include_router(admin.router)
app.include_router(discovery.router)
app.include_router(user_features.router)
app.include_router(notifications.router)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
