# from typing import List
# from fastapi import APIRouter, Depends, HTTPException, status, Response
# from sqlalchemy.orm import Session
# from app.db.session import get_db
# from app.schemas.schemas import Professional, ProfessionalCreate, ProfessionalUpdate
# from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest
# from app.services.crud import professional as crud_professional
# from app.services.auth import hash_password, verify_password, create_token_pair, refresh_access_token
# from app.api.dependencies import get_current_active_professional
#
# router = APIRouter()
#
# @router.post("/register", response_model=Professional, status_code=status.HTTP_201_CREATED)
# async def register_professional(
#     *,
#     db: Session = Depends(get_db),
#     professional_in: ProfessionalCreate
# ) -> Professional:
#     """
#     Register a new professional.
#     """
#     # Check if professional with this mobile number already exists
#     existing_professional = crud_professional.get_by_mobile(db, mobile_number=professional_in.mobile_number)
#     if existing_professional:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Professional with this mobile number already exists"
#         )
#
#     # Hash the password before storing
#     professional_in.password = hash_password(professional_in.password)
#
#     professional = crud_professional.create(db=db, obj_in=professional_in)
#
#     return professional
#
#
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
# @router.post("/login", response_model=TokenResponse)
# async def login_professional(
#     login_data: LoginRequest,
#     response: Response,
#     db: Session = Depends(get_db)
# ) -> TokenResponse:
#     """
#     Login professional using mobile number or email and return JWT tokens.
#     """
#     # Try to get professional by mobile number first
#     professional = crud_professional.get_by_mobile(db, mobile_number=login_data.identifier)
#
#     # If not found by mobile, try by email (if the model supports it)
#     # For now, we'll just support mobile number until email field is added to the model
#     if not professional:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials"
#         )
#
#     # Verify password
#     if not verify_password(login_data.password, professional.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials"
#         )
#
#     # Create token pair
#     tokens = create_token_pair(professional.id, professional.mobile_number)
#     response.set_cookie(
#         key="refresh_token",
#         value=tokens["refresh_token"],
#         httponly=True,
#         secure=True,  # only over HTTPS
#         samesite="strict"
#     )
#     return TokenResponse(**tokens)
#
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
