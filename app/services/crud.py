from datetime import timedelta
from typing import List, Optional, Any

from pydantic.v1 import UUID4
from sqlalchemy.orm import Session
import uuid

from app.models import CompanyRoleType, StatusType, BookingServices
from app.models.models import (Customers, CustomerVerifications, CompanyUsers, Users,
                               CustomerEmails, Companies, CompanyServices, Bookings)
from app.schemas import BookingServiceRequest
from app.schemas.schemas import (
    CompanyCreate,
    CustomerCreate, CustomerUpdate,
    UserCreate, UserUpdate, User,
    BookingCreate
)


class CRUDUser:
    @staticmethod
    def get(db: Session, id: UUID4) -> Optional[Users]:
        return db.query(Users).filter(Users.id == id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Users]:
        return db.query(Users).filter(Users.email == email).first()

    @staticmethod
    def create(db: Session, *, obj_in: UserCreate) -> Users:
        db_obj = Users(**obj_in.model_dump())
        db_obj.id = str(uuid.uuid4())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    #
    # def update(self, db: Session, *, db_obj: Professional, obj_in: ProfessionalUpdate) -> Professional:
    #     update_data = obj_in.model_dump(exclude_unset=True)
    #     for field, value in update_data.items():
    #         setattr(db_obj, field, value)
    #     db.add(db_obj)
    #     db.commit()
    #     db.refresh(db_obj)
    #     return db_obj
#
#
class CRUDCompany:
    @staticmethod
    def get(db: Session, id: UUID4) -> Optional[Companies]:
        return db.query(Companies).filter(Companies.id == id).first()

    @staticmethod
    def create(db: Session, *, obj_in: CompanyCreate, current_user: User) -> Companies:
        try:
            db_obj = Companies(**obj_in.model_dump())
            db_obj.id = str(uuid.uuid4())
            db.add(db_obj)
            print(db_obj.id)

            cmp_usr_obj = CompanyUsers(user_id=current_user.id,
                                       company_id=db_obj.id,
                                       role=CompanyRoleType.admin,
                                       status=StatusType.active)
            cmp_usr_obj.id = str(uuid.uuid4())
            db.add(cmp_usr_obj)
            db.commit()
            db.refresh(cmp_usr_obj)
            db.refresh(db_obj)

            return db_obj
        except Exception as e:
            db.rollback()
            raise e

#
#     def update(self, db: Session, *, db_obj: Business, obj_in: BusinessUpdate) -> Business:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#
# class CRUDBusinessStaff:
#     def get(self, db: Session, id: int) -> Optional[BusinessStaff]:
#         return db.query(BusinessStaff).filter(BusinessStaff.id == id).first()
#
#     def create(self, db: Session, *, obj_in: BusinessStaffCreate) -> BusinessStaff:
#         db_obj = BusinessStaff(**obj_in.model_dump())
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#     def update(self, db: Session, *, db_obj: BusinessStaff, obj_in: BusinessStaffCreate) -> BusinessStaff:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#
class CRUDService:
    @staticmethod
    def get_company_service(db: Session, id: UUID4) -> Optional[CompanyServices]:
        return db.query(CompanyServices).filter(CompanyServices.id == id).first()
#
#     def get_multi_by_business(self, db: Session, business_id: int, skip: int = 0, limit: int = 100) -> List[Service]:
#         return db.query(Service).filter(Service.business_id == business_id).offset(skip).limit(limit).all()
#
#     def create(self, db: Session, *, obj_in: ServiceCreate) -> Service:
#         db_obj = Service(**obj_in.model_dump())
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#     def update(self, db: Session, *, db_obj: Service, obj_in: ServiceUpdate) -> Service:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj


class CRUDCustomer:
    @staticmethod
    def get(db: Session, id: UUID4) -> Optional[Customers]:
        return db.query(Customers).filter(Customers.id == id).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[Customers]:
        return db.query(Customers).filter(Customers.email == email).first()

    def create(self, db: Session, *, obj_in: CustomerCreate) -> Customers:
        db_obj = Customers(**obj_in.model_dump())
        db_obj.id = str(uuid.uuid4())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_customer_email(self, db: Session, customer_id: int, email: str, status: str) -> CustomerEmails:
        db_obj = CustomerEmails(customer_id=customer_id, email=email, status=status)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Customers, obj_in: CustomerUpdate) -> Customers:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_verification_token(self, db: Session, token: str, type: str) -> Optional[CustomerVerifications]:
        return db.query(CustomerVerifications).filter(CustomerVerifications.token == token,
                                                      CustomerVerifications.type == type).first()

    def verify_token(self, db: Session, db_obj: CustomerVerifications) -> CustomerVerifications:
        db_obj.status = "verified"
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDBooking:
    @staticmethod
    def get(db: Session, id: UUID4) -> Optional[Bookings]:
        return db.query(Bookings).filter(Bookings.id == id).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[type[Bookings]]:
        return list(db.query(Bookings).offset(skip).limit(limit).all())
#
#     def get_multi_by_business(self, db: Session, business_id: int, skip: int = 0, limit: int = 100) -> List[Appointment]:
#         return db.query(Appointment).filter(Appointment.business_id == business_id).offset(skip).limit(limit).all()
#
#     def get_multi_by_client(self, db: Session, client_id: int, skip: int = 0, limit: int = 100) -> List[Appointment]:
#         return db.query(Appointment).filter(Appointment.client_id == client_id).offset(skip).limit(limit).all()
#
    @staticmethod
    def calc_service_params(db, services: List[BookingServiceRequest]):
        total_duration = 0
        total_price = 0

        for srv in services:
            selected_srv = CRUDService.get_company_service(db, srv.company_service_id)
            total_duration += selected_srv.custom_duration
            total_price += int(selected_srv.custom_price)

        return total_duration, total_price



    def create(self, db: Session, *, obj_in: BookingCreate, customer_id: UUID4) -> Bookings:
        total_duration, total_price = self.calc_service_params(db, obj_in.services)
        db_obj = Bookings(
            customer_id=customer_id,
            company_id=obj_in.company_id,
            start_at=obj_in.start_time,
            end_at= obj_in.start_time + timedelta(minutes=total_duration),
            total_price=total_price,
            notes=obj_in.notes
        )
        db.add(db_obj)
        db.commit()

        start_time = obj_in.start_time
        for srv in obj_in.services:
            duration, _ = self.calc_service_params(db, obj_in.services)
            db_service_obj = BookingServices(
                booking_id=db_obj.id,
                company_service_id=srv.company_service_id,
                user_id=srv.user_id,
                notes=srv.notes,
                start_at=start_time,
                end_at=start_time + timedelta(minutes=duration)
            )
            start_time = db_service_obj.end_at
            db.add(db_service_obj)

        db.commit()
        db.refresh(db_obj)
        return db_obj
#
#     def update(self, db: Session, *, db_obj: Appointment, obj_in: AppointmentUpdate) -> Appointment:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj


# Create instances
user = CRUDUser
company = CRUDCompany()
service = CRUDService()
customer = CRUDCustomer()
booking = CRUDBooking()
# appointment = CRUDAppointment()
# business_staff = CRUDBusinessStaff()
