from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import select
from werkzeug.utils import secure_filename
import os
import uuid

from core.db import uow
from forms.testimonials import TestimonialForm
from models.sql.testimonials import Testimonial
from models.sql.base import RoleBits
from utilities.decorators import role_validation
from services.base import _context, _invert_navbar_colors

bp = Blueprint("search", __name__, url_prefix="/search")


class Listing:
    """
    {# listing = {
    "href": "/retreats/slug-or-id",
    "title": "4 Day Refreshing Yoga Retreat with Meditation and Guided Walks in Alicante, Costa Blanca, Spain",
    "image_url": "https://…/cover.jpg",
    "image_alt": "Retreat group practicing yoga outdoors",
    "country": "Spain",
    "country_flag_emoji": "🇪🇸",
    "city": "Alicante",
    "region": "Costa Blanca",
    "duration_days": 4,
    "persons": 1,
    "available_all_year": true,
    "perks": ["Airport transfer included","All meals included","Vegetarian friendly","Instructed in English"],
    "interested_count": 28,
    "rating_value": 4.5,
    "rating_count": 610,
    "price_from": 563.0,
    "currency": "USD"
    } #}
    """
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.title = kwargs.get("title")
        self.snippet = kwargs.get("snippet")
        self.href = kwargs.get("href", "#")
        self.image_url = kwargs.get("image_url", "https://via.placeholder.com/400x300")
        self.image_alt = kwargs.get("image_alt", "Listing Image")
        self.country = kwargs.get("country", "Country")
        self.country_flag_emoji = kwargs.get("country_flag_emoji", "🏳️")
        self.city = kwargs.get("city", "City")
        self.region = kwargs.get("region", "Region")
        self.duration_days = kwargs.get("duration_days", 1)
        self.persons = kwargs.get("persons", 1)
        self.available_all_year = kwargs.get("available_all_year", True)
        self.perks = kwargs.get("perks", [])
        self.interested_count = kwargs.get("interested_count", 0)
        self.rating_value = kwargs.get("rating_value", 0.0)
        self.rating_count = kwargs.get("rating_count", 0)
        self.price_from = kwargs.get("price_from", 0.0)
        self.currency = kwargs.get("currency", "USD")


@bp.route("/", methods=["GET"])
def search_listings():

    # Dummy data for listings
    listings = [
        Listing(
            id=1,
            title="4 Day Refreshing Yoga Retreat with Meditation and Guided Walks in Alicante, Costa Blanca, Spain",
            snippet="Experience a rejuvenating 4-day yoga retreat in the serene landscapes of Alicante, Costa Blanca. Enjoy daily yoga sessions, meditation practices, and guided nature walks. Perfect for all levels.",
            href="/retreats/1",
            image_url=url_for('static', filename='images/blog/2.jpeg'),
            image_alt="Retreat group practicing yoga outdoors",
            country="Spain",
            country_flag_emoji="🇪🇸",
            city="Alicante",
            region="Costa Blanca",
            duration_days=4,
            persons=1,
            available_all_year=True,
            perks=["Airport transfer included", "All meals included", "Vegetarian friendly", "Instructed in English"],
            interested_count=28,
            rating_value=4.5,
            rating_count=610,
            price_from=563.0,
            currency="$ USD"
        ),
        Listing(
            id=2,
            title="7 Day Yoga and Wellness Retreat in Bali, Indonesia",
            snippet="Join us for a transformative 7-day yoga and wellness retreat in the heart of Bali. Immerse yourself in daily yoga practices, holistic wellness workshops, and explore the vibrant culture of Bali.",
            href="/retreats/2",
            image_url=url_for('static', filename='images/blog/1.jpeg'),
            image_alt="Yoga session at a beachside retreat",
            country="Indonesia",
            country_flag_emoji="🇮🇩",
            city="Ubud",
            region="Bali",
            duration_days=7,
            persons=1,
            available_all_year=False,
            perks=["Airport transfer included", "All meals included", "Vegan options available", "Instructed in English"],
            interested_count=45,
            rating_value=4.8,
            rating_count=890,
            price_from=1200.0,
            currency="$ USD"
        )
    ]
    return render_template("search/index.html", listings=listings, **_invert_navbar_colors(_context()), query="yoga retreat")
