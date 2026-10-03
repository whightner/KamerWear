from fastapi import APIRouter

from app.api.v1.endpoints import (
    addresses,
    admin_catalog,
    admin_returns,
    admin_store,
    admin_support,
    admin_visual_search,
    auth,
    cart,
    categories,
    checkout,
    fit,
    health,
    orders,
    products,
    returns,
    support,
    users,
    visual_search,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(addresses.router)
api_router.include_router(cart.router)
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(admin_store.router)
api_router.include_router(admin_catalog.router)
api_router.include_router(visual_search.router)
api_router.include_router(admin_visual_search.router)
api_router.include_router(fit.router)
api_router.include_router(returns.router)
api_router.include_router(admin_returns.router)
api_router.include_router(support.router)
api_router.include_router(admin_support.router)
