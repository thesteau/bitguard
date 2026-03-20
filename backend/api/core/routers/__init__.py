from .validator import router as validator_router


def include_routers(app):
    app.include_router(validator_router)
