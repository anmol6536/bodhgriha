# scripts/seed_enums.py
from models.enum import *
from sqlalchemy.orm import Session


def seed_enums(db_session: Session) -> None:
    """Seed all enumeration tables with initial data"""

    # Genders
    genders = [
        {'code': 'male', 'label': 'Male'},
        {'code': 'female', 'label': 'Female'},
        {'code': 'other', 'label': 'Other'},
        {'code': 'prefer_not_to_say', 'label': 'Prefer not to say'}
    ]
    for gender_data in genders:
        if not db_session.query(Gender).filter_by(code=gender_data['code']).first():
            db_session.add(Gender(**gender_data))

    # Currencies
    currencies = [
        {'code': 'INR', 'name': 'Indian Rupee', 'symbol': '₹'},
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
        {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'}
    ]
    for currency_data in currencies:
        if not db_session.query(Currency).filter_by(code=currency_data['code']).first():
            db_session.add(Currency(**currency_data))

    # Course Types
    course_types = [
        {'code': 'teacher_training', 'label': 'Teacher Training',
         'description': '200HR, 300HR, 500HR certification courses'},
        {'code': 'workshop', 'label': 'Workshop', 'description': 'Short intensive sessions on specific topics'},
        {'code': 'regular_class', 'label': 'Regular Class', 'description': 'Ongoing weekly or monthly classes'},
        {'code': 'retreat', 'label': 'Retreat', 'description': 'Multi-day intensive programs'},
        {'code': 'certification', 'label': 'Certification', 'description': 'Specialized certification programs'}
    ]
    for course_type_data in course_types:
        if not db_session.query(CourseType).filter_by(code=course_type_data['code']).first():
            db_session.add(CourseType(**course_type_data))

    # Yoga Experience Levels
    experience_levels = [
        {'code': 'beginner', 'label': 'Beginner', 'sort_order': 1},
        {'code': '1-2_years', 'label': '1-2 years', 'sort_order': 2},
        {'code': '3-5_years', 'label': '3-5 years', 'sort_order': 3},
        {'code': '5+_years', 'label': '5+ years', 'sort_order': 4},
        {'code': 'instructor', 'label': 'Instructor', 'sort_order': 5}
    ]
    for exp_data in experience_levels:
        if not db_session.query(YogaExperienceLevel).filter_by(code=exp_data['code']).first():
            db_session.add(YogaExperienceLevel(**exp_data))

    # Yoga Styles
    yoga_styles = [
        {'code': 'hatha', 'name': 'Hatha', 'description': 'Gentle, slow-paced style focusing on basic poses'},
        {'code': 'vinyasa', 'name': 'Vinyasa', 'description': 'Flow style linking movement with breath'},
        {'code': 'ashtanga', 'name': 'Ashtanga', 'description': 'Dynamic, athletic style with set sequences'},
        {'code': 'iyengar', 'name': 'Iyengar', 'description': 'Precise alignment-focused practice with props'},
        {'code': 'kundalini', 'name': 'Kundalini',
         'description': 'Spiritual practice combining poses, breathing, and meditation'},
        {'code': 'yin', 'name': 'Yin', 'description': 'Passive, long-held poses targeting deep tissues'},
        {'code': 'restorative', 'name': 'Restorative', 'description': 'Relaxing practice using props for support'},
        {'code': 'meditation', 'name': 'Meditation', 'description': 'Focused mindfulness and breathing practices'},
        {'code': 'pranayama', 'name': 'Pranayama', 'description': 'Breathing techniques and exercises'}
    ]
    for style_data in yoga_styles:
        if not db_session.query(YogaStyle).filter_by(code=style_data['code']).first():
            db_session.add(YogaStyle(**style_data))

    # Course Levels
    course_levels = [
        {'code': 'beginner', 'label': 'Beginner', 'sort_order': 1},
        {'code': 'intermediate', 'label': 'Intermediate', 'sort_order': 2},
        {'code': 'advanced', 'label': 'Advanced', 'sort_order': 3},
        {'code': 'all_levels', 'label': 'All Levels', 'sort_order': 4}
    ]
    for level_data in course_levels:
        if not db_session.query(CourseLevel).filter_by(code=level_data['code']).first():
            db_session.add(CourseLevel(**level_data))

    # Certification Levels
    cert_levels = [
        {'code': 'RYT-200', 'label': 'RYT-200', 'hours_required': 200},
        {'code': 'RYT-500', 'label': 'RYT-500', 'hours_required': 500},
        {'code': 'E-RYT-200', 'label': 'E-RYT-200', 'hours_required': 200},
        {'code': 'E-RYT-500', 'label': 'E-RYT-500', 'hours_required': 500},
        {'code': 'YACEP', 'label': 'YACEP', 'description': 'Yoga Alliance Continuing Education Provider'},
        {'code': 'other', 'label': 'Other', 'description': 'Other certification not listed'}
    ]
    for cert_data in cert_levels:
        if not db_session.query(CertificationLevel).filter_by(code=cert_data['code']).first():
            db_session.add(CertificationLevel(**cert_data))

    # Course Statuses
    course_statuses = [
        {'code': 'draft', 'label': 'Draft', 'description': 'Course is being prepared and not yet published'},
        {'code': 'published', 'label': 'Published', 'description': 'Course is live and accepting registrations'},
        {'code': 'full', 'label': 'Full', 'description': 'Course has reached maximum capacity'},
        {'code': 'cancelled', 'label': 'Cancelled', 'description': 'Course has been cancelled'},
        {'code': 'completed', 'label': 'Completed', 'description': 'Course has finished'},
        {'code': 'postponed', 'label': 'Postponed', 'description': 'Course has been postponed to a later date'}
    ]
    for status_data in course_statuses:
        if not db_session.query(CourseStatus).filter_by(code=status_data['code']).first():
            db_session.add(CourseStatus(**status_data))

    # Registration Statuses
    registration_statuses = [
        {'code': 'pending', 'label': 'Pending', 'description': 'Registration submitted but not yet confirmed'},
        {'code': 'confirmed', 'label': 'Confirmed', 'description': 'Registration is confirmed and active'},
        {'code': 'cancelled', 'label': 'Cancelled', 'description': 'Registration has been cancelled'},
        {'code': 'completed', 'label': 'Completed', 'description': 'Student has completed the course'},
        {'code': 'waitlisted', 'label': 'Waitlisted', 'description': 'Student is on waiting list'},
        {'code': 'no_show', 'label': 'No Show', 'description': 'Student did not attend the course'}
    ]
    for reg_status_data in registration_statuses:
        if not db_session.query(RegistrationStatus).filter_by(code=reg_status_data['code']).first():
            db_session.add(RegistrationStatus(**reg_status_data))

    # Payment Statuses
    payment_statuses = [
        {'code': 'pending', 'label': 'Pending', 'description': 'Payment is pending or processing'},
        {'code': 'completed', 'label': 'Completed', 'description': 'Payment has been successfully processed'},
        {'code': 'failed', 'label': 'Failed', 'description': 'Payment processing failed'},
        {'code': 'refunded', 'label': 'Refunded', 'description': 'Payment has been refunded'},
        {'code': 'partial_refund', 'label': 'Partial Refund', 'description': 'Payment has been partially refunded'},
        {'code': 'cancelled', 'label': 'Cancelled', 'description': 'Payment was cancelled before processing'}
    ]
    for payment_status_data in payment_statuses:
        if not db_session.query(PaymentStatus).filter_by(code=payment_status_data['code']).first():
            db_session.add(PaymentStatus(**payment_status_data))

    # Payment Methods
    payment_methods = [
        {'code': 'cash', 'label': 'Cash', 'description': 'Cash payment in person'},
        {'code': 'bank_transfer', 'label': 'Bank Transfer', 'description': 'Direct bank transfer or NEFT/RTGS'},
        {'code': 'upi', 'label': 'UPI', 'description': 'Unified Payments Interface (PhonePe, GPay, etc.)'},
        {'code': 'credit_card', 'label': 'Credit Card', 'description': 'Credit card payment'},
        {'code': 'debit_card', 'label': 'Debit Card', 'description': 'Debit card payment'},
        {'code': 'net_banking', 'label': 'Net Banking', 'description': 'Online banking payment'},
        {'code': 'paytm', 'label': 'Paytm', 'description': 'Paytm wallet payment'},
        {'code': 'razorpay', 'label': 'Razorpay', 'description': 'Razorpay gateway payment'},
        {'code': 'paypal', 'label': 'PayPal', 'description': 'PayPal payment'},
        {'code': 'cheque', 'label': 'Cheque', 'description': 'Cheque payment'},
        {'code': 'other', 'label': 'Other', 'description': 'Other payment method'}
    ]
    for payment_method_data in payment_methods:
        if not db_session.query(PaymentMethod).filter_by(code=payment_method_data['code']).first():
            db_session.add(PaymentMethod(**payment_method_data))

    db_session.commit()
