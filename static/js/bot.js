/* Updates robot: asks name, then email, then subscribes the visitor. */
(function () {
  'use strict';
  var root = document.getElementById('bot'); if (!root) return;
  var fab = document.getElementById('bot-fab'), panel = document.getElementById('bot-panel'), log = document.getElementById('bot-log'),
      quick = document.getElementById('bot-quick'), form = document.getElementById('bot-form'), input = document.getElementById('bot-in'),
      bubble = document.getElementById('bot-bubble'), send = form.querySelector('.bot-send'), closeBtn = document.getElementById('bot-x');
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var store = { get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  var step = 'idle', name = '', started = false, busy = false;

  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, reduce ? 0 : ms); }); };
  var scroll = function () { log.scrollTop = log.scrollHeight; };
  var add = function (text, who) { var d = document.createElement('div'); d.className = 'bot-msg ' + who; d.textContent = text; log.appendChild(d); scroll(); return d; };
  var say = function (text) {
    var t = document.createElement('div'); t.className = 'bot-msg nova typing'; t.innerHTML = '<i></i><i></i><i></i>'; log.appendChild(t); scroll();
    return wait(520 + Math.min(text.length * 9, 600)).then(function () { t.remove(); add(text, 'nova'); });
  };
  var enable = function (on, ph, type) { input.disabled = send.disabled = !on; if (ph) input.placeholder = ph; if (type) input.type = type; if (on) { input.value = ''; input.focus({ preventScroll: true }); } };
  var chips = function (list) { quick.innerHTML = ''; list.forEach(function (c) { var b = document.createElement('button'); b.type = 'button'; b.textContent = c[0]; b.onclick = function () { quick.innerHTML = ''; add(c[0], 'me'); c[1](); }; quick.appendChild(b); }); };

  var askName = function () { step = 'name'; return say('Great. What should I call you?').then(function () { enable(true, 'Your name', 'text'); input.autocomplete = 'name'; }); };
  var askEmail = function () { step = 'email'; return say('Nice to meet you, ' + name + '. Which email should I use?').then(function () { enable(true, 'you@company.com', 'email'); input.autocomplete = 'email'; input.inputMode = 'email'; }); };
  var done = function () { step = 'done'; enable(false, 'Subscribed'); input.type = 'text'; store.set('botDone', '1'); root.classList.add('seen'); };

  var start = function () {
    if (started) return; started = true;
    if (store.get('botDone')) { say('Welcome back! You are already on the list. Thanks for following along.').then(function () { step = 'done'; }); return; }
    say('Hi, I am Nova, the updates robot for ' + (root.dataset.owner || 'this site') + '.')
      .then(function () { return say('I can email you when a new article, case study or update goes live. Shall I add you?'); })
      .then(function () { chips([['Yes, add me', askName], ['No thanks', function () { say('No problem. I am here if you change your mind.').then(function () { step = 'idle'; }); }]]); });
  };

  var open = function () {
    panel.hidden = false; fab.setAttribute('aria-expanded', 'true'); bubble.hidden = true; root.classList.add('seen'); store.set('botSeen', '1');
    start(); if (!input.disabled) input.focus({ preventScroll: true });
  };
  var close = function () { panel.hidden = true; fab.setAttribute('aria-expanded', 'false'); fab.focus({ preventScroll: true }); };
  fab.addEventListener('click', function () { panel.hidden ? open() : close(); });
  closeBtn.addEventListener('click', close);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) close(); });

  form.addEventListener('submit', function (e) {
    e.preventDefault(); if (busy || input.disabled) return;
    var v = input.value.trim(); if (!v) return;
    if (step === 'name') {
      if (v.replace(/[^A-Za-z؀-ۿ]/g, '').length < 2) { add(v, 'me'); enable(false); say('Please type your name, at least two letters.').then(function () { enable(true); }); return; }
      name = v.slice(0, 80); add(v, 'me'); enable(false); askEmail();
    } else if (step === 'email') {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) { add(v, 'me'); enable(false); say('That email does not look right. Could you check it?').then(function () { enable(true); input.value = v; }); return; }
      add(v, 'me'); enable(false); busy = true;
      var fd = new FormData(form); fd.set('name', name); fd.set('email', v);
      say('Adding you to the list…').then(function () {
        return fetch(root.dataset.url, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' });
      }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok && j.ok, j: j }; }); })
        .then(function (res) {
          busy = false;
          if (res.ok) { return say('Done, ' + name.split(' ')[0] + '! I sent a welcome email to ' + v + '. You will hear from me when something new is published.').then(done); }
          var field = res.j && res.j.field;
          return say((res.j && res.j.error) || 'Something went wrong. Please try again in a moment.').then(function () { if (field === 'name') { step = 'name'; enable(true, 'Your name', 'text'); } else { step = 'email'; enable(true, 'you@company.com', 'email'); input.value = v; } });
        }).catch(function () { busy = false; say('I could not reach the server. Please check your connection and try again.').then(function () { step = 'email'; enable(true, 'you@company.com', 'email'); input.value = v; }); });
    }
  });

  /* a gentle hello once per visit, only after the visitor has had time to look around */
  if (!store.get('botDone') && !store.get('botSeen')) {
    setTimeout(function () {
      if (!panel.hidden || document.documentElement.classList.contains('lamp-off')) return;
      bubble.hidden = false; setTimeout(function () { bubble.hidden = true; }, 9000);
    }, 22000);
  }
})();
