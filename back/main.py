from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import models  # noqa: F401  (registra os modelos no metadata)
from core.config import settings
from core.exceptions import AppError
from core.middleware import JWTAuthMiddleware
from views import auth_view, familia_view, igreja_view, membro_view, usuario_view

# O schema do banco é gerenciado pelo Alembic: `alembic upgrade head`
app = FastAPI(title="Gerenciador de Igrejas")
app.add_middleware(JWTAuthMiddleware)
# Adicionado por último = camada mais externa: assim até os 401 do JWT levam os cabeçalhos CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


app.include_router(auth_view.router)
app.include_router(usuario_view.router)
app.include_router(igreja_view.router)
app.include_router(familia_view.router)
app.include_router(membro_view.router)
