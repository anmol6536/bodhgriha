# models/yoga/enums.py
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from models import Base


class Gender(Base):
    __tablename__ = 'genders'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="core"
    )


class Currency(Base):
    __tablename__ = 'currencies'

    id = Column(Integer, primary_key=True)
    code = Column(String(3), unique=True, nullable=False)  # INR, USD, EUR
    name = Column(String(50), nullable=False)  # Indian Rupee, US Dollar
    symbol = Column(String(5))  # ₹, $, €
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="payments"
    )


class CourseType(Base):
    __tablename__ = 'types'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    label = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="courses"
    )


class ExperienceLevel(Base):
    __tablename__ = 'experience_level'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="courses"
    )


class Style(Base):
    __tablename__ = 'styles'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="courses"
    )


class CourseLevel(Base):
    __tablename__ = 'course_levels'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class CourseStatus(Base):
    __tablename__ = 'status'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="courses"
    )


class RegistrationStatus(Base):
    __tablename__ = 'registration_statuses'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="registrations"
    )


class PaymentStatus(Base):
    __tablename__ = 'status'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="payments"
    )


class PaymentMethod(Base):
    __tablename__ = 'methods'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="payments"
    )


class CertificationLevel(Base):
    __tablename__ = 'certification_levels'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(Text)
    hours_required = Column(Integer)
    is_active = Column(Boolean, default=True)

    __table_args__ = dict(
        schema="courses"
    )
