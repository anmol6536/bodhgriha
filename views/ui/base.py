from flask import Blueprint, Response, request, render_template

bp = Blueprint("ui", __name__, url_prefix="/ui")

# Mock testimonials data
TESTIMONIALS_DATA = {
    "eyebrow": "What Our Community Says",
    "heading": "Trusted by Yogis Worldwide",
    "subheading": "Join thousands of practitioners who have found their perfect yoga experience through Bodhgriha. From life-changing retreats to transformative teacher trainings, discover what makes our community special.",
    "cta": {
        "text": "Start Your Journey",
        "href": "/search"
    },
    "items": [
        {
            "quote": "My retreat in Rishikesh through Bodhgriha was absolutely transformative. The authentic teachings and serene environment helped me deepen my practice beyond what I thought possible.",
            "author": "Sarah Mitchell",
            "suffix": "200-Hour YTT Graduate"
        },
        {
            "quote": "Finding the right yoga teacher training was overwhelming until I discovered Bodhgriha. Their platform made it easy to compare programs and find one that truly aligned with my goals.",
            "author": "Michael Chen",
            "suffix": "Certified Yoga Instructor"
        },
        {
            "quote": "The Ashtanga workshop I booked exceeded all expectations. The instructor was incredibly knowledgeable, and the small group setting allowed for personalized attention I couldn't get elsewhere.",
            "author": "Elena Rodriguez",
            "suffix": "Advanced Practitioner"
        },
        {
            "quote": "Bodhgriha helped me discover yoga retreats I never knew existed. The detailed descriptions and honest reviews made choosing the perfect retreat effortless and exciting.",
            "author": "David Thompson",
            "suffix": "Yoga Enthusiast"
        },
        {
            "quote": "The meditation retreat in the Himalayas was life-changing. Bodhgriha's curation process ensured I found an authentic experience that honored traditional practices.",
            "author": "Priya Sharma",
            "suffix": "Mindfulness Coach"
        },
        {
            "quote": "As a beginner, I was nervous about joining a yoga retreat. Bodhgriha's detailed program information and supportive community made me feel confident and welcomed from day one.",
            "author": "James Wilson",
            "suffix": "New Practitioner"
        }
    ]
}

@bp.get("/testimonials")
def view():
    """Handle testimonials navigation and display"""
    # Get current index
    current_i = int(request.args.get('i', 0))
    
    # Handle navigation
    nav = request.args.get('nav')
    if nav == 'next':
        current_i = (current_i + 1) % len(TESTIMONIALS_DATA['items'])
    elif nav == 'prev':
        current_i = (current_i - 1) % len(TESTIMONIALS_DATA['items'])
    
    # Ensure index is within bounds
    current_i = max(0, min(current_i, len(TESTIMONIALS_DATA['items']) - 1))
    
    return render_template(
        'partials/testimonials.html',
        testimonials=TESTIMONIALS_DATA,
        i=current_i,
        brand="#0c5741"
    )

@bp.get("/empty")
def empty():
    # empty body so hx-swap="outerHTML" removes the target element
    return Response("", status=200)
