import uuid
import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from core.security import decode_token


PUBLIC_PATHS = [
    "/health",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
]


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=401, headers={"WWW-Authenticate": "Bearer"})


class JWTAuthMiddleware:
    def __init__(self, app: ASGIApp, public_paths: set[str] | None = None) -> None:
        self.app = app
        self.public_paths = public_paths or PUBLIC_PATHS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if request.url.path in self.public_paths:
            await self.app(scope, receive, send)
            return

        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            await _unauthorized("Token ausente")(scope, receive, send)
            return

        try:
            payload = decode_token(token, expected_type="access")
            user_id = uuid.UUID(payload["sub"])
        except jwt.ExpiredSignatureError:
            await _unauthorized("Token expirado")(scope, receive, send)
            return
        except (jwt.InvalidTokenError, ValueError):
            await _unauthorized("Token inválido")(scope, receive, send)
            return

        scope.setdefault("state", {})["user_id"] = user_id
        await self.app(scope, receive, send)
