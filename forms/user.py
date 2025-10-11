from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField, SelectField, FileField
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


class RegisterTOTPForm(FlaskForm):
    """Form to register TOTP 2FA."""

    token = StringField(
        "2FA Code",
        validators=[DataRequired(), Length(min=6, max=6)],
        description="Enter the 2FA code from your authenticator app"
    )
    submit = SubmitField("Enable 2FA")



def valid_countries():
    # Example list; in a real app, use a comprehensive list or a library
    return [
        ('IN', 'India'),
        ('US', 'United States'),
        ('GB', 'United Kingdom'),
        ('CA', 'Canada'),
        ('AU', 'Australia'),
        ('FR', 'France'),
        ('DE', 'Germany'),
        ('JP', 'Japan'),
        ('CN', 'China'),
    ]


class AddressForm(FlaskForm):
    """Form to create or update a user address."""

    id = HiddenField()
    user_id = HiddenField()

    line1 = StringField(
        "Address line 1",
        validators=[DataRequired(), Length(max=255)],
    )

    line2 = StringField(
        "Address line 2",
        validators=[Optional(), Length(max=255)],
    )

    city = StringField(
        "City",
        validators=[DataRequired(), Length(max=120)],
    )

    state = StringField(
        "State / Province",
        validators=[Optional(), Length(max=120)],
    )

    postal_code = StringField(
        "Postal code",
        validators=[DataRequired(), Length(max=20)],
    )

    country_iso2 = SelectField(
        "Country",
        validators=[DataRequired(), Length(min=2, max=2)],
        choices=valid_countries(),
        description="Select your country"
    )

    is_primary = BooleanField("Primary address")

    submit = SubmitField("Save address")



class AvatarUploadForm(FlaskForm):
    """Form to upload or change user avatar."""

    avatar = FileField(
        "Upload Avatar",
        validators=[DataRequired()],
        description="Choose an image file to upload as your avatar"
    )
    
    submit = SubmitField("Upload Avatar")