# Muhammad Nouman: portfolio (Django 5.2)

A production-ready portfolio with a custom **dashboard** (visitor analytics, content management, inbox) in place of the Django admin.

## What is inside

| Area | Details |
| --- | --- |
| Public site | Home, Work (filterable) with a detail page per project, About, Experience, Skills, Services, Contact, Privacy, custom 404/500. Light and dark theme. |
| Lamp | Every banner has a pull-cord lamp. Pull it and light spreads from the shade to reveal the page; pull again and the page goes black. State is remembered across pages. Crawlers and no-JS visitors always get the lit page. |
| Dashboard | `/dashboard/`: overview charts, live visitors, visitor log with filters and CSV export, projects / skills / experience / services / education / about text / site settings, drag-to-reorder, publish and feature toggles, inbox (read, star, reply, delete), password change. |
| Analytics | Every page view is recorded (page, referrer, UTM, device, browser, OS, country, IP). Bots are flagged and excluded from charts. Staff visits are not counted. |
| SEO | Unique title and description per page, canonical URLs, Open Graph and Twitter cards, JSON-LD (Person, WebSite, CreativeWork, BreadcrumbList, ItemList), `sitemap.xml`, `robots.txt`, search-readiness checklist in Site settings. |
| Security | Secure cookies and HSTS when `DEBUG=False`, CSRF, login throttling, honeypot and rate limit on the contact form, dashboard at a configurable URL, Django admin off by default, uploads limited to 5 MB. |
| Deploy | `Dockerfile`, `docker-compose.yml`, gunicorn config, nginx and systemd examples in `deploy/`. |

## Run it locally

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate            # upgrades your existing db.sqlite3 and keeps all data
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in at http://127.0.0.1:8000/dashboard/ with your existing superuser.
Starting from an empty database instead? Run `python manage.py seed_data` and `python manage.py createsuperuser`.

Run the tests: `python manage.py test apps`

## Go live (VPS with nginx)

1. Copy `.env.example` to `.env` and fill in `SECRET_KEY`, `ALLOWED_HOSTS`, `SITE_URL` (https), `CSRF_TRUSTED_ORIGINS`. Keep `DEBUG=False`.
2. `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
3. Run gunicorn with `deploy/portfolio.service`, put `deploy/nginx.conf` in front, then `certbot --nginx -d yourdomain.com`.
4. In the dashboard open **Site settings**: fill the SEO fields, upload a 1200x630 share image, then follow the *Search readiness* list. Submit `https://yourdomain.com/sitemap.xml` in Google Search Console.
5. Optional: schedule `python manage.py prune_analytics` weekly to enforce `ANALYTICS_RETENTION_DAYS`.

Docker: `docker compose up -d --build`.

## Daily use

* **Add a project**: Dashboard → Projects → Add project. Fill title and summary, add tech tags and capabilities, upload a cover. Untick *Published* to keep it hidden.
* **Reorder**: drag the handle on any list (projects, skills, experience, services, education).
* **Change hero text, contact details, social links, portrait, résumé PDF, lamp default**: Dashboard → Site settings. Changes are live instantly.
* **Lamp default**: *Lamp starts switched on* in Site settings. Off (default) means first-time visitors see a dark page and pull the cord. Their choice is remembered only for that visit, so every new visit starts dark.
* **Hide the dashboard URL**: set `DASHBOARD_URL=my-secret-path/` in `.env`.

## Privacy note

Analytics stores IP addresses and a first-party cookie (`nv_id`). Set `ANALYTICS_ANONYMIZE_IP=True` to truncate IPs, or `ANALYTICS_USE_COOKIE=False` for cookie-less counting. The `/privacy/` page already describes this; edit `templates/privacy.html` if you change behaviour.

## Notes

* Fonts load from Google Fonts. To self-host, download Bricolage Grotesque and JetBrains Mono (woff2) into `static/fonts/` and replace the `<link>` in `templates/base.html` and `templates/dashboard/base.html`.
* Country detection works automatically behind Cloudflare (`CF-IPCountry`). Otherwise add a MaxMind GeoLite2 folder to `GEOIP_PATH` and `pip install geoip2`.
* Two small data fixes ship as migrations: stray "Date range:" and "Headline:" prefixes in the existing database content are removed.

## v4: hiring-focused edition

- **Home** is built for CEOs, HR and managers: lamp banner, "Remote / On-site / Contract" hire triptych, stacked case studies, how-I-work sequence, toolbox tabs, blog magazine, git-log experience, services. Every "Hire me" button opens a 30-second dialog that lands in the dashboard inbox (and your email).
- **Lamp**: the page opens dark. Pull the chain (drag it down, tap it, or press Enter) to light the room. Real pendulum swing, synthesised click sound, warm-up flicker. State is remembered; search crawlers always see the lit page. Set `lamp_default_on` in Site settings to start lit.
- **Case studies** are Projects with "case study" ticked (challenge, solution, metrics, architecture flow). **Blog** is under Dashboard > Blog posts (Markdown). Sample articles and case studies were written from your résumé: review them and replace any wording that is not exactly true for you (`python manage.py seed_blog`, `seed_projects` only fill empty content).
- **Mobile** (under 900px) switches to an app layout: bottom tab bar with a centre Hire button, "More" bottom sheet, swipe cards, safe-area padding.
- Fonts load from Google Fonts at runtime; your server needs outbound internet for that (or self-host the two families).

- **Dashboard motion**: animated sign-in screen (aurora, particles, glowing card, show/hide password), staggered sidebar, count-up KPIs, charts that draw in, growing bars, spotlight cards and animated tables/toasts. Files: `static/dashboard/fx.css`, `fx.js`. All of it switches off under reduced-motion.

## Local test, then deploy

Local (Windows PowerShell):
    python -m venv venv ; venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver        # DEBUG=True in .env for local

If you test with DEBUG=False, either run `python manage.py collectstatic --noinput`
first or just run as-is: the site falls back to plain static storage when no
manifest exists (no more "Missing staticfiles manifest entry").

PythonAnywhere (from the repo):
    git clone https://github.com/MuhammadNouman769/noumanportfolio.git
    cd noumanportfolio && git checkout redesign-v7   # or merge to main first
    mkvirtualenv --python=python3.12 nouman && pip install -r requirements.txt
    create .env (SECRET_KEY, DEBUG=False, ALLOWED_HOSTS=<you>.pythonanywhere.com)
    python manage.py migrate && python manage.py collectstatic --noinput
    Web tab: set source dir + virtualenv, WSGI -> core.wsgi,
             Static: /static/ -> <repo>/staticfiles , /media/ -> <repo>/media
    Reload.

## Updates robot and email subscribers

A small robot (bottom-left) asks visitors for a name and email and subscribes them. When you publish a new
blog post or a case study, every active subscriber gets a designed email card automatically (once per item).
Dashboard > Subscribers lists people, lets you pause/remove them, send a custom update (with a "send me a test"
button) and shows recent campaigns. Every email has a one-click unsubscribe link.

Emails need SMTP in `.env`, otherwise they only print in the console. Gmail example (use an App Password):

    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_HOST_USER=you@gmail.com
    EMAIL_HOST_PASSWORD=<16-character app password>
    DEFAULT_FROM_EMAIL=Muhammad Nouman <you@gmail.com>

After pulling: `python manage.py migrate` (new tables) then `collectstatic` and reload.

## Dummy data for design and QA

    python manage.py seed_dummy            # adds 9 posts (15 total), 2 categories, 3 projects (15 total),
                                           # 4 experience entries, 8 contact messages, 14 subscribers
    python manage.py seed_dummy --remove   # deletes only what that command added

Dummy subscribers use `@example.com` and never receive emails. Seeding does not trigger announcement emails.

## One-command update on PythonAnywhere

One-time setup (Bash console):

    chmod +x ~/muhammad-nouman-portfolio/deploy/pa_update.sh
    echo "alias deploy='bash ~/muhammad-nouman-portfolio/deploy/pa_update.sh'" >> ~/.bashrc
    source ~/.bashrc

After that, every update is just:  `deploy`
(it pulls, installs requirements, migrates, collects static files and reloads the site).
