/* Moving banner slider on the home page. Autoplay, swipe, arrows, dots, pause on hover/focus. */
(function () {
  'use strict';
  var root = document.querySelector('[data-slider]');
  if (!root) return;
  var track = root.querySelector('.bs-track'), slides = [].slice.call(root.querySelectorAll('.bs-slide'));
  var dotsBox = root.querySelector('.bs-dots'), n = slides.length, i = 0, timer = null, DELAY = 5800;
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (n < 2) { root.classList.add('single'); return; }
  var dots = slides.map(function (s, k) {
    var b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('aria-label', 'Banner ' + (k + 1) + ' of ' + n);
    b.innerHTML = '<i></i>'; b.addEventListener('click', function () { go(k, true); }); dotsBox.appendChild(b); return b;
  });
  function go(k, user) {
    i = (k + n) % n; track.style.transform = 'translate3d(' + (-100 * i) + '%,0,0)';
    slides.forEach(function (s, j) { s.classList.toggle('is-active', j === i); s.setAttribute('aria-hidden', j === i ? 'false' : 'true'); [].forEach.call(s.querySelectorAll('a,button'), function (el) { if (j === i) el.removeAttribute('tabindex'); else el.setAttribute('tabindex', '-1'); }); });
    dots.forEach(function (d, j) { d.classList.toggle('on', j === i); d.setAttribute('aria-selected', j === i ? 'true' : 'false'); d.classList.remove('run'); });
    if (!reduce) { void dotsBox.offsetWidth; dots[i].classList.add('run'); }
    if (user) restart();
  }
  function stop() { clearTimeout(timer); timer = null; root.classList.add('paused'); }
  function restart() { clearTimeout(timer); root.classList.remove('paused'); if (reduce || document.hidden) return; timer = setTimeout(function () { go(i + 1); restart(); }, DELAY); }
  root.querySelector('[data-prev]').addEventListener('click', function () { go(i - 1, true); });
  root.querySelector('[data-next]').addEventListener('click', function () { go(i + 1, true); });
  root.addEventListener('mouseenter', stop); root.addEventListener('mouseleave', restart);
  root.addEventListener('focusin', stop); root.addEventListener('focusout', restart);
  root.addEventListener('keydown', function (e) { if (e.key === 'ArrowLeft') go(i - 1, true); if (e.key === 'ArrowRight') go(i + 1, true); });
  document.addEventListener('visibilitychange', function () { if (document.hidden) stop(); else restart(); });
  /* swipe */
  var x0 = null, y0 = 0, dx = 0, w = 1;
  track.addEventListener('pointerdown', function (e) { if (e.pointerType === 'mouse') return; x0 = e.clientX; y0 = e.clientY; dx = 0; w = track.offsetWidth; stop(); });
  track.addEventListener('pointermove', function (e) { if (x0 === null) return; dx = e.clientX - x0; if (Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(e.clientY - y0)) { track.style.transition = 'none'; track.style.transform = 'translate3d(' + (-100 * i + dx / w * 100) + '%,0,0)'; } });
  function end() { if (x0 === null) return; track.style.transition = ''; var d = dx; x0 = null; if (d < -w * .15) go(i + 1, true); else if (d > w * .15) go(i - 1, true); else go(i, true); }
  track.addEventListener('pointerup', end); track.addEventListener('pointercancel', end);
  go(0); restart();
})();
