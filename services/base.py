from utilities.navbar_loader import get_navbar_context
from utilities.about_loader import get_about_context
from flask import request, url_for, render_template


def _invert_navbar_colors(context):
    v = "relative inline-flex items-center gap-2 px-2.5 py-2 text-sm font-medium text-black/90 list-none cursor-pointer transition-colors duration-300 ease-out hover:text-[#0c5741] after:absolute after:left-0 after:bottom-0 after:h-[2px] after:w-0 after:bg-[#0c5741] after:transition-all after:duration-300 after:ease-out hover:after:w-full"
    context['navbar_config']['styles']['desktop']['simple_link'] = v
    context['navbar_config']['styles']['desktop']['auth_link'] = v
    context['navbar_config']['styles']['desktop']['mega_menu_summary'] = v
    context['navbar_config']['styles']['brand']['logo'] = '"h-8 w-8 brightness-0"'
    context['navbar_config']['styles']['brand']['text'] = '"font-bold text-lg truncate text-black"'
    return context


def _context():
    return dict(
        page_title="Yoga Teacher Training – Bodhgriha",
        page_description="Discover certified yoga teacher training programs across India. Compare curricula, dates, and prices.",
        canonical_url=request.base_url,
        og_image=url_for("static", filename="images/og-default.jpg", _external=True),
        twitter_site="@bodhgriha",
        theme_color="#0ea5e9",
        # search_url=url_for("search"),
        use_hyperscript=False,
        robots="index, follow",
        tailwind_config={
            "theme": {
                "extend": {
                    "colors": {"brand": {"DEFAULT": "#0ea5e9", "dark": "#0369a1"}}
                }
            }
        },
        brand_primary="#0c5741",
        **get_navbar_context(),
        **get_about_context()
    )
