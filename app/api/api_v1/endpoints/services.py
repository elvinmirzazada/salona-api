from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schemas import (CompanyCategoryWithServicesResponse, CompanyUser,
                               CompanyCategoryCreate, CompanyCategoryUpdate, CompanyCategory,
                               CategoryServiceCreate, CategoryServiceUpdate, CategoryServiceResponse)
from app.schemas.responses import DataResponse
import uuid
import json
from app.services.crud import service as crud_service, user as crud_user, company as crud_company
from app.services.file_storage import file_storage_service
from app.api.dependencies import get_current_company_id

router = APIRouter()


@router.get("/companies/{company_slug}/services", response_model=DataResponse[List[CompanyCategoryWithServicesResponse]])
def get_company_services(
    company_slug: str,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Get service by company ID with details.
    """
    company = crud_company.get_by_slug(db=db, slug=company_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    company_id = str(company.id)
    services = crud_service.get_company_services(db=db, company_id=company_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return DataResponse.success_response(
        data=services,
        message="Services fetched successfully"
    )


@router.get("/companies/{company_slug}/staff", response_model=DataResponse[List[CompanyUser]])
def get_company_users(
    company_slug: str,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Get users by company ID with details.
    """
    company = crud_company.get_by_slug(db=db, slug=company_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    company_id = str(company.id)
    users = crud_user.get_company_users(db=db, company_id=company_id)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return DataResponse.success_response(
        data=users,
        message="Services fetched successfully"
    )


@router.post("/categories", response_model=DataResponse[CompanyCategory], status_code=status.HTTP_201_CREATED)
def create_category(
        *,
        db: Session = Depends(get_db),
        category_in: CompanyCategoryCreate,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a new service category.
    """
    try:
        # Create the category
        category_in.company_id = company_id
        category = crud_service.create_category(db=db, obj_in=category_in)

        return DataResponse.success_response(
            data=category,
            message="Category created successfully"
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to create categroy: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.get("/categories/{category_id}", response_model=DataResponse[CompanyCategory])
def get_category(
    category_id: str,
    db: Session = Depends(get_db)
) -> DataResponse:
    """
    Get a specific category by ID.
    """
    category = crud_service.get_category(db=db, category_id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return DataResponse.success_response(
        data=category,
        message="Category fetched successfully"
    )


@router.get("/companies/categories", response_model=DataResponse[List[CompanyCategory]])
def get_company_categories(
        db: Session = Depends(get_db),
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all categories for a company.
    """
    categories = crud_service.get_company_categories(db=db, company_id=company_id)

    return DataResponse.success_response(
        data=categories,
        message="Categories fetched successfully"
    )


@router.put("/categories/{category_id}", response_model=DataResponse[CompanyCategory])
def update_category(
        *,
        db: Session = Depends(get_db),
        category_id: str,
        category_in: CompanyCategoryUpdate,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Update a service category.
    """
    category_in.company_id = company_id
    category = crud_service.get_category(db=db, category_id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    updated_category = crud_service.update_category(
        db=db,
        db_obj=category,
        obj_in=category_in
    )

    return DataResponse.success_response(
        data=updated_category,
        message="Category updated successfully"
    )


@router.delete("/categories/{category_id}", response_model=DataResponse)
def delete_category(
        *,
        db: Session = Depends(get_db),
        category_id: str,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Delete a service category.
    """
    success = crud_service.delete_category(db=db, category_id=category_id, company_id=company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return DataResponse.success_response(
        message="Category deleted successfully"
    )


@router.post("", response_model=DataResponse[CategoryServiceResponse], status_code=status.HTTP_201_CREATED)
async def create_service(
        *,
        db: Session = Depends(get_db),
        service_in: Annotated[str, Form(...)],
        image: Annotated[UploadFile | None, File()] = None,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a new service.
    """
    try:

        service_in = CategoryServiceCreate(**json.loads(service_in))
        # Verify that the category belongs to the company
        category = crud_service.get_category(db=db, category_id=service_in.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        if str(category.company_id) != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Category does not belong to this company"
            )

        # Upload image if provided
        if image:
            file_content = await image.read()
            filename = f"services/{uuid.uuid4()}/service.{image.filename.split('.')[-1]}"
            image_url = await file_storage_service.upload_file(
                file_content=file_content,
                file_name=filename,
                content_type=image.content_type
            )
            service_in.image_url = image_url

        # Create the service
        service = crud_service.create_service(db=db, obj_in=service_in)

        return DataResponse.success_response(
            data=service,
            message="Service created successfully"
        )
    except Exception as e:
        db.rollback()
        return DataResponse.error_response(
            message=f"Failed to create service: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/services/{service_id}", response_model=DataResponse[CategoryServiceResponse])
def get_service(
    service_id: str,
    db: Session = Depends(get_db),
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get a specific service by ID.
    """
    service = crud_service.get_service(db=db, service_id=service_id, company_id=company_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return DataResponse.success_response(
        data=service,
        message="Service fetched successfully"
    )


@router.put("/service/{service_id}", response_model=DataResponse[CategoryServiceResponse])
async def update_service(
        *,
        db: Session = Depends(get_db),
        service_id: str,
        service_in: Annotated[str, Form(...)],
        image: Annotated[UploadFile | None, File()] = None,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Update a service.
    """

    service_in = CategoryServiceUpdate(**json.loads(service_in))

    # Verify the service exists and belongs to the company
    service = crud_service.get_service(db=db, service_id=service_id, company_id=company_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    # Handle image removal
    if service_in.remove_image and service.image_url:
        try:
            await file_storage_service.remove_file(service.image_url)
            service_in.image_url = None
        except Exception as e:
            # Log the error but don't fail the update
            print(f"Failed to remove image: {str(e)}")

    # Upload new image if provided
    if image:
        # Remove old image if exists
        if service.image_url:
            try:
                await file_storage_service.remove_file(service.image_url)
            except Exception as e:
                # Log the error but don't fail the update
                print(f"Failed to remove old image: {str(e)}")

        # Upload new image
        filename_prefix = f"{uuid.uuid4()}"

        file_content = await image.read()
        filename = f"services/{filename_prefix}/service.{image.filename.split('.')[-1]}"
        image_url = await file_storage_service.upload_file(
            file_content=file_content,
            file_name=filename,
            content_type=image.content_type
        )
        service_in.image_url = image_url

    # Update the service
    updated_service = crud_service.update_service(
        db=db,
        db_obj=service,
        obj_in=service_in
    )

    return DataResponse.success_response(
        data=updated_service,
        message="Service updated successfully"
    )


@router.delete("/service/{service_id}", response_model=DataResponse)
def delete_service(
        *,
        db: Session = Depends(get_db),
        service_id: str,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Delete a service.
    """
    success = crud_service.delete_service(db=db, service_id=service_id, company_id=company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return DataResponse.success_response(
        message="Service deleted successfully"
    )
