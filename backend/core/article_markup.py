"""Serialize the small set of formatting available in the article editor."""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit


class ArticleMarkup(HTMLParser):
    tags = set("p br div h2 h3 h4 strong b em i ul ol li blockquote a hr details summary table thead tbody tr th td".split())
    void = {"br", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.text = []
        self.stack = []
        self.raw_tag = None

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.raw_tag = tag
        if self.raw_tag or tag not in self.tags:
            return
        attribute = ""
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if self.safe_href(href):
                attribute = f' href="{escape(href, quote=True)}"'
        self.parts.append(f"<{tag}{attribute}>")
        if tag not in self.void:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == self.raw_tag:
            self.raw_tag = None
            return
        if tag not in self.stack:
            return
        while self.stack:
            current = self.stack.pop()
            self.parts.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data):
        if self.raw_tag:
            return
        self.text.append(data)
        self.parts.append(escape(data, quote=False))

    @staticmethod
    def safe_href(value):
        if not value or value != value.strip() or any(ord(c) < 32 or c == chr(92) for c in value):
            return False
        try:
            url = urlsplit(value)
        except ValueError:
            return False
        if value.startswith(("#", "/")) and not value.startswith("//"):
            return not url.netloc
        return url.scheme in {"https", "http"} and bool(url.hostname)

    def result(self):
        self.close()
        while self.stack:
            self.parts.append(f"</{self.stack.pop()}>")
        return "".join(self.parts).strip() if "".join(self.text).strip() else ""


def sanitize_article(value):
    parser = ArticleMarkup()
    parser.feed(value)
    return parser.result()
