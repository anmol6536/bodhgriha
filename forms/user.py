from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional


class UserForm(FlaskForm):
    """Form for creating or updating a user."""

    id = HiddenField()  # for editing existing users

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Invalid email format."),
            Length(max=255),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            Optional(),  # optional on edit
            Length(min=8, message="Password must be at least 8 characters."),
        ],
    )

    first_name = StringField(
        "First Name",
        validators=[DataRequired(), Length(max=200)],
    )

    last_name = StringField(
        "Last Name",
        validators=[DataRequired(), Length(max=200)],
    )

    is_active = BooleanField("Active", default=True)

    submit = SubmitField("Save")


class SignupForm(FlaskForm):
    """Form for public user signup."""
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Invalid email format."),
            Length(max=255),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            Optional(),  # optional on edit
            Length(min=8, message="Password must be at least 8 characters."),
        ],
    )

    first_name = StringField(
        "First Name",
        validators=[DataRequired(), Length(max=200)],
    )

    last_name = StringField(
        "Last Name",
        validators=[DataRequired(), Length(max=200)],
    )

    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=4)],
    )
    remember_me = BooleanField("Remember Me", default=False)

    # totp
    totp_code = StringField(
        "2FA Code (if enabled)",
        validators=[Optional(), Length(min=6, max=6)],
        description="Enter your 2FA code"
    )

    submit = SubmitField("Log In")


class ForgotPasswordForm(FlaskForm):
    """Request a password reset link by email."""
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    submit = SubmitField("Send Reset Link")
