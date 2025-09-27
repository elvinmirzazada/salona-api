from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.db.session import get_db
from app.schemas import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.responses import DataResponse
from app.schemas.schemas import ResponseMessage
from app.schemas.schemas import UserCreate
from app.services.auth import hash_password, verify_password, create_token_pair
from app.services.crud import user as crud_user

router = APIRouter()

@router.post("/auth/signup", response_model=ResponseMessage, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: Session = Depends(get_db),
    response: Response,
    user_in: UserCreate
) -> ResponseMessage:
    """
    Register a new user.
    """

    try:
        existing_customer = crud_user.get_by_email(
            db=db,
            email=user_in.email
        )
        if existing_customer:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return ResponseMessage(message="User with this email already exists for this business", status="error")

        user_in.password = hash_password(user_in.password)
        crud_user.create(db=db, obj_in=user_in)
        response.status_code = status.HTTP_201_CREATED
        return ResponseMessage(message="User created successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.post("/auth/login", response_model=DataResponse[TokenResponse])
async def user_login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Login professional using mobile number or email and return JWT tokens.
    """
    # Try to get professional by mobile number first
    user = crud_user.get_by_email(db, email=login_data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    company = crud_user.get_company_by_user(db, user.id)
    # Create token pair
    tokens = create_token_pair(user.id, user.email, actor="user", ver="1", company_id=str(company.company_id) if company else '')
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="strict"
    )
    return DataResponse.success_response(data = TokenResponse(**tokens))


@router.put("/auth/logout")
async def logout_user(response: Response):
    """
    Logout professional by clearing the refresh token cookie
    """
    try:
        response.delete_cookie(key="refresh_token")
        return ResponseMessage(message="Logged out successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.get("/me", response_model=DataResponse[User])
async def get_current_user(
    *,
    current_user: User = Depends(get_current_active_user)
) -> DataResponse:
    """
    Get current logged-in user.
    """
    return DataResponse.success_response(data=current_user)
