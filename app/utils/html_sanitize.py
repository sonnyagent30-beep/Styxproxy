"""HTML sanitization for inbound email content.

Uses only Python stdlib (html.parser) — no external dependencies.
Strips dangerous tags, event handlers, and javascript: URLs while
preserving safe HTML formatting for the admin support inbox.
"""
import re
from html import escape
from html.parser import HTMLParser


# Tags that are safe to preserve in email HTML
ALLOWED_TAGS: frozenset[str] = frozenset({
    'p', 'br', 'hr', 'div', 'span',
    'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'ins',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
    'a', 'img',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'caption',
    'font', 'center', 'small', 'sub', 'sup',
})

# Attributes that are safe to preserve
ALLOWED_ATTRS: frozenset[str] = frozenset({
    'href', 'src', 'alt', 'title', 'width', 'height',
    'style', 'class', 'id', 'colspan', 'rowspan',
    'align', 'valign', 'bgcolor', 'color', 'face', 'size',
    'border', 'cellpadding', 'cellspacing',
    'target', 'rel',
})

# Tags whose content should be entirely removed (not just the tags)
DROP_CONTENT_TAGS: frozenset[str] = frozenset({
    'script', 'style', 'iframe', 'object', 'embed', 'applet',
    'form', 'input', 'button', 'select', 'textarea', 'option',
    'link', 'meta', 'base', 'head', 'title',
    'svg', 'math', 'template', 'noscript',
})

# Attribute prefixes that are always dangerous
DANGEROUS_ATTR_RE = re.compile(r'^on', re.IGNORECASE)

# Dangerous URL protocols
DANGEROUS_PROTOCOL_RE = re.compile(
    r'^\s*(javascript|vbscript|data|file)\s*:', re.IGNORECASE
)


class _SanitizerParser(HTMLParser):
    """HTML parser that strips dangerous content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._output: list[str] = []
        self._drop_depth: int = 0  # nesting depth inside a dropped tag

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()

        # If we're inside a dropped tag, increment depth and skip
        if self._drop_depth > 0:
            if tag_lower in DROP_CONTENT_TAGS:
                self._drop_depth += 1
            return

        # Drop dangerous tags entirely (including their content)
        if tag_lower in DROP_CONTENT_TAGS:
            self._drop_depth = 1
            return

        # Skip disallowed tags but keep their content
        if tag_lower not in ALLOWED_TAGS:
            return

        # Build safe attribute string
        clean_attrs: list[str] = []
        for name, value in attrs:
            name_lower = name.lower()

            # Skip event handlers and dangerous attributes
            if DANGEROUS_ATTR_RE.match(name_lower):
                continue
            if name_lower not in ALLOWED_ATTRS:
                continue

            # Skip dangerous URL protocols
            if value and DANGEROUS_PROTOCOL_RE.match(value):
                continue

            # Escape attribute value
            if value is None:
                clean_attrs.append(name_lower)
            else:
                clean_attrs.append(f'{name_lower}="{escape(value, quote=True)}"')

        attr_str = (' ' + ' '.join(clean_attrs)) if clean_attrs else ''
        self._output.append(f'<{tag_lower}{attr_str}>')

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        # If we're inside a dropped tag
        if self._drop_depth > 0:
            if tag_lower in DROP_CONTENT_TAGS:
                self._drop_depth -= 1
            return

        # Skip disallowed tags
        if tag_lower not in ALLOWED_TAGS:
            return

        self._output.append(f'</{tag_lower}>')

    def handle_data(self, data: str) -> None:
        if self._drop_depth == 0:
            self._output.append(escape(data))

    def handle_entityref(self, name: str) -> None:
        if self._drop_depth == 0:
            self._output.append(f'&{name};')

    def handle_charref(self, name: str) -> None:
        if self._drop_depth == 0:
            self._output.append(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        pass  # Strip HTML comments

    def handle_decl(self, decl: str) -> None:
        pass  # Strip DOCTYPE declarations

    def handle_pi(self, data: str) -> None:
        pass  # Strip processing instructions

    def get_output(self) -> str:
        return ''.join(self._output)


def sanitize_html(html: str) -> str:
    """Sanitize HTML to prevent XSS attacks.

    Removes dangerous tags (script, iframe, etc.), event handlers
    (onerror, onclick, etc.), and javascript: URLs while preserving
    safe HTML formatting.

    Args:
        html: Raw HTML string to sanitize.

    Returns:
        Sanitized HTML string safe for rendering in the admin inbox.
    """
    if not html:
        return ''

    parser = _SanitizerParser()
    parser.feed(html)
    result = parser.get_output()

    # Post-processing: remove any remaining dangerous patterns
    # (belt-and-suspenders for edge cases the parser might miss)
    result = re.sub(
        r'javascript\s*:', '', result, flags=re.IGNORECASE
    )
    result = re.sub(
        r'vbscript\s*:', '', result, flags=re.IGNORECASE
    )
    result = re.sub(
        r'expression\s*\(', '', result, flags=re.IGNORECASE
    )

    return result
