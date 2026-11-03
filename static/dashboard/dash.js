/* Dashboard behaviour: theme, menu, confirm dialog, charts, live feed, drag-to-reorder, inline rows. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var root = document.documentElement;
  function csrf() { var m = document.cookie.match(/csrftoken=([^;]+)/); return m ? m[1] : (($('input[name=csrfmiddlewaretoken]') || {}).value || ''); }

  /* theme + mobile menu */
  var tb = $('#dash-theme');
  if (tb) tb.addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') === 'dark' || (root.getAttribute('data-theme') === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark'; root.setAttribute('data-theme', next);
    try { localStorage.setItem('dash-theme', next); } catch (e) {}
    drawAll();
  });
  var mb = $('#menu-btn'), side = $('#side');
  if (mb) mb.addEventListener('click', function () { side.classList.toggle('open'); });
  document.addEventListener('click', function (e) { if (side && side.classList.contains('open') && !side.contains(e.target) && e.target !== mb && !mb.contains(e.target)) side.classList.remove('open'); });

  /* confirm dialog for destructive forms */
  var dlg = $('#confirm');
  $$('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (f.dataset.ok) return;
      e.preventDefault();
      $('#confirm-title').textContent = 'Are you sure?'; $('#confirm-text').textContent = f.dataset.confirm;
      dlg.returnValue = ''; dlg.showModal();
      dlg.addEventListener('close', function once() { dlg.removeEventListener('close', once); if (dlg.returnValue === 'ok') { f.dataset.ok = '1'; f.submit(); } });
    });
  });
  $$('tr.click').forEach(function (tr) { tr.addEventListener('click', function (e) { if (!e.target.closest('a,button')) location.href = tr.dataset.href; }); });

  /* ---------- charts ---------- */
  var NS = 'http://www.w3.org/2000/svg';
  function el(n, a, p) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; }
  function css(v) { return getComputedStyle(root).getPropertyValue(v).trim(); }
  function niceMax(m) { if (m <= 4) return 4; var p = Math.pow(10, Math.floor(Math.log10(m))); var n = m / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p; }
  function tipFor(box) { var t = box.querySelector('.tip'); if (!t) { t = document.createElement('div'); t.className = 'tip'; t.hidden = true; box.appendChild(t); } return t; }

  function lineChart(box, data) {
    box.innerHTML = '';
    var W = box.clientWidth, H = box.clientHeight, m = { l: 36, r: 12, t: 12, b: 26 };
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'none' }, box);
    var max = niceMax(Math.max.apply(null, data.map(function (d) { return Math.max(d.views, d.visitors); }).concat([1])));
    var x = function (i) { return m.l + (data.length < 2 ? 0 : i * (W - m.l - m.r) / (data.length - 1)); };
    var y = function (v) { return m.t + (H - m.t - m.b) * (1 - v / max); };
    for (var g = 0; g <= 4; g++) {
      var gy = y(max * g / 4); el('line', { x1: m.l, x2: W - m.r, y1: gy, y2: gy, class: 'grid-line' }, svg);
      var tx = el('text', { x: m.l - 8, y: gy + 4, 'text-anchor': 'end', class: 'tick' }, svg); tx.textContent = Math.round(max * g / 4);
    }
    var step = Math.ceil(data.length / 7);
    data.forEach(function (d, i) { if (i % step === 0 || i === data.length - 1) { var t = el('text', { x: x(i), y: H - 6, 'text-anchor': i === 0 ? 'start' : (i === data.length - 1 ? 'end' : 'middle'), class: 'tick' }, svg); t.textContent = d.label; } });
    var pts = function (k) { return data.map(function (d, i) { return x(i).toFixed(1) + ',' + y(d[k]).toFixed(1); }); };
    var p1 = pts('views'); el('polygon', { points: m.l + ',' + y(0) + ' ' + p1.join(' ') + ' ' + x(data.length - 1) + ',' + y(0), class: 'a1' }, svg);
    el('polyline', { points: p1.join(' '), class: 'l1' }, svg); el('polyline', { points: pts('visitors').join(' '), class: 'l2' }, svg);
    var hl = el('line', { y1: m.t, y2: H - m.b, class: 'hover-line', visibility: 'hidden' }, svg);
    var d1 = el('circle', { r: 5, class: 'dot', fill: css('--s1'), visibility: 'hidden' }, svg), d2 = el('circle', { r: 5, class: 'dot', fill: css('--s2'), visibility: 'hidden' }, svg);
    var tip = tipFor(box);
    var hit = el('rect', { x: m.l, y: 0, width: W - m.l - m.r, height: H, fill: 'transparent' }, svg);
    function at(e) {
      var r = svg.getBoundingClientRect(); var px = (e.clientX - r.left) / r.width * W;
      var i = Math.max(0, Math.min(data.length - 1, Math.round((px - m.l) / ((W - m.l - m.r) / Math.max(1, data.length - 1)))));
      var d = data[i]; hl.setAttribute('x1', x(i)); hl.setAttribute('x2', x(i)); hl.setAttribute('visibility', 'visible');
      d1.setAttribute('cx', x(i)); d1.setAttribute('cy', y(d.views)); d1.setAttribute('visibility', 'visible');
      d2.setAttribute('cx', x(i)); d2.setAttribute('cy', y(d.visitors)); d2.setAttribute('visibility', 'visible');
      tip.hidden = false; tip.innerHTML = '<b>' + d.label + '</b><i style="background:' + css('--s1') + '"></i>' + d.views + ' page views<br><i style="background:' + css('--s2') + '"></i>' + d.visitors + ' visitors';
      tip.style.left = Math.min(Math.max(x(i) / W * 100, 12), 88) + '%'; tip.style.top = Math.min(y(d.views), y(d.visitors)) + 'px';
    }
    hit.addEventListener('mousemove', at); hit.addEventListener('touchstart', function (e) { at(e.touches[0]); }, { passive: true });
    hit.addEventListener('mouseleave', function () { hl.setAttribute('visibility', 'hidden'); d1.setAttribute('visibility', 'hidden'); d2.setAttribute('visibility', 'hidden'); tip.hidden = true; });
  }

  function barChart(box, data) {
    box.innerHTML = '';
    var W = box.clientWidth, H = box.clientHeight, m = { l: 30, r: 4, t: 8, b: 22 };
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'none' }, box);
    var max = niceMax(Math.max.apply(null, data.map(function (d) { return d.views; }).concat([1])));
    var bw = (W - m.l - m.r) / data.length;
    [0, 0.5, 1].forEach(function (f) { var gy = m.t + (H - m.t - m.b) * (1 - f); el('line', { x1: m.l, x2: W - m.r, y1: gy, y2: gy, class: 'grid-line' }, svg); var t = el('text', { x: m.l - 6, y: gy + 4, 'text-anchor': 'end', class: 'tick' }, svg); t.textContent = Math.round(max * f); });
    var tip = tipFor(box);
    data.forEach(function (d, i) {
      var h = (H - m.t - m.b) * d.views / max, bx = m.l + i * bw + 2;
      var r = el('rect', { x: bx, y: H - m.b - h, width: Math.max(2, bw - 4), height: Math.max(h, d.views ? 2 : 0), rx: 3, class: 'bar' }, svg);
      if (i % 3 === 0) { var t = el('text', { x: bx + (bw - 4) / 2, y: H - 6, 'text-anchor': 'middle', class: 'tick' }, svg); t.textContent = (d.hour < 10 ? '0' : '') + d.hour; }
      r.addEventListener('mouseenter', function () { tip.hidden = false; tip.innerHTML = '<b>' + (d.hour < 10 ? '0' : '') + d.hour + ':00</b>' + d.views + ' page views'; tip.style.left = ((bx + (bw - 4) / 2) / W * 100) + '%'; tip.style.top = (H - m.b - h) + 'px'; });
      r.addEventListener('mouseleave', function () { tip.hidden = true; });
    });
  }

  var series = $('#series-data') && JSON.parse($('#series-data').textContent);
  var hours = $('#hours-data') && JSON.parse($('#hours-data').textContent);
  function drawAll() { if (series && $('#chart')) lineChart($('#chart'), series); if (hours && $('#hours')) barChart($('#hours'), hours); }
  drawAll(); var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(drawAll, 120); });

  var tbtn = $('#chart-table-btn');
  if (tbtn && series) tbtn.addEventListener('click', function () {
    var tw = $('#chart-table'), show = tw.hidden;
    if (show && !tw.innerHTML) tw.innerHTML = '<table class="tbl"><thead><tr><th>Date</th><th class="num">Page views</th><th class="num">Visitors</th></tr></thead><tbody>' + series.slice().reverse().map(function (d) { return '<tr><td>' + d.label + '</td><td class="num">' + d.views + '</td><td class="num">' + d.visitors + '</td></tr>'; }).join('') + '</tbody></table>';
    tw.hidden = !show; $('#chart').hidden = show; tbtn.textContent = show ? 'Show as chart' : 'Show as table'; tbtn.setAttribute('aria-pressed', show);
  });

  /* live feed */
  if (window.DASH_LIVE_URL && $('#feed')) setInterval(function () {
    if (document.hidden) return;
    fetch(window.DASH_LIVE_URL, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) {
      var n = $('#online-n'); if (n) n.textContent = j.online;
      var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
      if (j.recent.length) $('#feed').innerHTML = j.recent.map(function (r) { return '<li><span class="feed-time">' + esc(r.time) + '</span><span class="feed-main"><b>' + esc(r.label) + '</b><small>' + esc(r.country) + ' · ' + esc(r.device) + ' · ' + esc(r.source) + '</small></span></li>'; }).join('');
    }).catch(function () {});
  }, 15000);

  /* ---------- list: toggles + drag to reorder ---------- */
  $$('[data-toggle]').forEach(function (b) {
    b.addEventListener('click', function () {
      fetch(b.dataset.toggle, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); }).then(function (j) {
          b.classList.toggle('on', j.value); b.setAttribute('aria-pressed', j.value);
          if (b.textContent.trim() === 'Published') b.closest('tr').classList.toggle('dim', !j.value);
        });
    });
  });
  var tbl = $('#sortable');
  if (tbl) {
    var body = tbl.tBodies[0], drag = null;
    body.addEventListener('dragstart', function (e) { drag = e.target.closest('tr[data-id]'); if (drag) { drag.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; } });
    body.addEventListener('dragover', function (e) { e.preventDefault(); var t = e.target.closest('tr[data-id]'); $$('.over', body).forEach(function (r) { r.classList.remove('over'); }); if (t && t !== drag) t.classList.add('over'); });
    body.addEventListener('drop', function (e) {
      e.preventDefault(); var t = e.target.closest('tr[data-id]'); if (!drag || !t || t === drag) return;
      var rows = $$('tr[data-id]', body); body.insertBefore(drag, rows.indexOf(drag) < rows.indexOf(t) ? t.nextSibling : t);
    });
    body.addEventListener('dragend', function () {
      if (!drag) return; drag.classList.remove('dragging'); $$('.over', body).forEach(function (r) { r.classList.remove('over'); }); drag = null;
      fetch(tbl.dataset.reorder, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: $$('tr[data-id]', body).map(function (r) { return r.dataset.id; }) }) });
    });
  }

  /* ---------- editor: inline rows ---------- */
  $$('.fs').forEach(function (fs) {
    var p = fs.dataset.prefix, rows = $('.fs-rows', fs), total = $('#id_' + p + '-TOTAL_FORMS'), tpl = $('.fs-empty', fs);
    var renumber = function () { if (fs.dataset.ordered !== '1') return; $$('.fs-row', rows).forEach(function (r, i) { var o = $('input[name$="-order"]', r); if (o) o.value = i + 1; }); };
    $('.fs-add', fs).addEventListener('click', function () {
      var n = parseInt(total.value, 10), wrap = document.createElement('div'); wrap.innerHTML = tpl.innerHTML.replace(/__prefix__/g, n);
      var row = wrap.firstElementChild; rows.appendChild(row); total.value = n + 1; renumber();
      var f = $('input[type=text],input:not([type=hidden])', row); if (f) f.focus();
    });
    fs.addEventListener('click', function (e) {
      var up = e.target.closest('.fs-up'), dn = e.target.closest('.fs-down'); if (!up && !dn) return;
      var r = e.target.closest('.fs-row'); if (up && r.previousElementSibling) rows.insertBefore(r, r.previousElementSibling); if (dn && r.nextElementSibling) rows.insertBefore(r.nextElementSibling, r); renumber();
    });
    $('#editor').addEventListener('submit', renumber); renumber();
  });
})();
