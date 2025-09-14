from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from app.models.models import (Customers, CustomerVerifications, CustomerPhones,
                               CustomerEmails)
from app.schemas.schemas import (
    BusinessCreate, BusinessUpdate,
    ServiceCreate, ServiceUpdate,
    CustomerCreate, CustomerUpdate,
    AppointmentCreate, AppointmentUpdate,
    ProfessionalCreate, ProfessionalUpdate, 
    BusinessStaffCreate
)


# class CRUDProfessional:
#     def get(self, db: Session, id: int) -> Optional[Professional]:
#         return db.query(Professional).filter(Professional.id == id).first()
#
#     def get_by_mobile(self, db: Session, mobile_number: str) -> Optional[Professional]:
#         return db.query(Professional).filter(Professional.mobile_number == mobile_number).first()
#
#     def create(self, db: Session, *, obj_in: ProfessionalCreate) -> Professional:
#         db_obj = Professional(
#             first_name=obj_in.first_name,
#             last_name=obj_in.last_name,
#             password=obj_in.password,  # Should be hashed before storing
#             mobile_number=obj_in.mobile_number,
#             country=obj_in.country,
#             accept_privacy_policy=obj_in.accept_privacy_policy
#         )
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#     def update(self, db: Session, *, db_obj: Professional, obj_in: ProfessionalUpdate) -> Professional:
#         update_data = obj_in.model_dump(exclude_unset=True)
#         for field, value in update_data.items():
#             setattr(db_obj, field, value)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
#
#
# class CRUDBusiness:
#     def get(self, db: Session, id: int) -> Optional[Business]:
#         return db.query(Business).filter(Business.id == id).first()
#
#     def get_multi_by_owner(self, db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[Business]:
#         return db.query(Business).filter(Business.owner_id == owner_id).offset(skip).limit(limit).all()
#
#     def create(self, db: Session, *, obj_in: BusinessCreate) -> Business:
#         db_obj = Business(**obj_in.model_dump())
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
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
# class CRUDService:
#     def get(self, db: Session, id: int) -> Optional[Service]:
#         return db.query(Service).filter(Service.id == id).first()
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
    def get(self, db: Session, id: int) -> Optional[Customers]:
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


# class CRUDAppointment:
#     def get(self, db: Session, id: int) -> Optional[Appointment]:
#         return db.query(Appointment).filter(Appointment.id == id).first()
#
#     def get_multi_by_business(self, db: Session, business_id: int, skip: int = 0, limit: int = 100) -> List[Appointment]:
#         return db.query(Appointment).filter(Appointment.business_id == business_id).offset(skip).limit(limit).all()
#
#     def get_multi_by_client(self, db: Session, client_id: int, skip: int = 0, limit: int = 100) -> List[Appointment]:
#         return db.query(Appointment).filter(Appointment.client_id == client_id).offset(skip).limit(limit).all()
#
#     def create(self, db: Session, *, obj_in: AppointmentCreate) -> Appointment:
#         db_obj = Appointment(**obj_in.model_dump())
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj
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
# professional = CRUDProfessional()
# business = CRUDBusiness()
# service = CRUDService()
customer = CRUDCustomer()
# appointment = CRUDAppointment()
# business_staff = CRUDBusinessStaff()
