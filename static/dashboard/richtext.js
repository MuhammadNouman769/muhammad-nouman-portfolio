/* Built-in rich text editor for the dashboard (no external libraries).
   - toolbar: text / heading / subheading, bold, italic, underline, lists, quote, link, clear, undo, redo
   - pasting text is understood automatically: paragraphs, "# heading", "- bullet", "1. number", **bold**
   - pasting from Word / web pages keeps headings, bold, lists and links, drops everything else */
(function () {
  'use strict';
  var ALLOWED = { P: 1, BR: 1, H2: 1, H3: 1, H4: 1, STRONG: 1, EM: 1, U: 1, UL: 1, OL: 1, LI: 1, BLOCKQUOTE: 1, A: 1, HR: 1 };
  var RENAME = { B: 'STRONG', I: 'EM', H1: 'H2', H5: 'H4', H6: 'H4', DIV: 'P' };
  var DROP = { SCRIPT: 1, STYLE: 1, IFRAME: 1, OBJECT: 1, EMBED: 1, NOSCRIPT: 1, META: 1, LINK: 1, HEAD: 1, TITLE: 1 };

  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function inline(s) {
    s = esc(s);
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em>$2</em>');
    return s;
  }

  function plainToHtml(text) {
    var out = [], para = [], kind = null;
    function flushPara() { if (para.length) { out.push('<p>' + para.map(inline).join('<br>') + '</p>'); para = []; } }
    function closeList() { if (kind) { out.push('</' + kind + '>'); kind = null; } }
    text.replace(/\r\n?/g, '\n').split('\n').forEach(function (raw) {
      var line = raw.trim(), m, n;
      if (!line) { flushPara(); closeList(); return; }
      if ((m = line.match(/^(#{1,3})\s+(.+)$/))) {
        flushPara(); closeList();
        var t = { 1: 'h2', 2: 'h3', 3: 'h4' }[m[1].length];
        out.push('<' + t + '>' + inline(m[2]) + '</' + t + '>'); return;
      }
      m = line.match(/^[-*\u2022]\s+(.+)$/); n = line.match(/^\d+[.)]\s+(.+)$/);
      if (m || n) {
        flushPara();
        var want = m ? 'ul' : 'ol';
        if (kind !== want) { closeList(); out.push('<' + want + '>'); kind = want; }
        out.push('<li>' + inline((m || n)[1]) + '</li>'); return;
      }
      if ((m = line.match(/^>\s?(.+)$/))) { flushPara(); closeList(); out.push('<blockquote><p>' + inline(m[1]) + '</p></blockquote>'); return; }
      closeList(); para.push(line);
    });
    flushPara(); closeList();
    return out.join('');
  }

  function clean(node) {
    var out = '';
    node.childNodes.forEach(function (n) {
      if (n.nodeType === 3) { out += esc(n.nodeValue); return; }
      if (n.nodeType !== 1) return;
      var tag = n.tagName; if (DROP[tag]) return;
      tag = RENAME[tag] || tag;
      var inner = clean(n);
      if (!ALLOWED[tag]) { out += inner; return; }
      if (tag === 'BR' || tag === 'HR') { out += '<' + tag.toLowerCase() + '>'; return; }
      if (tag === 'A') {
        var h = (n.getAttribute('href') || '').trim();
        out += /^(https?:|mailto:|tel:|\/|#)/i.test(h) ? '<a href="' + h.replace(/"/g, '&quot;') + '">' + inner + '</a>' : inner;
        return;
      }
      var t = tag.toLowerCase(); out += '<' + t + '>' + inner + '</' + t + '>';
    });
    return out;
  }

  function init(root) {
    var area = root.querySelector('.rte-area'), src = root.querySelector('.rte-src'), bar = root.querySelector('.rte-bar');
    if (!area || !src) return;
    root.classList.add('rte-on');
    try { document.execCommand('defaultParagraphSeparator', false, 'p'); } catch (e) {}

    function sync() {
      var empty = !area.textContent.trim() && !area.querySelector('hr');
      area.classList.toggle('rte-empty', empty);
      src.value = empty ? '' : area.innerHTML;
    }
    function block(tag) {
      var v = (document.queryCommandValue('formatBlock') || '').toLowerCase().replace(/[<>]/g, '');
      document.execCommand('formatBlock', false, v === tag ? 'p' : tag);
    }
    function link() {
      var url = window.prompt('Link address (for example https://example.com)');
      if (!url) return;
      url = url.trim();
      if (!/^(https?:|mailto:|tel:|\/|#)/i.test(url)) url = 'https://' + url;
      document.execCommand('createLink', false, url);
    }
    var cmds = {
      p: function () { document.execCommand('formatBlock', false, 'p'); },
      h2: function () { block('h2'); }, h3: function () { block('h3'); },
      bold: function () { document.execCommand('bold'); }, italic: function () { document.execCommand('italic'); },
      underline: function () { document.execCommand('underline'); },
      ul: function () { document.execCommand('insertUnorderedList'); }, ol: function () { document.execCommand('insertOrderedList'); },
      quote: function () { block('blockquote'); }, link: link, unlink: function () { document.execCommand('unlink'); },
      clear: function () { document.execCommand('removeFormat'); document.execCommand('unlink'); document.execCommand('formatBlock', false, 'p'); },
      undo: function () { document.execCommand('undo'); }, redo: function () { document.execCommand('redo'); }
    };
    function refresh() {
      if (document.activeElement !== area) return;
      var v = (document.queryCommandValue('formatBlock') || '').toLowerCase().replace(/[<>]/g, '');
      bar.querySelectorAll('.rte-btn').forEach(function (b) {
        var c = b.dataset.cmd, on = false;
        try {
          if (c === 'bold' || c === 'italic' || c === 'underline') on = document.queryCommandState(c);
          else if (c === 'ul') on = document.queryCommandState('insertUnorderedList');
          else if (c === 'ol') on = document.queryCommandState('insertOrderedList');
          else if (c === 'h2' || c === 'h3') on = v === c;
          else if (c === 'quote') on = v === 'blockquote';
          else if (c === 'p') on = v === 'p';
        } catch (e) {}
        b.classList.toggle('on', !!on);
      });
    }

    bar.addEventListener('mousedown', function (e) { if (e.target.closest('.rte-btn')) e.preventDefault(); });
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('.rte-btn'); if (!b || !cmds[b.dataset.cmd]) return;
      area.focus(); cmds[b.dataset.cmd](); sync(); refresh();
    });
    area.addEventListener('input', sync);
    area.addEventListener('keyup', refresh);
    area.addEventListener('mouseup', refresh);
    area.addEventListener('focus', function () { if (!area.textContent.trim() && !area.querySelector('p,h2,h3,h4,ul,ol,blockquote')) area.innerHTML = '<p><br></p>'; });
    area.addEventListener('blur', sync);
    document.addEventListener('selectionchange', refresh);
    area.addEventListener('paste', function (e) {
      var cd = e.clipboardData; if (!cd) return;
      e.preventDefault();
      var html = cd.getData('text/html'), text = cd.getData('text/plain'), out = '';
      if (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        // plain-text editors put text in <div>/<span> only: treat that as plain text so # - 1. ** are understood
        if (doc.body.querySelector('h1,h2,h3,h4,h5,h6,ul,ol,li,strong,b,em,i,u,a,blockquote')) out = clean(doc.body);
      }
      if (!out.trim()) out = plainToHtml(text || '');
      document.execCommand('insertHTML', false, out);
      sync();
    });
    var form = root.closest('form');
    if (form) form.addEventListener('submit', sync);
    sync();
  }

  function boot() { document.querySelectorAll('[data-rte]').forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
