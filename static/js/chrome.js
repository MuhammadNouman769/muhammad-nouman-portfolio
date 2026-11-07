/* Section sub-header: builds anchor links from [data-sec], highlights the section in view, shows page progress. */
(function () {
  'use strict';
  var nav = document.getElementById('site-nav'), sub = document.getElementById('subnav'), box = document.getElementById('sub-links'), bar = document.getElementById('sub-bar');
  if (!nav) return;
  var root = document.documentElement, ticking = false, items = [], links = [];
  function setTotal() { root.style.setProperty('--nav-total', nav.offsetHeight + 'px'); }
  setTotal(); window.addEventListener('resize', setTotal, { passive: true });
  if (sub && box) {
    var used = {};
    [].forEach.call(document.querySelectorAll('[data-sec]'), function (el, k) {
      var label = (el.getAttribute('data-sec') || '').trim(); if (!label) return;
      if (!el.id) el.id = 'sec-' + (k + 1);
      if (used[el.id]) return; used[el.id] = 1; items.push({ el: el, label: label });
    });
    if (items.length >= 2) {
      items.forEach(function (it) {
        var a = document.createElement('a'); a.href = '#' + it.el.id; a.textContent = it.label; box.appendChild(a); links.push(a);
        a.addEventListener('click', function () { mark(links.indexOf(a)); });
      });
      sub.hidden = false; setTotal();
    }
  }
  function mark(i) {
    links.forEach(function (a, j) { if (j === i) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
    var a = links[i]; if (a && box.scrollWidth > box.clientWidth) { var l = a.offsetLeft - (box.clientWidth - a.offsetWidth) / 2; box.scrollTo({ left: l, behavior: 'smooth' }); }
  }
  var current = -1;
  function update() {
    ticking = false;
    nav.classList.toggle('scrolled', window.scrollY > 8);
    var h = document.documentElement.scrollHeight - innerHeight;
    if (bar) bar.style.transform = 'scaleX(' + (h > 0 ? Math.min(1, scrollY / h) : 0) + ')';
    if (!items.length) return;
    var line = nav.offsetHeight + 40, idx = 0;
    for (var i = 0; i < items.length; i++) { if (items[i].el.getBoundingClientRect().top <= line) idx = i; }
    if (innerHeight + scrollY >= document.documentElement.scrollHeight - 4) idx = items.length - 1;
    if (idx !== current) { current = idx; mark(idx); }
  }
  function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(update); } }
  window.addEventListener('scroll', onScroll, { passive: true }); window.addEventListener('resize', onScroll, { passive: true });
  update();
})();
