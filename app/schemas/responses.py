from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel
from fastapi import status

T = TypeVar('T')

class BaseResponse(BaseModel):
    success: bool
    message: str
    status_code: int = status.HTTP_200_OK
    
class DataResponse(BaseResponse, Generic[T]):
    data: Optional[T] = None
    
    @classmethod
    def success_response(cls, data: Optional[T] = None, message: str = "Success", status_code: int = status.HTTP_200_OK) -> "DataResponse[T]":
        return cls(
            success=True,
            message=message,
            status_code=status_code,
            data=data
        )
    
    @classmethod
    def error_response(cls, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, data: Optional[T] = None) -> "DataResponse[T]":
        return cls(
            success=False,
            message=message,
            status_code=status_code,
            data=data
        )

class ErrorResponse(BaseResponse):
    error_code: Optional[str] = None
    details: Optional[Any] = None
    
    @classmethod
    def create(cls, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: Optional[str] = None, details: Optional[Any] = None) -> "ErrorResponse":
        return cls(
            success=False,
            message=message,
            status_code=status_code,
            error_code=error_code,
            details=details
        )