"""Idempotent: writes the four flagship case studies. Safe to run repeatedly (update_or_create by slug)."""
from django.core.management.base import BaseCommand

from apps.projects.models import Project, ProjectFeature, ProjectTag

CASES = [
    dict(
        slug='btr-mall', order_in_showcase=1,
        defaults=dict(
            title='BTR Mall — Multi-Vendor E-Commerce Platform', status=Project.STATUS_PROGRESS, year=2025,
            kind='ecommerce', accent='#1f6b3e', case_study=True, featured=True, published=True,
            role='Backend engineer', client_type='Own product', duration='Aug 2025 to present', team='Solo',
            summary=('A multi-vendor marketplace inspired by Daraz and Amazon. One Django and DRF backend serves '
                     'a React web app and a React Native mobile app, covering seller onboarding, catalog, cart, '
                     'checkout, orders, shipment and delivery.'),
            body=('BTR Mall is the largest system I have built on my own. It is a modular Django backend where each '
                  'business area (accounts, stores, catalog, cart, orders, shipping) is its own app with a narrow public surface.\n\n'
                  'The APIs are versioned REST endpoints documented with Swagger/OpenAPI, so the web and mobile clients are built against one contract.'),
            challenge=('A marketplace is harder than a single-shop store because every order can contain items from several sellers. '
                       'Each seller needs to see, fulfil and be paid for only their part, while the customer still sees one cart, one checkout and one order.\n\n'
                       'The catalog adds a second problem. Products have brands, categories, variants and attributes, and stock has to be tracked per variant, '
                       'otherwise a shared "size M" stock number oversells the wrong item.'),
            solution=('I split the domain into focused Django apps and kept business rules in service functions instead of views, so the same logic backs both '
                      'the web and mobile APIs. A customer order is stored as one parent order with child shipments per seller. Each seller works only with their own child records, '
                      'and shipment and delivery status roll up to the parent order the customer sees.\n\n'
                      'Access control uses JWT authentication with role-based permissions (customer, seller, admin), enforced in DRF permission classes rather than scattered checks. '
                      'Catalog reads are cached in Redis, and slow or retryable work such as notifications runs in Celery workers. '
                      'The whole stack runs in Docker Compose, so a new machine goes from clone to running API with one command.'),
            results=('Seller onboarding and store management flow built end to end\n'
                     'Catalog with categories, brands, variants, attributes and per-variant inventory\n'
                     'Cart, wishlist, checkout, order, shipment and delivery workflows\n'
                     'One API contract for the React web app and the React Native app\n'
                     'Swagger/OpenAPI documentation generated from the code'),
            metrics=('2|client apps on one API: web and mobile\n'
                     'Multi-vendor|orders split per seller\n'
                     'JWT + RBAC|customer, seller and admin roles\n'
                     'Docker|one-command local and deploy environment'),
            architecture=('React / React Native|web and mobile clients\n'
                          'DRF API|versioned REST, JWT, role permissions\n'
                          'Service layer|business rules shared by all endpoints\n'
                          'PostgreSQL|orders, catalog, inventory\n'
                          'Redis|catalog caching and Celery broker\n'
                          'Celery|background and retryable tasks'),
            lessons=('Splitting orders per seller early was the right call. Retrofitting it into a single-order model later would have touched every report and every status transition.\n\n'
                     'The project is still in progress and the live demo is coming soon, so I describe only what is built and tested today.'),
        ),
        tags=['Django', 'DRF', 'PostgreSQL', 'Redis', 'Celery', 'Docker', 'React', 'React Native'],
        features=['Seller onboarding and store management', 'Categories, brands, variants, attributes and inventory',
                  'Cart, wishlist, checkout, order, shipment and delivery workflows', 'JWT authentication with role-based access control',
                  'Redis caching and Celery background tasks', 'Swagger/OpenAPI documentation', 'Dockerized development and deployment'],
    ),
    dict(
        slug='dinex', order_in_showcase=2,
        defaults=dict(
            title='DineX — Multi-Tenant Restaurant POS & Management SaaS', status=Project.STATUS_PROGRESS, year=2026,
            kind='saas', accent='#166534', case_study=True, featured=True, published=True, order=2,
            role='Full-stack engineer', client_type='Own product', duration='Sep 2026 to present', team='Solo',
            summary=('A subscription platform for restaurants: point of sale, orders, recipe-based inventory, cash management and reporting. '
                     'Every restaurant is a tenant with strictly isolated data.'),
            body=('DineX replaces the notebook, the till and the stock sheet with one system. A Django and DRF backend powers a Next.js and TypeScript web app, '
                  'with a separate admin panel for running the SaaS itself.\n\n'
                  'It is built to be operated, not just demoed: HTTPS, nightly backups, CI and more than 200 automated tests on the flows where money and stock move.'),
            challenge=('In a multi-tenant product the worst bug is one restaurant seeing another restaurant\'s data. Isolation has to be a property of the system, '
                       'not something each developer remembers on every query.\n\n'
                       'Restaurants also have operational rules that generic e-commerce ignores. Selling a burger should reduce flour, patties and cheese, '
                       'cash must reconcile at the end of a shift, and every sensitive change needs an audit trail.'),
            solution=('Tenant scoping is enforced centrally: every tenant-owned model carries its restaurant, and request-level scoping filters queries by default, '
                      'so a missing filter fails safe. Tests assert that one tenant cannot read or write another\'s records.\n\n'
                      'Inventory is recipe-based. Menu items map to ingredients, and completing an order writes stock movements automatically instead of editing a number by hand. '
                      'Cash shifts, payments, invoices and an audit log record who did what. Plans and invoices are driven by a scheduled billing job.\n\n'
                      'The POS covers the order lifecycle, floors and tables, kiosk mode and a menu catalog with variants, modifiers and deals. '
                      'It deploys with Docker behind Caddy for automatic HTTPS, with nightly backups and CI running the test suite.'),
            results=('Per-restaurant data isolation across the whole API\n'
                     'POS with order lifecycle, floors and tables, and kiosk mode\n'
                     'Menu catalog with variants, modifiers and deals\n'
                     'Recipe-based inventory with automatic ingredient stock movements\n'
                     'Cash shifts, payments, audit log, plans, invoices and a scheduled billing job\n'
                     'Staff management: employees, work schedules, attendance and rider settlements\n'
                     'A DineX admin panel for operating the SaaS'),
            metrics=('200+|automated tests on core flows\n'
                     'Multi-tenant|strict per-restaurant data isolation\n'
                     'Nightly|database backups\n'
                     'HTTPS|automatic via Caddy'),
            architecture=('Next.js + TypeScript|restaurant web app with Tailwind CSS\n'
                          'Caddy|HTTPS and routing\n'
                          'DRF API|JWT auth, tenant-scoped queries\n'
                          'PostgreSQL|tenant data, stock movements, audit log\n'
                          'Billing job|scheduled plans and invoices\n'
                          'CI + backups|test suite on every push, nightly dumps'),
            lessons=('Writing the isolation tests first made every later feature safer to add. When a new model forgot its tenant, a test failed instead of a customer noticing.\n\n'
                     'Modelling stock as movements rather than a mutable number gave reports and corrections for free, because the history is the source of truth.'),
        ),
        tags=['Django', 'DRF', 'PostgreSQL', 'Next.js', 'TypeScript', 'Tailwind CSS', 'Docker', 'Caddy', 'JWT'],
        features=['Multi-tenant architecture with per-restaurant data isolation', 'POS: order lifecycle, floors and tables, kiosk mode',
                  'Menu catalog with variants, modifiers and deals', 'Recipe-based inventory with automatic stock movements',
                  'Cash shifts, payments, audit log, plans and invoices', 'Scheduled billing job',
                  'Staff management: schedules, attendance and rider settlements', '200+ automated tests, CI, HTTPS and nightly backups'],
    ),
    dict(
        slug='goal-line-report', order_in_showcase=3,
        defaults=dict(
            title='Goal Line Report — Content Management & Editorial Platform', status=Project.STATUS_LIVE, year=2025,
            kind='editorial', accent='#15803d', case_study=True, featured=True, published=True,
            live_url='https://goallinereport.com/',
            role='Backend engineer', client_type='Client work', duration='Delivered and live', team='Solo',
            summary=('A live editorial platform where stories move through Draft, Review, Approval and Published, with role-based access, '
                     'scheduled publishing and reader features like comments, likes and bookmarks.'),
            body=('Goal Line Report publishes sports stories to the public at goallinereport.com. Behind the site is a workflow that keeps writers, editors and the chief editor in their own lanes.\n\n'
                  'The back office is a customized Django admin using Jazzmin, with filters, search and bulk actions tuned for how an editorial desk actually works.'),
            challenge=('A newsroom cannot publish straight from a text box. Stories need drafting, review and sign-off, and only the right people may move a story forward. '
                       'A mistake here means unfinished or unapproved content going public.\n\n'
                       'Editors also need to plan ahead. Publishing at a set time must happen reliably, even when nobody is online.'),
            solution=('I modelled the workflow as explicit states (Draft, Review, Approval, Published) with permission checks on each transition. '
                      'Three roles map to the desk: Chief Editor, Editor and End User, and Django groups and permissions enforce what each can do.\n\n'
                      'Scheduled publishing runs on Celery, so a story set for a future time goes live without anyone clicking. '
                      'Stories support categories, tags, attachments and rich text through CKEditor. Readers get comments, likes, bookmarks, subscriptions and email notifications.\n\n'
                      'The admin is customized with Jazzmin, filters, search and actions so editors work through queues instead of scrolling lists.'),
            results=('Live in production at goallinereport.com\n'
                     'Four-stage editorial workflow with role-gated transitions\n'
                     'Scheduled publishing handled by background workers\n'
                     'Comments, likes, bookmarks, subscriptions and email notifications for readers'),
            metrics=('Draft → Published|4-stage review workflow\n'
                     '3|roles: Chief Editor, Editor, End User\n'
                     'Live|in production\n'
                     'Celery|scheduled publishing'),
            architecture=('Browser|readers and editors\n'
                          'Django + Bootstrap 5|public site and Jazzmin admin\n'
                          'Workflow layer|states and role permissions\n'
                          'PostgreSQL|stories, users, engagement\n'
                          'Celery|scheduled publishing and emails'),
            lessons=('Making workflow states explicit, rather than a "published" checkbox, kept the rules readable and made each new role cheap to add.\n\n'
                     'Tuning the admin for the editors\' daily queue mattered as much as the public pages, because that is where the team spends their day.'),
        ),
        tags=['Django', 'PostgreSQL', 'Celery', 'Jazzmin', 'CKEditor', 'Bootstrap 5'],
        features=['Draft, Review, Approval, Published workflow', 'Chief Editor, Editor and End User roles',
                  'Categories, tags, attachments and rich-text editing', 'Scheduled publishing via Celery',
                  'Comments, likes, bookmarks and subscriptions', 'Email notifications', 'Customized Jazzmin admin with filters, search and actions'],
    ),
    dict(
        slug='elecmech', order_in_showcase=4,
        defaults=dict(
            title='ElecMech — Engineering Services & Machinery Platform', status=Project.STATUS_LIVE, year=2025,
            kind='corporate', accent='#14532d', case_study=True, featured=True, published=True,
            live_url='https://elecmech.com.pk/',
            role='Full-stack developer', client_type='Client work', duration='Delivered and live', team='Solo',
            summary=('A live corporate website and machinery catalog for an engineering services company, with product inquiries, '
                     'WhatsApp ordering and automated email notifications.'),
            body=('ElecMech needed a site that explains what the company does and lets buyers ask about machinery without friction. '
                  'It is live at elecmech.com.pk.\n\n'
                  'The pages are responsive from phone to desktop and structured for search, with a project showcase that proves the work.'),
            challenge=('Industrial buyers rarely check out online. They ask questions, compare models and want a quick human reply, often on WhatsApp. '
                       'A standard shopping cart would have been the wrong tool.\n\n'
                       'The company also needed to be found. Machinery and services searches depend on clean, fast, crawlable pages.'),
            solution=('I built a machinery and industrial product catalog, and replaced the cart with a product inquiry flow plus a WhatsApp ordering link that opens with the product already filled in. '
                      'Inquiries are saved in the database and trigger an email through SMTP, so nothing depends on someone watching a chat.\n\n'
                      'Pages use semantic markup, sensible titles and descriptions and optimized assets for SEO and speed. Layouts were designed for desktop, tablet and mobile, '
                      'and a project showcase presents completed work.'),
            results=('Live in production at elecmech.com.pk\n'
                     'Machinery and industrial product catalog\n'
                     'Product inquiry and WhatsApp ordering integration\n'
                     'Automated email notifications for contact and inquiries\n'
                     'Responsive layouts and SEO-friendly pages'),
            metrics=('Live|in production\n'
                     '3|screen sizes designed: desktop, tablet, mobile\n'
                     'WhatsApp|ordering from any product page\n'
                     'SMTP|automatic inquiry emails'),
            architecture=('Visitor|search, phone or desktop\n'
                          'Django + Bootstrap 5|catalog and showcase pages\n'
                          'Inquiry flow|saved and emailed\n'
                          'MariaDB|products and inquiries\n'
                          'SMTP + WhatsApp|owner is notified immediately'),
            lessons=('Matching the checkout to how buyers really buy, by asking and chatting, mattered more than any feature on a shopping-cart checklist.\n\n'
                     'Storing every inquiry as well as emailing it gave the owner a record to follow up from.'),
        ),
        tags=['Django', 'MariaDB', 'Bootstrap 5', 'JavaScript', 'SMTP'],
        features=['Machinery and industrial product catalog', 'Product inquiry and WhatsApp ordering integration',
                  'Contact and inquiry management with automated email', 'Responsive desktop, tablet and mobile layouts',
                  'SEO-friendly pages and performance optimization', 'Project and portfolio showcase'],
    ),
]


class Command(BaseCommand):
    help = 'Create or update the flagship case studies (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite case studies that already have content.')

    def handle(self, *args, **options):
        for c in CASES:
            data = dict(c['defaults'], order_in_showcase=c['order_in_showcase'])
            current = Project.objects.filter(slug=c['slug']).first()
            if current and current.challenge and not options.get('force'):
                self.stdout.write(f"  case study kept (already written): {c['slug']}")
                continue
            project, created = Project.objects.update_or_create(slug=c['slug'], defaults=data)
            existing = {t.name for t in project.tags.all()}
            for name in c['tags']:
                if name not in existing:
                    ProjectTag.objects.create(project=project, name=name)
            project.features.all().delete()
            for i, text in enumerate(c['features'], start=1):
                ProjectFeature.objects.create(project=project, text=text, order=i)
            self.stdout.write(f"  case study {'created' if created else 'updated'}: {project.slug}")
