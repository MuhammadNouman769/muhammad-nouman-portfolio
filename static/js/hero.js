/* Home hero motion: gradient heading, typing role line, count-up numbers, cursor spotlight. */
(function () {
  'use strict';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.hero.h-banner');
  if (!hero) return;
  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  // 1) last words of the heading get the animated gradient
  var h1 = hero.querySelector('h1');
  if (h1 && !h1.querySelector('.grad')) {
    var words = h1.textContent.trim().split(/\s+/);
    if (words.length > 3) {
      var n = Math.min(3, Math.ceil(words.length / 3));
      h1.innerHTML = esc(words.slice(0, -n).join(' ')) + ' <span class="grad">' + esc(words.slice(-n).join(' ')) + '</span>';
    }
  }

  // 2) typing role line
  var role = hero.querySelector('[data-rotate]');
  if (role) {
    var list = role.getAttribute('data-rotate').split('|'), wi = 0, ci = list[0].length, del = false;
    if (!reduce) {
      (function tick() {
        var w = list[wi];
        role.textContent = w.slice(0, ci);
        var wait = del ? 38 : 85;
        if (!del && ci === w.length) { del = true; wait = 1500; }
        else if (del && ci === 0) { del = false; wi = (wi + 1) % list.length; wait = 350; }
        else ci += del ? -1 : 1;
        setTimeout(tick, wait);
      })();
    }
  }

  // 3) count-up numbers
  hero.querySelectorAll('.h-trust b').forEach(function (el) {
    var m = el.textContent.trim().match(/^(\d+)(.*)$/);
    if (!m || reduce) return;
    var end = +m[1], suffix = m[2], t0 = null;
    el.textContent = '0' + suffix;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / 1400), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * e) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    setTimeout(function () { requestAnimationFrame(step); }, 500);
  });

  // 4) cursor spotlight
  if (!reduce) {
    hero.addEventListener('pointermove', function (e) {
      var r = hero.getBoundingClientRect();
      hero.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
      hero.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
    });
  }
})();
