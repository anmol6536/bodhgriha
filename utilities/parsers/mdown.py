import yaml
import bleach
import markdown
import re
from bleach.callbacks import nofollow
from bs4 import BeautifulSoup


FRONT = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_markdown(md: str) -> tuple[dict, str, str]:
    ALLOWED_TAGS = [
        "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li", "strong", "em", "b", "i", "blockquote", "code", "pre",
        "span", "a", "img"
    ]
    ALLOWED_ATTRS = {
        # allow classes on headings/typography
        **{t: ["class"] for t in
           ["p", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "b", "i", "code", "pre", "span"]},
        "a": ["href", "title", "rel", "target", "class"],
        "img": ["src", "alt", "title", "width", "height", "loading", "class"],
    }

    meta = {}
    m = FRONT.match(md)
    body = md
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        body = md[m.end():]

    raw_html = markdown.markdown(body, extensions=["extra", "sane_lists", "codehilite", "attr_list"])
    clean_html = bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True,
                              protocols=["http", "https", "mailto"], )  # same as above
    clean_html = bleach.linkify(clean_html, callbacks=[nofollow])
    soup = BeautifulSoup(clean_html, "html.parser")
    pretty_html = soup.prettify()
    plain_text = bleach.clean(raw_html, tags=[], strip=True)

    return meta, pretty_html,  plain_text
