from __future__ import annotations

import html
import re
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        elif tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "td"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value)
    text = html.unescape("".join(parser.parts)).replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_div(html_text: str, class_name: str) -> str:
    match = re.search(
        rf'<div\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>(.*?)</div>\s*</div>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else ""


def meta_content(html_text: str, name: str) -> str:
    match = re.search(
        rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'](.*?)["\']\s*/?>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html.unescape(match.group(1)).strip() if match else ""
