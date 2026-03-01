from .pages import router as pages_router
from .blog import router as blog_router
from .submit import router as submit_router


def include_routers(app):
    app.include_router(pages_router)
    app.include_router(blog_router)
    app.include_router(submit_router)
