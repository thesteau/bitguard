from .resource import router as resource_router
from .validator import router as validator_router


def include_routers(app):
    app.include_router(resource_router)
    app.include_router(validator_router)
