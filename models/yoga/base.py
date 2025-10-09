from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models import Base


Instructors = Table(
    "instructors",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("auth.users.id"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.courses.id"), primary_key=True),
    schema="courses",
)


class YogaSchool(Base):
    __tablename__ = 'schools'
    __table_args__ = dict(
        schema="admin"
    )

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('auth.users.id'), nullable=False)  # User who owns/manages the school
    name = Column(String(255), nullable=False)
    description = Column(Text)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    website = Column(String(255))

    # Registration info
    registration_number = Column(String(100), unique=True)  # Official registration number
    certification_body = Column(String(255))  # Yoga Alliance, etc.

    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    locations = relationship("Location", back_populates="school", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="school", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<YogaSchool(name='{self.name}', email='{self.email}')>"


class InstructorProfile(Base):
    """
    Additional metadata for users with INSTRUCTOR role.
    This extends the base User model with yoga-specific instructor information.
    """
    __tablename__ = 'instructor_profiles'
    __table_args__ = dict(
        schema="courses"
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth.users.id'), nullable=False, unique=True)

    # Professional yoga credentials
    certification_level = Column(Integer, ForeignKey('courses.certification_levels.id'), nullable=False)
    certification_body = Column(String(100))  # Yoga Alliance, etc.
    years_experience = Column(Integer)
    bio = Column(Text)

    # Teaching specializations (stored as JSON array in JSONB for better querying)
    specializations = Column(Text)  # JSON string: ["Hatha", "Vinyasa", "Meditation"]

    # Teaching preferences and availability
    preferred_class_types = Column(Text)  # JSON string
    max_students_per_class = Column(Integer)
    travel_radius_km = Column(Integer)  # How far willing to travel

    # Rates and availability
    hourly_rate = Column(Numeric(8, 2), nullable=False)
    currency = Column(Integer, ForeignKey('payments.currencies.id'), nullable=False)
    is_available_for_hire = Column(Boolean, default=False)

    # Social media and portfolio
    instagram_handle = Column(String(100), unique=True)
    youtube_channel = Column(String(255), unique=True)
    personal_website = Column(String(255), unique=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="instructor_profile")

    def __repr__(self):
        return f"<InstructorProfile(user_id={self.user_id}, level='{self.certification_level}')>"


class Location(Base):
    __tablename__ = 'locations'
    __table_args__ = dict(
        schema="admin"
    )

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey('admin.schools.id'), nullable=False)

    # Location details
    name = Column(String(255), nullable=False)  # Studio name or branch name
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), nullable=False, default='India')

    # Geographic coordinates
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))

    # Contact info
    phone = Column(String(20))
    email = Column(String(255))

    # Facility details
    capacity = Column(Integer)  # Maximum students
    amenities = Column(Text)  # JSON string of amenities

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    school = relationship("YogaSchool", back_populates="locations")
    courses = relationship("Course", back_populates="location")

    def __repr__(self):
        return f"<Location(name='{self.name}', city='{self.city}')>"


class Course(Base):
    __tablename__ = 'courses'
    __table_args__ = dict(
        schema="courses"
    )

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey('admin.schools.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('admin.locations.id'), nullable=False)

    # Course details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    course_type = Column(Integer, ForeignKey('courses.types.id'), nullable=False)  # Workshop, Retreat, TTC, etc.
    style = Column(Integer, ForeignKey('courses.styles.id'))  # Hatha, Vinyasa, etc.
    level = Column(Integer, ForeignKey('courses.experience_level.id'))  # Beginner, Intermediate, Advanced
    certification_level = Column(Integer, ForeignKey('courses.certification_levels.id'))  # 200HR, 300HR, etc.

    # Duration and scheduling
    duration_hours = Column(Integer)  # Total course hours
    duration_days = Column(Integer)  # Total course days
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    schedule_details = Column(Text)  # JSON string with detailed schedule

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(Integer, ForeignKey('payments.currencies.id'), nullable=False)
    early_bird_price = Column(Numeric(10, 2))
    early_bird_deadline = Column(DateTime(timezone=True))

    # Capacity and registration
    max_students = Column(Integer, nullable=False)
    min_students = Column(Integer, default=1)
    current_registrations = Column(Integer, default=0)

    # Requirements and inclusions
    prerequisites = Column(Text)
    what_to_bring = Column(Text)
    what_included = Column(Text)
    accommodation_info = Column(Text)

    # Status
    status = Column(Integer, ForeignKey('courses.status.id'), default=1)  # Default to 'upcoming'
    is_featured = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    school = relationship("YogaSchool", back_populates="courses")
    location = relationship("Location", back_populates="courses")
    course_type_rel = relationship("CourseType")
    style_rel = relationship("Style")
    level_rel = relationship("ExperienceLevel")
    certification_level_rel = relationship("CertificationLevel")
    currency_rel = relationship("Currency")
    status_rel = relationship("CourseStatus")
    instructors = relationship("User", secondary=Instructors, backref="courses_teaching")

    @property
    def available_spots(self):
        return self.max_students - self.current_registrations

    @property
    def is_full(self):
        return self.current_registrations >= self.max_students

    @property
    def is_early_bird_valid(self):
        if not self.early_bird_deadline:
            return False
        return func.now() <= self.early_bird_deadline

    def __repr__(self):
        return f"<Course(title='{self.title}', type='{self.course_type}')>"
