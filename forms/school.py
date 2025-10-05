# forms/school.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, Email, URL, Regexp


class SchoolRegisterForm(FlaskForm):
    name = StringField("School Name", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=5000)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20),
                                             Regexp(r"^[0-9+\- ()]*$", message="Invalid phone")])
    website = StringField("Website", validators=[Optional(), URL(), Length(max=255)])
    registration_number = StringField("Registration Number", validators=[Optional(), Length(max=100)])
    certification_body = StringField("Certification Body", validators=[Optional(), Length(max=255)])
