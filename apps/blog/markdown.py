
"""A small, safe Markdown subset renderer. No dependencies.

Everything is HTML-escaped first; only the constructs below ever produce tags:
##/### headings, paragraphs, -/* and 1. lists, > quotes,
| Markdown tables, ``` fenced code, `code`, **bold**, *italic*,
[text](url).
"""

import re

from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify


_CODE = re.compile(r'`([^`\n]+)`')
_BOLD = re.compile(r'\*\*(.+?)\*\*')
_ITAL = re.compile(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])')
_LINK = re.compile(r'\[([^\]\n]+)\]\(([^)\s]+)\)')
_HEAD = re.compile(r'^(#{2,3})\s+(.+?)\s*#*$')
_UL = re.compile(r'^\s*[-*]\s+(.*)$')
_OL = re.compile(r'^\s*\d+[.)]\s+(.*)$')

# Markdown table separator, e.g. |---|---| or |:---|---:|
_TABLE_SEP = re.compile(
    r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$'
)


def _table_cells(line):
    """Convert a Markdown table row into individual cells."""
    line = line.strip()

    if line.startswith('|'):
        line = line[1:]

    if line.endswith('|'):
        line = line[:-1]

    return [cell.strip() for cell in line.split('|')]


def _is_table_start(lines, index):
    """Check whether the current line starts a Markdown table."""
    return (
        index + 1 < len(lines)
        and '|' in lines[index]
        and bool(_TABLE_SEP.match(lines[index + 1]))
    )


def _safe_url(url):
    """url arrives HTML-escaped. Allow only http(s), mailto and relative targets."""
    u = url.strip()
    low = re.sub(r'[\s\x00-\x1f]', '', u).lower()

    if low.startswith(('http://', 'https://', 'mailto:')):
        return u

    if low.startswith(('/', '#', '?')) and not low.startswith('//'):
        return u

    if ':' not in low.split('/')[0] and not low.startswith('//'):
        return u

    return None


def _link(m):
    text, url = m.group(1), _safe_url(m.group(2))

    if url is None:
        return text

    external = url.lower().startswith(('http://', 'https://'))
    extra = ' rel="noopener noreferrer" target="_blank"' if external else ''

    return f'<a href="{url}"{extra}>{text}</a>'


def inline(text):
    """text is already escaped. Code spans are protected from the other rules."""
    stash = []

    def keep(m):
        stash.append(f'<code>{m.group(1)}</code>')
        return f'\x00{len(stash) - 1}\x00'

    text = _CODE.sub(keep, text)
    text = _LINK.sub(_link, text)
    text = _BOLD.sub(r'<strong>\1</strong>', text)
    text = _ITAL.sub(r'<em>\1</em>', text)

    return re.sub(
        r'\x00(\d+)\x00',
        lambda m: stash[int(m.group(1))],
        text
    )


def _parse(source):
    """Yield parsed Markdown blocks."""
    lines = (source or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')

    i, n = 0, len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        # Markdown table
        if _is_table_start(lines, i):
            headers = _table_cells(line)
            i += 2
            rows = []

            while i < n and lines[i].strip() and '|' in lines[i]:
                cells = _table_cells(lines[i])

                # Match every row's number of cells with header columns.
                cells = (cells + [''] * len(headers))[:len(headers)]

                rows.append(cells)
                i += 1

            yield ('table', headers, rows)
            continue

        # Fenced code block
        if line.strip().startswith('```'):
            lang = re.sub(
                r'[^a-zA-Z0-9_+-]',
                '',
                line.strip()[3:].strip()
            )[:20]

            i += 1
            buf = []

            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1

            i += 1
            yield ('code', lang, '\n'.join(buf))
            continue

        # Headings
        m = _HEAD.match(line)

        if m:
            yield ('h', len(m.group(1)), m.group(2))
            i += 1
            continue

        # Blockquotes
        if line.lstrip().startswith('>'):
            buf = []

            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(lines[i].lstrip()[1:].lstrip())
                i += 1

            yield ('quote', ' '.join(buf))
            continue

        # Unordered and ordered lists
        for kind, rx in (('ul', _UL), ('ol', _OL)):
            if rx.match(line):
                items = []

                while i < n and rx.match(lines[i]):
                    items.append(rx.match(lines[i]).group(1))    # type: ignore
                    i += 1

                yield (kind, items)
                break

        else:
            # Paragraphs
            buf = []

            while i < n and lines[i].strip() and not (
                lines[i].strip().startswith('```')
                or _HEAD.match(lines[i])
                or lines[i].lstrip().startswith('>')
                or _UL.match(lines[i])
                or _OL.match(lines[i])
                or _is_table_start(lines, i)
            ):
                buf.append(lines[i].strip())
                i += 1

            yield ('p', ' '.join(buf))


def _plain(text):
    return re.sub(
        r'[`*]|\[([^\]]*)\]\([^)]*\)',
        lambda m: m.group(1) or '',
        text
    )


def _unique_id(text, seen):
    base = slugify(_plain(text))[:60] or 'section'
    slug, n = base, 2

    while slug in seen:
        slug = f'{base}-{n}'
        n += 1

    seen.add(slug)
    return slug


def render(source):
    out, seen = [], set()

    for b in _parse(source):
        kind = b[0]

        if kind == 'h':
            sid = _unique_id(b[2], seen)   # pyright: ignore[reportGeneralTypeIssues]
            out.append(
                f'<h{b[1]} id="{sid}">'
                f'{inline(escape(b[2]))}'  # pyright: ignore[reportGeneralTypeIssues]
                f'</h{b[1]}>'
            )

        elif kind == 'p':
            out.append(f'<p>{inline(escape(b[1]))}</p>')

        elif kind in ('ul', 'ol'):
            out.append(
                f'<{kind}>'
                + ''.join(
                    f'<li>{inline(escape(x))}</li>'
                    for x in b[1] # pyright: ignore[reportGeneralTypeIssues]
                )
                + f'</{kind}>'
            )

        elif kind == 'quote':
            out.append(
                f'<blockquote><p>{inline(escape(b[1]))}</p></blockquote>'
            )

        elif kind == 'table':
            headers, rows = b[1], b[2] # pyright: ignore[reportGeneralTypeIssues]

            thead = '<thead><tr>' + ''.join(
                f'<th scope="col">{inline(escape(cell))}</th>'
                for cell in headers # pyright: ignore[reportGeneralTypeIssues]
            ) + '</tr></thead>'

            tbody = '<tbody>' + ''.join(
                '<tr>' + ''.join(
                    f'<td>{inline(escape(cell))}</td>'
                    for cell in row # pyright: ignore[reportGeneralTypeIssues]
                ) + '</tr>'
                for row in rows # pyright: ignore[reportGeneralTypeIssues]
            ) + '</tbody>'

            out.append(
                '<div class="md-table-wrap">'
                '<table class="md-table">'
                f'{thead}{tbody}'
                '</table></div>'
            )

        elif kind == 'code':
            cls = f' class="lang-{b[1]}"' if b[1] else ''

            out.append(
                f'<pre><code{cls}>{escape(b[2])}</code></pre>'  # pyright: ignore[reportGeneralTypeIssues]
            )

    return mark_safe('\n'.join(out))


def toc(source):
    seen, items = set(), []

    for b in _parse(source):
        if b[0] == 'h':
            items.append((
                _unique_id(b[2], seen),   # pyright: ignore[reportGeneralTypeIssues]
                _plain(b[2]),  # pyright: ignore[reportGeneralTypeIssues]
                b[1]
            ))

    return items
