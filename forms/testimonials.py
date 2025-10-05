from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    HiddenField,
    SelectField,
    BooleanField,
    SubmitField,
    FieldList,
    FormField,
)
from wtforms.validators import DataRequired, Length, Optional, URL
from flask_wtf.file import MultipleFileField, FileAllowed


# class TestimonialMetaForm(FlaskForm):
#     """Nested form for the testimonial.meta JSONB field (locale, photos, context)."""

#     locale = StringField(
#         "Locale",
#         validators=[Optional(), Length(max=20)],
#         description="Locale (e.g. en-US).",
#     )

#     # Allow a small list of photo URLs. Templates can render add/remove controls.
#     photos = FieldList(
#         StringField("Photo URL", validators=[Optional(), URL(), Length(max=2000)]),
#         min_entries=0,
#         max_entries=8,
#         description="List of photo URLs related to the testimonial.",
#     )

#     context = TextAreaField(
#         "Context",
#         validators=[Optional(), Length(max=2000)],
#         description="Optional context for the testimonial (e.g. after finishing a program).",
#     )


class TestimonialForm(FlaskForm):
    """Form to create or edit a Testimonial.

    Mirrors the important public fields from the Testimonial model and
    embeds TestimonialMetaForm for structured meta data.
    """

    # For edits; leave empty for new testimonials
    id = HiddenField()

    # References (backend should ensure school_id is provided)
    user_id = HiddenField(description="User id submitting the testimonial")
    school_id = HiddenField(validators=[DataRequired()], description="Target school id")
    course_id = HiddenField(description="Optional course id")

    # Content
    title = StringField(
        "Title",
        validators=[DataRequired(message="Title is required."), Length(max=200)],
    )

    description = TextAreaField(
        "Testimonial",
        validators=[DataRequired(message="Please enter the testimonial text."), Length(max=10000)],
        description="Tell others about your experience.",
    )

    # Rating 1..5 (use SelectField for nicer UI)
    rating = SelectField(
        "Rating",
        choices=[("5", "5"), ("4", "4"), ("3", "3"), ("2", "2"), ("1", "1")],
        default="5",
        validators=[DataRequired()],
        description="Rate your experience from 1 (worst) to 5 (best).",
    )

    # Publishing controls (may be ignored for public submissions)
    is_published = BooleanField("Publish immediately", default=False)

    # Meta subform with locale/photos/context
    # meta = FormField(TestimonialMetaForm)

    # Allow uploading multiple images optionally
    photos_upload = MultipleFileField(
        "Upload Photos",
        validators=[
            Optional(),
            FileAllowed({"png", "jpg", "jpeg", "gif"}, "Images only"),
        ],
        description="Upload one or more images (optional).",
    )

    submit = SubmitField("Submit Testimonial")
