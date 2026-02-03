from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Request, File, UploadFile
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import logging
from fastapi.responses import RedirectResponse, JSONResponse

from app.api.dependencies import get_current_active_user, get_current_company_id
from app.db.session import get_db
from app.models import AvailabilityType
from app.models.models import Users
from app.schemas import User
from app.schemas.auth import (
    LoginRequest, TokenResponse, VerificationRequest,
    GoogleAuthorizationResponse, GoogleCallbackRequest, GoogleOAuthResponse
)
from app.schemas.responses import DataResponse
from app.schemas.schemas import ResponseMessage, TimeOffCreate, TimeOff, TimeOffUpdate, UserUpdate
from app.schemas.schemas import UserCreate
from app.services.auth import hash_password, verify_password, create_token_pair, verify_token
from app.services.crud import user as crud_user
from app.services.crud import user_time_off as crud_time_off
from app.services.crud import company as crud_company
from app.services.email_service import email_service, create_verification_token
from app.services.google_oauth import GoogleOAuthService
from app.models.enums import VerificationType, VerificationStatus


logger = logging.getLogger()
router = APIRouter()


# Helper function to create a new user (reused by both signup and Google OAuth)
async def _create_new_user(
    db: Session,
    user_in: UserCreate,
    send_verification_email: bool = True
) -> tuple[Users, str]:
    """
    Internal helper to create a new user.

    Returns:
        Tuple of (new_user, message)
    """
    user_in.email = user_in.email.lower()

    # Check if user already exists
    existing_user = crud_user.get_by_email(db=db, email=user_in.email)
    if existing_user:
        raise ValueError("User with this email already exists")

    # Hash password
    user_in.password = hash_password(user_in.password)
    new_user = crud_user.create(db=db, obj_in=user_in)

    # Create verification token
    verification_record = create_verification_token(
        db=db,
        entity_id=new_user.id,
        verification_type=VerificationType.EMAIL,
        entity_type="user",
        expires_in_hours=24
    )

    if send_verification_email:
        # Send verification email
        try:
            user_name = f"{new_user.first_name} {new_user.last_name}"
            email_sent = email_service.send_verification_email(
                to_email=new_user.email,
                verification_token=verification_record.token,
                user_name=user_name
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error sending verification email: {str(e)}")
            email_sent = False

        if not email_sent:
            raise Exception(f"Warning: Failed to send verification email to {new_user.email}")

        message = "User created successfully. Please check your email to verify your account."
    else:
        # Auto-verify email for OAuth users
        crud_user.verify_token(db=db, db_obj=verification_record)
        message = "User created successfully via Google OAuth"

    return new_user, message


@router.post("/auth/signup", response_model=ResponseMessage, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: Session = Depends(get_db),
    response: Response,
    user_in: UserCreate
) -> ResponseMessage:
    """
    Register a new user and send email verification.
    """

    try:
        new_user, message = await _create_new_user(db, user_in, send_verification_email=True)
        response.status_code = status.HTTP_201_CREATED
        return ResponseMessage(message=message, status="success")
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ResponseMessage(message=str(e), status="error")
    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.post("/auth/verify-email", response_model=DataResponse)
async def verify_email(
    *,
    db: Session = Depends(get_db),
    verification_in: VerificationRequest,
    response: Response
) -> DataResponse:
    """
    Verify user email with token.
    """
    try:
        token = crud_user.get_verification_token(
            db=db,
            token=verification_in.token,
            type=VerificationType.EMAIL
        )

        if not token:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Verification token not found"
            )

        if token.status != VerificationStatus.PENDING or token.expires_at < datetime.now():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Token has expired or is invalid"
            )

        result = crud_user.verify_token(db=db, db_obj=token)
        if result:
            return DataResponse.success_response(
                message="Email verified successfully"
            )

        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message="Email verification failed",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Verification process failed: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
        max_age=tokens['rt_expires_in'],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="none"
    )
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        max_age=tokens['at_expires_in'],
        httponly=True,
        secure=True,  # only over HTTPS
        samesite="none"
    )

    return DataResponse.success_response(data = TokenResponse(**tokens))


@router.put("/auth/logout")
async def logout_user(response: Response):
    """
    Logout professional by clearing the refresh token cookie
    """
    from app.core.config import settings
    try:
        # Determine cookie domain - must match the domain used when setting cookies
        cookie_domain = ".salona.me" if "salona.me" in settings.API_URL else None
        is_production = "https://" in settings.API_URL

        response.set_cookie(
            key="refresh_token",
            value='',
            max_age=0,
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="none"
        )
        response.set_cookie(
            key="access_token",
            value='',
            max_age=0,
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="none"
        )

        return ResponseMessage(message="Logged out successfully", status="success")
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ResponseMessage(message=f"Internal server error: {str(e)}", status="error")


@router.get("/me", response_model=DataResponse)
async def get_current_user(
    *,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_active_user)
) -> DataResponse:
    """
    Get current logged-in user. Returns CompanyUser if user belongs to a company, otherwise returns User.
    """
    # Check if user belongs to a company
    if current_user.company_id:
        try:
            # Get company user details
            company_user = crud_company.get_company_user(
                db=db, 
                user_id=str(current_user.id), 
                company_id=str(current_user.company_id)
            )
            if company_user:
                return DataResponse.success_response(data=company_user)
        except Exception as e:
            print(f"Error fetching company user: {str(e)}")
            # Fall through to return basic user if company user fetch fails
    
    # Return basic user if no company association - convert SQLAlchemy model to Pydantic schema
    user_schema = User.model_validate(current_user)
    return DataResponse.success_response(data=user_schema)


@router.put("/me", response_model=DataResponse[User], status_code=status.HTTP_200_OK)
async def update_current_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    response: Response,
    current_user: Users = Depends(get_current_active_user)
) -> DataResponse:
    """
    Update current user's information (first_name, last_name, email, phone).
    """
    try:
        # Update the user
        updated_user = crud_user.update(
            db=db,
            db_obj=current_user,
            obj_in=user_in
        )
        
        # Convert to Pydantic schema for response
        user_schema = User.model_validate(updated_user)
        
        return DataResponse.success_response(
            message="User information updated successfully",
            data=user_schema,
            status_code=status.HTTP_200_OK
        )
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to update user information: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/time-offs", response_model=DataResponse[TimeOff], status_code=status.HTTP_201_CREATED)
async def create_time_off(
    *,
    db: Session = Depends(get_db),
    time_off_in: TimeOffCreate,
    response: Response,
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a new time off period for the current user.
    """
    try:
        # Check for overlapping time offs
        has_overlap = crud_time_off.check_overlapping_time_offs(
            db=db,
            user_id=time_off_in.user_id,
            start_date=time_off_in.start_date,
            end_date=time_off_in.end_date
        )

        if has_overlap:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                message="The time off period overlaps with existing ones",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Create the time off
        time_off = crud_time_off.create(
            db=db,
            obj_in=time_off_in,
            company_id=company_id
        )

        return DataResponse.success_response(
            message="Time off created successfully",
            data=time_off,
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to create time off: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/time-offs", response_model=DataResponse[List[TimeOff]], status_code=status.HTTP_200_OK)
async def get_all_user_time_offs(
    *,
    db: Session = Depends(get_db),
    start_date: datetime = Query(datetime.today(), description="Filter time offs that end after this date"),
    availability_type: AvailabilityType = Query(AvailabilityType.WEEKLY, description="Type of availability check: daily, weekly, or monthly"),
    response: Response,
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all time offs for the current user with optional date filtering.
    """
    try:
        end_date = start_date + timedelta(
                days=1 if availability_type == AvailabilityType.DAILY else
                     7 if availability_type == AvailabilityType.WEEKLY else 31
            )
        time_offs = crud_time_off.get_user_time_offs(
            db=db,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date
        )

        return DataResponse.success_response(
            data=time_offs,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to retrieve time offs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/time-offs/{time_off_id}", response_model=DataResponse[TimeOff], status_code=status.HTTP_200_OK)
async def update_time_off(
    *,
    time_off_id: str,
    db: Session = Depends(get_db),
    time_off_in: TimeOffUpdate,
    response: Response,
    current_user: User = Depends(get_current_active_user)
) -> DataResponse:
    """
    Update an existing time off period.
    """
    try:
        # Get the time off by ID
        time_off = crud_time_off.get(db=db, time_off_id=time_off_id)
        if not time_off:
            response.status_code = status.HTTP_404_NOT_FOUND
            return DataResponse.error_response(
                message="Time off not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Check if the time off belongs to the current user
        if str(time_off.user_id) != str(current_user.id):
            response.status_code = status.HTTP_403_FORBIDDEN
            return DataResponse.error_response(
                message="You don't have permission to update this time off",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Determine the new start and end dates for overlap check
        start_date = time_off_in.start_date if time_off_in.start_date is not None else time_off.start_date
        end_date = time_off_in.end_date if time_off_in.end_date is not None else time_off.end_date

        # Check for overlapping time offs
        has_overlap = crud_time_off.check_overlapping_time_offs(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            exclude_id=time_off_id
        )

        if has_overlap:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return DataResponse.error_response(
                message="The updated time off period overlaps with existing ones",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Update the time off
        updated_time_off = crud_time_off.update(
            db=db,
            db_obj=time_off,
            obj_in=time_off_in
        )

        return DataResponse.success_response(
            message="Time off updated successfully",
            data=updated_time_off,
            status_code=status.HTTP_200_OK
        )
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to update time off: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/time-offs/{time_off_id}", response_model=DataResponse, status_code=status.HTTP_200_OK)
async def delete_time_off(
    *,
    time_off_id: str,
    db: Session = Depends(get_db),
    response: Response,
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Delete a time off period.
    """
    # Get the time off by ID
    time_off = crud_time_off.get(db=db, time_off_id=time_off_id)
    if not time_off:
        response.status_code = status.HTTP_404_NOT_FOUND
        return DataResponse.error_response(
            message="Time off not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Delete the time off
    deleted = crud_time_off.delete(db=db, time_off_id=time_off_id)
    if not deleted:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message="Failed to delete time off",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return DataResponse.success_response(
        message="Time off deleted successfully",
        status_code=status.HTTP_200_OK
    )


@router.post("/auth/refresh-token", response_model=DataResponse[TokenResponse])
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Refresh access and refresh tokens using the refresh token cookie.
    """
    from app.core.config import settings
    try:
        # Get the refresh token from the request cookies
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )

        # Verify and decode the refresh token
        payload = verify_token(refresh_token, "refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Extract user data from payload
        user_id = payload.get("sub")
        email = payload.get("email")
        company_id = payload.get("company_id")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Create new tokens
        new_tokens = create_token_pair(
            id=user_id,
            email=email,
            actor="user",
            ver="1",
            company_id=company_id
        )

        # Determine cookie domain - use shared domain for production
        cookie_domain = ".salona.me" if "salona.me" in settings.API_URL else None
        is_production = "https://" in settings.API_URL

        # Set new cookies
        response.set_cookie(
            key="refresh_token",
            value=new_tokens["refresh_token"],
            max_age=new_tokens['rt_expires_in'],
            httponly=True,
            secure=is_production,
            samesite="lax",
            domain=cookie_domain
        )
        response.set_cookie(
            key="access_token",
            value=new_tokens["access_token"],
            max_age=new_tokens['at_expires_in'],
            httponly=True,
            secure=is_production,
            samesite="lax",
            domain=cookie_domain
        )

        return DataResponse.success_response(data=TokenResponse(**new_tokens))

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/auth/verify-token", response_model=DataResponse[dict])
async def verify_access_token(
    request: Request,
    response: Response
) -> DataResponse:
    """
    Verify the access token and return the token data.
    """
    try:
        # Get the access token from the request cookies
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token not found"
            )

        # Verify and decode the access token
        payload = verify_token(access_token, "access")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token"
            )

        # Return token validity info
        return DataResponse.success_response(data={
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "company_id": payload.get("company_id"),
            "expires_at": payload.get("exp")
        })

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify token: {str(e)}"
        )


@router.post("/auth/google/authorize", response_model=GoogleAuthorizationResponse)
async def google_authorize(
    response: Response
) -> GoogleAuthorizationResponse:
    """
    Initiate Google OAuth flow - returns authorization URL and state token.
    """
    try:
        state = GoogleOAuthService.generate_state_token()

        # Store state in response cookie for verification later
        response.set_cookie(
            key="google_oauth_state",
            value=state,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=600  # 10 minutes
        )

        authorization_url = GoogleOAuthService.get_authorization_url(state)

        return GoogleAuthorizationResponse(
            authorization_url=authorization_url,
            state=state
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth: {str(e)}"
        )


@router.get("/auth/google/callback", response_model=DataResponse[TokenResponse])
async def google_callback(
    request: Request,
    response: Response,
    state: str = Query(..., description="State token for CSRF protection"),
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Handle Google OAuth callback for both signup and login.
    - If user exists: authenticates and returns tokens
    - If user doesn't exist: creates new user with random password and returns tokens

    This unified endpoint eliminates the need for separate signup/login paths.
    """
    from app.core.config import settings
    try:
        error = None
        google_email = ""
        google_name = "Google User"  # Initialize with default value
        # Verify state token for CSRF protection
        stored_state = request.cookies.get("google_oauth_state")
        if not stored_state or stored_state != state:
            error = 'Invalid state parameter'
        else:
            # Get redirect_uri from environment or default
            redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/v1/users/auth/google/callback')

            # Exchange authorization code for tokens
            token_response = GoogleOAuthService.exchange_code_for_token(
                code,
                redirect_uri
            )
            print(f'Token response: {token_response}')
            if not token_response:
                error = 'Failed to exchange authorization code for tokens'
            else:
                access_token = token_response.get("access_token")
                if not access_token:
                    error = 'No access token in response'

                else:
                    # Get user info from Google
                    user_info = GoogleOAuthService.get_user_info(access_token)

                    if not user_info:
                        error = 'Failed to retrieve user information from Google'

                    else:
                        google_email = user_info.get("email", "").lower()
                        google_name = user_info.get("name", "Google User")

                        if not google_email:
                            error = 'Google account does not have an email'

        if error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error
            )
        # Check if user already exists
        user = crud_user.get_by_email(db=db, email=google_email)

        if user:
            # User exists - authenticate them
            company = crud_user.get_company_by_user(db, user.id)
            tokens = create_token_pair(
                user.id,
                user.email,
                actor="user",
                ver="1",
                company_id=str(company.company_id) if company else ''
            )
            auth_message = "Logged in successfully via Google"
        else:
            # User doesn't exist - create new user with random password
            random_password = GoogleOAuthService.generate_random_password()
            hashed_password = hash_password(random_password)

            # Parse name into first and last name
            name_parts = google_name.split(" ", 1)
            first_name = name_parts[0] if name_parts else "User"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Create user object
            user_create = UserCreate(
                first_name=first_name,
                last_name=last_name,
                email=google_email,
                password=hashed_password,
                phone=""  # Default empty phone for OAuth users
            )

            new_user, auth_message = await _create_new_user(
                db=db,
                user_in=user_create,
                send_verification_email=False  # No email verification for OAuth users
            )

            # Create tokens for new user
            tokens = create_token_pair(
                new_user.id,
                new_user.email,
                actor="user",
                ver="1",
                company_id=""
            )
            auth_message = "Account created and logged in successfully via Google"
            user = new_user

        # Set cookies
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=tokens['rt_expires_in'],
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="none"
        )
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=tokens['at_expires_in'],
            httponly=True,
            secure=True,  # only over HTTPS
            samesite="none"
        )

        # Clear the state cookie
        response.delete_cookie(key="google_oauth_state")
        return DataResponse.success_response(data = TokenResponse(**tokens))

    except Exception as e:
        return DataResponse.error_response(message=f"Google OAuth process failed: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/me/profile-photo", response_model=DataResponse[dict])
async def upload_profile_photo(
        *,
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
        current_user: Users = Depends(get_current_active_user)
) -> DataResponse:
    """Upload profile photo to S3 and update user record."""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            return DataResponse.error_response(
                message="Invalid file type. Only JPEG, PNG, and WebP are allowed",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (e.g., max 5MB)
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:
            return DataResponse.error_response(
                message="File size exceeds 5MB limit",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Upload to S3 (implement this service)
        from app.services.file_storage import file_storage_service
        photo_url = await file_storage_service.upload_file(
            file_content=file_content,
            file_name=f"users/{current_user.id}/profile.{file.filename.split('.')[-1]}",
            content_type=file.content_type
        )

        # Update user record
        _ = crud_user.update(
            db=db,
            db_obj=current_user,
            obj_in=UserUpdate(profile_photo_url=photo_url)
        )

        return DataResponse.success_response(
            message="Profile photo uploaded successfully",
            data={"profile_photo_url": photo_url}
        )
    except Exception as e:
        return DataResponse.error_response(
            message=f"Failed to upload profile photo: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/me/profile-photo", response_model=DataResponse)
async def delete_profile_photo(
        *,
        db: Session = Depends(get_db),
        current_user: Users = Depends(get_current_active_user)
) -> DataResponse:
    """Upload profile photo to S3 and update user record."""
    try:
        # Update user record
        _ = crud_user.update(
            db=db,
            db_obj=current_user,
            obj_in=UserUpdate(profile_photo_url=None)
        )

        return DataResponse.success_response(
            message="Profile photo deleted successfully",
        )
    except Exception as e:
        return DataResponse.error_response(
            message=f"Failed to delete profile photo: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
