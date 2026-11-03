"""A small, safe Markdown subset renderer. No dependencies.

Everything is HTML-escaped first; only the constructs below ever produce tags:
##/### headings, paragraphs, -/* and 1. lists, > quotes, ``` fenced code, `code`, **bold**, *italic*, [text](url).
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
    return re.sub(r'\x00(\d+)\x00', lambda m: stash[int(m.group(1))], text)


def _parse(source):
    """Yield blocks: ('h', level, text) ('p', text) ('ul'|'ol', [items]) ('quote', text) ('code', lang, text)."""
    lines = (source or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith('```'):
            lang = re.sub(r'[^a-zA-Z0-9_+-]', '', line.strip()[3:].strip())[:20]
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            yield ('code', lang, '\n'.join(buf))
            continue
        m = _HEAD.match(line)
        if m:
            yield ('h', len(m.group(1)), m.group(2))
            i += 1
            continue
        if line.lstrip().startswith('>'):
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(lines[i].lstrip()[1:].lstrip())
                i += 1
            yield ('quote', ' '.join(buf))
            continue
        for kind, rx in (('ul', _UL), ('ol', _OL)):
            if rx.match(line):
                items = []
                while i < n and rx.match(lines[i]):
                    items.append(rx.match(lines[i]).group(1))
                    i += 1
                yield (kind, items)
                break
        else:
            buf = []
            while i < n and lines[i].strip() and not (
                    lines[i].strip().startswith('```') or _HEAD.match(lines[i]) or lines[i].lstrip().startswith('>')
                    or _UL.match(lines[i]) or _OL.match(lines[i])):
                buf.append(lines[i].strip())
                i += 1
            yield ('p', ' '.join(buf))


def _plain(text):
    return re.sub(r'[`*]|\[([^\]]*)\]\([^)]*\)', lambda m: m.group(1) or '', text)


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
            sid = _unique_id(b[2], seen)
            out.append(f'<h{b[1]} id="{sid}">{inline(escape(b[2]))}</h{b[1]}>')
        elif kind == 'p':
            out.append(f'<p>{inline(escape(b[1]))}</p>')
        elif kind in ('ul', 'ol'):
            out.append(f'<{kind}>' + ''.join(f'<li>{inline(escape(x))}</li>' for x in b[1]) + f'</{kind}>')
        elif kind == 'quote':
            out.append(f'<blockquote><p>{inline(escape(b[1]))}</p></blockquote>')
        elif kind == 'code':
            cls = f' class="lang-{b[1]}"' if b[1] else ''
            out.append(f'<pre><code{cls}>{escape(b[2])}</code></pre>')
    return mark_safe('\n'.join(out))


def toc(source):
    seen, items = set(), []
    for b in _parse(source):
        if b[0] == 'h':
            items.append((_unique_id(b[2], seen), _plain(b[2]), b[1]))
    return items
