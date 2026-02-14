from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.schemas import (CompanyCategoryWithServicesResponse, CompanyUser,
                               CompanyCategoryCreate, CompanyCategoryUpdate, CompanyCategory,
                               CategoryServiceCreate, CategoryServiceUpdate, CategoryServiceResponse,
                               CompanyCategoryHierarchical)
from app.schemas.responses import DataResponse
import uuid
import json
from app.services.crud import service as crud_service, user as crud_user, company as crud_company
from app.services.file_storage import file_storage_service
from app.api.dependencies import get_current_company_id

router = APIRouter()


@router.get("/companies/{company_slug}/services", response_model=DataResponse[List[CompanyCategoryWithServicesResponse]])
async def get_company_services(
    company_slug: str,
    db: AsyncSession = Depends(get_db)
) -> DataResponse:
    """
    Get service by company ID with details.
    """
    company = await crud_company.get_by_slug(db=db, slug=company_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    company_id = str(company.id)
    services = await crud_service.get_company_services(db=db, company_id=company_id)
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
async def get_company_users(
    company_slug: str,
    db: AsyncSession = Depends(get_db)
) -> DataResponse:
    """
    Get users by company ID with details.
    """
    company = await crud_company.get_by_slug(db=db, slug=company_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    company_id = str(company.id)
    users = await crud_user.get_company_users(db=db, company_id=company_id)
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
async def create_category(
        *,
        db: AsyncSession = Depends(get_db),
        category_in: CompanyCategoryCreate,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a new service category or subcategory.
    If parent_category_id is provided, validates that the parent category doesn't have services.
    """
    try:
        # Validate parent category if this is a subcategory
        if category_in.parent_category_id:
            parent_category = await crud_service.get_category(db=db, category_id=str(category_in.parent_category_id))
            if not parent_category:
                return DataResponse.error_response(
                    message="Parent category not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            if str(parent_category.company_id) != company_id:
                return DataResponse.error_response(
                    message="Parent category does not belong to this company",
                    status_code=status.HTTP_403_FORBIDDEN
                )

            # Check if parent has services
            if parent_category.services_count > 0:
                return DataResponse.error_response(
                    message="Cannot add subcategories to a category that already has services. Please remove the services first.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # Create the category
        category_in.company_id = company_id
        category = await crud_service.create_category(db=db, obj_in=category_in)

        return DataResponse.success_response(
            data=category,
            message="Category created successfully"
        )
    except Exception as e:
        await db.rollback()
        return DataResponse.error_response(
            message=f"Failed to create category: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.get("/categories/{category_id}", response_model=DataResponse[CompanyCategory])
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db)
) -> DataResponse:
    """
    Get a specific category by ID.
    """
    category = await crud_service.get_category(db=db, category_id=category_id)
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
async def get_company_categories(
        db: AsyncSession = Depends(get_db),
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all categories for a company (flat list).
    """
    categories = await crud_service.get_company_categories(db=db, company_id=company_id)

    return DataResponse.success_response(
        data=categories,
        message="Categories fetched successfully"
    )


@router.get("/companies/categories/hierarchical", response_model=DataResponse[List[CompanyCategoryHierarchical]])
async def get_company_categories_hierarchical(
        db: AsyncSession = Depends(get_db),
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get all categories for a company in hierarchical structure (categories with nested subcategories).
    """
    categories = await crud_service.get_company_categories_hierarchical(db=db, company_id=company_id)

    return DataResponse.success_response(
        data=categories,
        message="Categories fetched successfully"
    )


@router.put("/categories/{category_id}", response_model=DataResponse[CompanyCategory])
async def update_category(
        *,
        db: AsyncSession = Depends(get_db),
        category_id: str,
        category_in: CompanyCategoryUpdate,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Update a service category.
    """
    category_in.company_id = company_id
    category = await crud_service.get_category(db=db, category_id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    updated_category = await crud_service.update_category(
        db=db,
        db_obj=category,
        obj_in=category_in
    )

    return DataResponse.success_response(
        data=updated_category,
        message="Category updated successfully"
    )


@router.delete("/categories/{category_id}", response_model=DataResponse)
async def delete_category(
        *,
        db: AsyncSession = Depends(get_db),
        category_id: str,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Delete a service category.
    """
    success = await crud_service.delete_category(db=db, category_id=category_id, company_id=company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return DataResponse.success_response(
        message="Category deleted successfully"
    )


@router.post("", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
        *,
        db: AsyncSession = Depends(get_db),
        service_in: Annotated[str, Form(...)],
        image: Annotated[UploadFile | None, File()] = None,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a new service.
    Services can only be added to categories that don't have subcategories.
    """
    try:

        service_in = CategoryServiceCreate(**json.loads(service_in))
        # Verify that the category belongs to the company
        category = await crud_service.get_category(db=db, category_id=service_in.category_id)
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

        # Create the service (validation happens inside)
        service = await crud_service.create_service(db=db, obj_in=service_in)

        return DataResponse.success_response(
            data=None,
            message="Service created successfully"
        )
    except ValueError as e:
        # Handle validation errors (e.g., category has subcategories)
        await db.rollback()
        return DataResponse.error_response(
            message=str(e),
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        await db.rollback()
        return DataResponse.error_response(
            message=f"Failed to create service: {str(e)}",
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/services/{service_id}", response_model=DataResponse[CategoryServiceResponse])
async def get_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Get a specific service by ID.
    """
    service = await crud_service.get_service(db=db, service_id=service_id, company_id=company_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return DataResponse.success_response(
        data=service,
        message="Service fetched successfully"
    )


@router.put("/service/{service_id}", response_model=DataResponse)
async def update_service(
        *,
        db: AsyncSession = Depends(get_db),
        service_id: str,
        service_in: Annotated[str, Form(...)],
        image: Annotated[UploadFile | None, File()] = None,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Update a service.
    Can move service to a different category if the target category doesn't have subcategories.
    """
    try:
        service_in = CategoryServiceUpdate(**json.loads(service_in))

        # Verify the service exists and belongs to the company
        service = await crud_service.get_service(db=db, service_id=service_id, company_id=company_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        # Validate new category if being changed
        if service_in.category_id and str(service_in.category_id) != str(service.category_id):
            new_category = await crud_service.get_category(db=db, category_id=str(service_in.category_id))
            if not new_category:
                return DataResponse.error_response(
                    message="Target category not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            if str(new_category.company_id) != company_id:
                return DataResponse.error_response(
                    message="Target category does not belong to this company",
                    status_code=status.HTTP_403_FORBIDDEN
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

        # Update the service (validation happens inside)
        updated_service = await crud_service.update_service(
            db=db,
            db_obj=service,
            obj_in=service_in
        )

        return DataResponse.success_response(
            data=None,
            message="Service updated successfully"
        )
    except ValueError as e:
        # Handle validation errors (e.g., category has subcategories)
        await db.rollback()
        return DataResponse.error_response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        await db.rollback()
        return DataResponse.error_response(
            message=f"Failed to update service: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/service/{service_id}", response_model=DataResponse)
async def delete_service(
        *,
        db: AsyncSession = Depends(get_db),
        service_id: str,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Delete a service.
    """
    success = await crud_service.delete_service(db=db, service_id=service_id, company_id=company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return DataResponse.success_response(
        message="Service deleted successfully"
    )


@router.post("/service/{service_id}/copy", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def copy_service(
        *,
        db: AsyncSession = Depends(get_db),
        service_id: str,
        company_id: str = Depends(get_current_company_id)
) -> DataResponse:
    """
    Create a copy of an existing service.
    The copied service will include all properties and staff assignments from the original service.
    The name will have " (Copy)" appended to it.
    """
    try:
        # Copy the service
        copied_service = await crud_service.copy_service(db=db, service_id=service_id, company_id=company_id)

        if not copied_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        return DataResponse.success_response(
            data=None,
            message="Service copied successfully"
        )
    except Exception as e:
        await db.rollback()
        return DataResponse.error_response(
            message=f"Failed to copy service: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


