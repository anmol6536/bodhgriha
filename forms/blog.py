from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp
from flask_wtf.file import FileField, FileRequired, FileAllowed

MD_EXTENSIONS = {"md", "markdown", "mdown", "mkd", "mkdown"}


class BlogUploadForm(FlaskForm):
    """Upload a Markdown file for a blog post (front-matter supported)."""

    md_file = FileField(
        "Markdown File",
        validators=[
            FileRequired(message="Please choose a Markdown file."),
            FileAllowed(MD_EXTENSIONS, "Markdown files only (.md, .markdown)."),
        ],
        description="Upload a .md file with optional YAML front matter."
    )

    publish = BooleanField("Publish immediately", default=False)

    submit = SubmitField("Upload")
