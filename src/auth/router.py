from fastapi import APIRouter, status

from src.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from src.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_service = AuthService()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> dict:
    return await _service.register(payload.email, payload.password)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    token = await _service.login(payload.email, payload.password)
    return TokenResponse(access_token=token)
