from fastapi import FastAPI

from app.core.config import get_settings
from app.routers.address_routes import router as address_router
from app.routers.user_routes import router as user_router

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Independent ShopEase User Management Microservice. "
        "Authenticates requests with JWTs issued by the ShopEase Authentication Service."
    ),
)

app.include_router(user_router)
app.include_router(address_router)


@app.get("/health", tags=["Health"], summary="Service health check")
def health_check():
    return {"status": "ok", "service": settings.app_name}
