/* Dashboard motion layer. Progressive: without it everything is still visible. */
(function () {
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var bar = document.getElementById('nprog');

  /* top loading bar on navigation and form posts */
  var go = function () { if (bar) { bar.classList.remove('run'); void bar.offsetWidth; bar.classList.add('run'); } };
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (a && !a.target && a.origin === location.origin && !e.metaKey && !e.ctrlKey && a.getAttribute('href').charAt(0) !== '#') go();
  });
  document.addEventListener('submit', go);

  /* sidebar stagger index, sticky header shadow */
  $$('.side-nav a').forEach(function (a, i) { a.style.setProperty('--n', i); });
  var top = document.querySelector('.top');
  if (top) addEventListener('scroll', function () { top.classList.toggle('stuck', scrollY > 6); }, { passive: true });

  /* toasts dismiss themselves */
  $$('.toasts .toast').forEach(function (t, i) { setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 450); }, 5200 + i * 600); });

  /* ripple on buttons */
  document.addEventListener('pointerdown', function (e) {
    var b = e.target.closest('.btn'); if (!b || reduce) return;
    var r = b.getBoundingClientRect(), s = Math.max(r.width, r.height), d = document.createElement('span');
    d.className = 'ripple'; d.style.cssText = 'width:' + s + 'px;height:' + s + 'px;left:' + (e.clientX - r.left - s / 2) + 'px;top:' + (e.clientY - r.top - s / 2) + 'px';
    b.appendChild(d); setTimeout(function () { d.remove(); }, 650);
  });

  /* index rows so CSS can stagger them */
  $$('tbody').forEach(function (tb) { $$('tr', tb).forEach(function (tr, i) { tr.style.setProperty('--i', Math.min(i, 14)); }); });
  $$('.inbox').forEach(function (ul) { $$('li', ul).forEach(function (li, i) { li.style.setProperty('--i', Math.min(i, 14)); }); });
  $$('.bars').forEach(function (ul) { $$('.bar-fill', ul).forEach(function (f, i) { f.style.setProperty('--i', i); }); });
  $$('.feed li').forEach(function (li, i) { li.style.setProperty('--i', Math.min(i, 10)); });

  /* count-up for KPI numbers */
  var count = function (el) {
    var raw = el.textContent.trim(), m = raw.match(/^([\d,]+(?:\.\d+)?)(%?)$/);
    if (!m || reduce) return;
    var end = parseFloat(m[1].replace(/,/g, '')), dec = (m[1].split('.')[1] || '').length, pct = m[2], comma = m[1].indexOf(',') > -1;
    var t0 = performance.now(), dur = 1300;
    (function f(t) {
      var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4), v = end * e;
      var s = v.toFixed(dec); if (comma) s = Number(s).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
      el.textContent = s + pct; if (p < 1) requestAnimationFrame(f); else el.textContent = raw;
    })(t0);
  };

  /* chart draw-in once the card is visible */
  var armChart = function (c) {
    $$('polyline', c).forEach(function (p) { try { p.style.setProperty('--len', Math.ceil(p.getTotalLength()) + 2); } catch (e) {} });
    $$('.bar', c).forEach(function (r, i) { r.style.setProperty('--i', i); });
    c.classList.add('draw');
    /* dash.js redraws charts on resize; do not replay the intro every time */
    setTimeout(function () { c.classList.remove('draw'); $$('polyline', c).forEach(function (p) { p.style.strokeDasharray = 'none'; }); }, 3200);
  };

  /* reveal cards and sections as they scroll in */
  var targets = $$('.content .card, .content .kpis > *, .content .table-wrap, .content .grid > *, .content form > section, .content .editor > *');
  var seen = new Set();
  targets = targets.filter(function (t) { if (seen.has(t)) return false; seen.add(t); return !t.closest('dialog'); });
  targets.forEach(function (t) {
    var sibs = Array.prototype.filter.call(t.parentNode.children, function (c) { return seen.has(c); });
    t.style.setProperty('--i', Math.min(sibs.indexOf(t), 6));
    if (!reduce) t.classList.add('fx');
  });
  var show = function (t) {
    t.classList.add('in');
    $$('.kpi-value', t).forEach(count);
    if (t.matches('.kpi-value')) count(t);
    $$('.chart', t).forEach(armChart);
    setTimeout(function () { t.classList.add('done'); }, 1200);
  };
  if (reduce || !('IntersectionObserver' in window)) { targets.forEach(show); }
  else {
    var io = new IntersectionObserver(function (en) { en.forEach(function (x) { if (x.isIntersecting) { show(x.target); io.unobserve(x.target); } }); }, { threshold: .08, rootMargin: '0px 0px -4% 0px' });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* spotlight follows the pointer over cards */
  if (matchMedia('(hover: hover) and (pointer: fine)').matches && !reduce) {
    $$('.card').forEach(function (c) {
      c.addEventListener('pointermove', function (e) { var r = c.getBoundingClientRect(); c.style.setProperty('--mx', (e.clientX - r.left) + 'px'); c.style.setProperty('--my', (e.clientY - r.top) + 'px'); });
    });
  }

  /* new rows in the live feed flash in */
  var feed = document.getElementById('feed');
  if (feed) new MutationObserver(function (ms) { ms.forEach(function (m) { Array.prototype.forEach.call(m.addedNodes, function (n) { if (n.nodeType === 1 && n.tagName === 'LI') n.classList.add('fresh'); }); }); }).observe(feed, { childList: true });
})();
