from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import register_database_lifecycle
from app.routers.auth import login_router as auth_login_router
from app.routers.auth import me_router as auth_me_router
from app.routers.auth import router as auth_router
from app.routers.auth import versioned_router as versioned_auth_router
from app.routers.assistant import router as assistant_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router

app = FastAPI(title="ECOM_OPPO API")
register_database_lifecycle(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "ecom-oppo-api"}


# Canonical route from approved brainstorm.
app.include_router(auth_router, prefix="/auth")
app.include_router(auth_login_router, prefix="/auth")
app.include_router(auth_me_router, prefix="/auth")
app.include_router(versioned_auth_router, prefix="/auth")
# Versioned alias to align with project routing convention.
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(versioned_auth_router, prefix="/api/v1/auth")
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(assistant_router)
