from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field

from services.storage import auth as storage_auth
from services.api.auth import create_access_token, get_current_username

router = APIRouter()


class SignupRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/signup", summary="Create a new user")
def signup(payload: SignupRequest):
    ok = storage_auth.create_user(payload.username, payload.password)
    if not ok:
        raise HTTPException(status_code=400, detail="User already exists")
    return {"status": "created", "username": payload.username}


@router.post("/login", response_model=TokenResponse, summary="Login and obtain access token")
def login(payload: LoginRequest, response: Response):
    if not storage_auth.verify_user(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token({"sub": payload.username})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60,
    )
    return {"access_token": access_token}


@router.post("/logout", summary="Clear login session")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "logged_out"}


@router.get("/profile", summary="Return current user", tags=["auth"])
def profile(username: str = Depends(get_current_username)):
    return {"username": username}
