"""Main API router."""
from ninja import Router
from apps.orders.routers.router_a import orders_router
from apps.orders.routers.comments_router import comments_router
from apps.users.routers.auth import auth_router

router = Router()

# Include sub-routers
router.add_router("/orders", orders_router, tags=["Orders"])
router.add_router("/orders", comments_router, tags=["Order Comments"])
router.add_router("/auth", auth_router, tags=["Authentication"])


@router.get("/")
def api_root(request):
    """API root endpoint."""
    return {
        "message": "Welcome to Seafood Order Management API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/api/docs",
            "auth": "/api/auth",
            "orders": "/api/orders",
            "health": "/api/health",
        }
    }
