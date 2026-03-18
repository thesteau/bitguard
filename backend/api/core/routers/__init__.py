from .resource import router as resource_router


def include_routers(app):
    app.include_router(resource_router)
