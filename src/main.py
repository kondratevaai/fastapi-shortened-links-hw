from contextlib import asynccontextmanager
from fastapi import FastAPI

from database import init_db, close_db
from routers import links, users


#context manager for application startup and shutdown:
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


# init fastapi app for url shortening service and connect router: 
app = FastAPI(
    title="URL Shortening Service API",
    description="api for creating and managing shortened links with analytics",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(links.router)
app.include_router(users.router)


# the base api info: 
@app.get("/")
async def root():
    return {
        "message": "url shortening service api",
        "version": "1.0.0",
        "endpoints": {
            "create_short_link": "post /links/shorten",
            "redirect": "get /{short_code}",
            "get_link_stats": "get /links/{short_code}/stats",
            "delete_link": "delete /links/{short_code}",
            "update_link": "put /links/{short_code}",
            "search_by_url": "get /links/search"
        }
    }
