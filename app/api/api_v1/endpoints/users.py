from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import User, UserCreate, UserUpdate
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest
from app.services.crud import user as crud_user
from app.schemas.schemas import ResponseMessage
from app.services.auth import hash_password, verify_password, create_token_pair, refresh_access_token
from app.api.dependencies import get_current_active_professional

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


# @router.get("/me", response_model=Professional)
# async def get_current_professional_info(
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Get current professional's information from JWT token.
#     """
#     return current_professional
#
#
# @router.get("/{professional_id}", response_model=Professional)
# async def get_professional(
#     professional_id: int,
#     db: Session = Depends(get_db),
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Get professional by ID. Requires authentication.
#     """
#     # Check if the requesting professional is trying to access their own data or has permission
#     if current_professional.id != professional_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this professional's information"
#         )
#
#     professional = crud_professional.get(db=db, id=professional_id)
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Professional not found"
#         )
#     return professional
#
#
# @router.put("/{professional_id}", response_model=Professional)
# async def update_professional(
#     *,
#     db: Session = Depends(get_db),
#     professional_id: int,
#     professional_in: ProfessionalUpdate,
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Update professional. Requires authentication.
#     """
#     # Check if the requesting professional is trying to update their own data
#     if current_professional.id != professional_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to update this professional's information"
#         )
#
#     professional = crud_professional.get(db=db, id=professional_id)
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Professional not found"
#         )
#
#     professional = crud_professional.update(db=db, db_obj=professional, obj_in=professional_in)
#     return professional
#
#
# @router.get("/mobile/{mobile_number}", response_model=Professional)
# async def get_professional_by_mobile(
#     mobile_number: str,
#     db: Session = Depends(get_db),
#     current_professional: Professional = Depends(get_current_active_professional)
# ) -> Professional:
#     """
#     Get professional by mobile number. Requires authentication.
#     """
#     professional = crud_professional.get_by_mobile(db=db, mobile_number=mobile_number)
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Professional not found"
#         )
#
#     # Check if the requesting professional is trying to access their own data
#     if current_professional.id != professional.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this professional's information"
#         )
#
#     return professional
#
#
@router.post("/auth/login", response_model=TokenResponse)
async def user_login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> TokenResponse:
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

    # Create token pair
    tokens = create_token_pair(user.id, user.email, actor="user", ver="1")
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="strict"
    )
    return TokenResponse(**tokens)

#
# @router.post("/refresh-token", response_model=TokenResponse)
# async def refresh_token(
#     refresh_data: RefreshTokenRequest
# ) -> TokenResponse:
#     """
#     Refresh access token using refresh token.
#     """
#     tokens = refresh_access_token(refresh_data.refresh_token)
#     if not tokens:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid refresh token"
#         )
#
#     return TokenResponse(**tokens)
#
#
# @router.post("/logout")
# async def logout_professional(response: Response):
#     """
#     Logout professional by clearing the refresh token cookie
#     """
#     response.delete_cookie(
#         key="refresh_token",
#         httponly=True,
#         secure=True,
#         samesite="strict"
#     )
#     return {"message": "Successfully logged out"}
