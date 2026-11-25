"""Run on the server:  python manage.py diagnose_site

Checks everything that differs between your laptop and the live server and prints a clear PASS / FAIL
list, including the real Python error behind any "Something broke on my side" page.
"""
import glob
import json
import os
import re
import traceback

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, override_settings


class Command(BaseCommand):
    help = 'Diagnose why pages return 500 / why the PDF does not open on this server.'

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS('  PASS  ') + msg)

    def bad(self, msg):
        self.fails += 1
        self.stdout.write(self.style.ERROR('  FAIL  ') + msg)

    def info(self, msg):
        self.stdout.write('  ....  ' + msg)

    def head(self, t):
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + t))

    def handle(self, *a, **o):
        self.fails = 0
        base = settings.BASE_DIR

        self.head('1. Settings')
        self.info(f'DEBUG={settings.DEBUG}  SITE_URL={settings.SITE_URL}  BEHIND_PROXY={getattr(settings, "BEHIND_PROXY", None)}')
        self.info(f'ALLOWED_HOSTS={settings.ALLOWED_HOSTS}')
        self.info(f'DB={connection.settings_dict.get("NAME")}  MEDIA_ROOT={settings.MEDIA_ROOT}')
        self.info(f'static storage={settings.STORAGES["staticfiles"]["BACKEND"]}')
        if settings.DEBUG:
            self.bad('DEBUG is True on the server. Set DEBUG=False in .env')
        else:
            self.ok('DEBUG is off')

        self.head('2. Database + migrations')
        try:
            plan = MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes())
            if plan:
                self.bad(f'{len(plan)} migration(s) NOT applied, run: python manage.py migrate   ({", ".join(m.app_label + "." + m.name for m, _ in plan[:6])})')
            else:
                self.ok('all migrations applied')
        except Exception as e:
            self.bad(f'cannot read migrations: {e}')
        for model in apps.get_models():
            try:
                model.objects.count()
            except Exception as e:
                self.bad(f'table for {model._meta.label} is broken: {type(e).__name__}: {str(e)[:120]}')

        self.head('3. Templates referenced by code exist')
        missing = 0
        tdirs = [str(d) for d in settings.TEMPLATES[0]['DIRS']]
        pat = re.compile(r"""['"]([\w/]+\.html)['"]""")
        for f in glob.glob(str(base / 'apps/**/*.py'), recursive=True) + glob.glob(str(base / 'core/*.py')):
            for m in pat.finditer(open(f, encoding='utf8', errors='ignore').read()):
                p = m.group(1)
                if not any(os.path.exists(os.path.join(d, p)) for d in tdirs) and not glob.glob(str(base / f'apps/*/templates/{p}')):
                    missing += 1
                    self.bad(f'template "{p}" is used in {os.path.relpath(f, base)} but the file is missing')
        if not missing:
            self.ok('no missing templates')

        self.head('4. Static files')
        root = settings.STATIC_ROOT
        manifest = os.path.join(root, 'staticfiles.json')
        if not os.path.exists(os.path.join(root, 'css')):
            self.bad('STATIC_ROOT has no files: run python manage.py collectstatic --noinput (and map /static/ in the PythonAnywhere Web tab)')
        elif os.path.exists(manifest):
            paths = json.load(open(manifest))['paths']
            stale = [r for r in glob.glob(str(base / 'static/**/*.*'), recursive=True) if os.path.relpath(r, base / 'static') not in paths]
            (self.bad if stale else self.ok)(f'{len(stale)} static file(s) newer than the last collectstatic, run collectstatic' if stale else 'manifest is up to date')
        else:
            self.ok('no manifest (plain static URLs), fine')

        self.head('5. Books: files on disk')
        try:
            from apps.books.models import Book
            for b in Book.objects.all():
                for label, f in (('PDF', b.pdf_file), ('cover', b.cover_image)):
                    if not f:
                        continue
                    if os.path.exists(f.path):
                        self.ok(f'{b.title}: {label} found ({os.path.getsize(f.path) // 1024} KB)')
                    else:
                        self.bad(f'{b.title}: {label} is in the database but NOT on this server: {f.path}  -> upload media/ or re-upload it in Dashboard > Books')
        except Exception as e:
            self.bad(f'books check failed: {e}')

        self.head('6. Pages (real request, shows the Python error if one fails)')
        host = next((h for h in settings.ALLOWED_HOSTS if h and not h.startswith('.') and h != '*'), 'localhost')
        urls = ['/', '/about/', '/projects/', '/blog/', '/books/', '/contact/', '/health/']
        try:
            from apps.books.models import Book
            for b in Book.objects.filter(published=True)[:3]:
                urls += [b.get_absolute_url(), b.get_read_url()] + ([b.get_file_url()] if b.has_pdf else [])
        except Exception:
            pass
        with override_settings(ALLOWED_HOSTS=['*']):
            c = Client(HTTP_HOST=host, HTTP_X_FORWARDED_PROTO='https', raise_request_exception=True)
            for u in urls:
                try:
                    r = c.get(u, secure=True)
                    if r.status_code >= 500:
                        self.bad(f'{u} -> {r.status_code}')
                    elif r.status_code == 404 and u.endswith('file/'):
                        self.bad(f'{u} -> 404: the PDF file is missing on disk')
                    else:
                        extra = f'  ({r["Content-Type"]}, X-Frame-Options={r.get("X-Frame-Options", "-")})' if u.endswith('file/') else ''
                        self.ok(f'{u} -> {r.status_code}{extra}')
                except Exception as e:
                    tb = traceback.extract_tb(e.__traceback__)
                    where = next((f'{os.path.relpath(t.filename, base)}:{t.lineno}' for t in reversed(tb) if str(base) in t.filename and 'venv' not in t.filename and 'site-packages' not in t.filename), '?')
                    self.bad(f'{u} -> CRASH {type(e).__name__}: {str(e)[:200]}  [{where}]')

        self.stdout.write('')
        if self.fails:
            self.stdout.write(self.style.ERROR(f'{self.fails} problem(s) found. Fix the FAIL lines above (or send them to Claude).'))
        else:
            self.stdout.write(self.style.SUCCESS('Everything looks fine on this server.'))
