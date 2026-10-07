from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import models
from core.database import Base, engine
from core.exceptions import AppError
from core.middleware import JWTAuthMiddleware
from views import auth_view, user_view


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Gerenciador de Igrejas", lifespan=lifespan)
app.add_middleware(JWTAuthMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)


app.include_router(auth_view.router)
app.include_router(user_view.router)
