"""Dummy content for filling every section while you design and test. Remove with: manage.py seed_dummy --remove"""

CATEGORIES = ['Database', 'Security']

POSTS = [
    dict(title='Zero-downtime migrations in Django: the three-step rule', cat='Django', accent='#3452e8', days=210,
         tags='Django, PostgreSQL, Migrations',
         excerpt='Adding a column should never take the site down. The expand, backfill, contract pattern keeps deploys boring.',
         body="""A migration that locks a busy table is the fastest way to turn a normal deploy into an incident. I follow one rule: never change the shape of data and the code that reads it in the same release.

## Step 1: expand

Add the new column as nullable, or add the new table, and ship it on its own. Old code ignores it. New code can start writing to it.

```python
class Migration(migrations.Migration):
    operations = [
        migrations.AddField('order', 'shipping_status', models.CharField(max_length=20, null=True)),
    ]
```

## Step 2: backfill

Fill old rows in small batches from a management command, not inside the migration. A batch of a few thousand rows keeps locks short and lets you stop at any time.

- Order by primary key and resume from the last id.
- Sleep briefly between batches when the database is busy.
- Log progress so a restart is safe.

## Step 3: contract

Once every row is filled and nothing reads the old column, make the new one required and drop the old one in a later release. Two small deploys are safer than one clever one.

## What I check before every deploy

Run `sqlmigrate` and read the SQL. If you see an `ALTER TABLE` that rewrites the table or a `CREATE INDEX` without `CONCURRENTLY` on a large table, split it up first."""),
    dict(title='JWT and role-based access in DRF without the spaghetti', cat='Django', accent='#7c3aed', days=190,
         tags='DRF, JWT, Security',
         excerpt='Customer, seller and admin roles on one API. Put the rules in one place and every view stays short.',
         body="""When an API serves a web app and a mobile app with three kinds of users, permission checks tend to leak into every view. The fix is to make roles data, and permissions a small set of reusable classes.

## One source of truth for roles

Keep the role on the user model and put it inside the token as a claim. Views read `request.user.role`, never the raw token.

## Permission classes that read like English

```python
class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'seller'

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id
```

Combine them per view: `permission_classes = [IsSeller & IsOwner]`.

## Scope the queryset, not just the permission

A permission class answers yes or no. The queryset decides what exists for this user. Filtering in `get_queryset` stops a seller from even guessing another seller's order id.

## Short access tokens, rotating refresh tokens

Keep access tokens to minutes and rotate refresh tokens on use. Blacklist on logout. It costs one table and removes a whole class of stolen-token stories."""),
    dict(title='Postgres indexes: what I check before adding one', cat='Database', accent='#0e7490', days=170,
         tags='PostgreSQL, Performance, Indexes',
         excerpt='An index is a trade: faster reads, slower writes, more disk. Three questions decide whether it earns its place.',
         body="""Most slow endpoints are one missing index away from fast, and most slow writes are one unnecessary index away from slower. I ask three questions before adding any.

## 1. Which query, and how often?

Find the real query with `EXPLAIN (ANALYZE, BUFFERS)`. An index for a report that runs once a night is rarely worth it. An index for a list view hit thousands of times an hour almost always is.

## 2. What is the column order?

For a composite index, put the equality columns first and the range or sort column last.

```sql
CREATE INDEX CONCURRENTLY orders_seller_status_created
ON orders (seller_id, status, created_at DESC);
```

This serves `WHERE seller_id = ? AND status = ? ORDER BY created_at DESC` without a sort step.

## 3. Could a partial index do the job?

If 95% of rows are `status = 'done'` and you only query the open ones, index just those. The index is smaller and faster to maintain.

```sql
CREATE INDEX CONCURRENTLY orders_open ON orders (seller_id) WHERE status <> 'done';
```

## Clean up

Every few months, check `pg_stat_user_indexes` for indexes with zero scans. Dropping an unused index is a free speed-up for every write."""),
    dict(title='Writing API errors that frontend developers can actually use', cat='Django', accent='#0b8a70', days=150,
         tags='DRF, API design',
         excerpt='A status code and a vague message is not an error format. Give clients a stable code, a field and a human sentence.',
         body="""Frontend developers lose hours to errors like `{"detail": "Bad request"}`. A good error tells the client what to do next, and does it the same way on every endpoint.

## A shape worth standardising

```json
{
  "error": {
    "code": "stock_too_low",
    "message": "Only 2 left in stock.",
    "field": "quantity"
  }
}
```

- **code** is stable and machine readable. Clients switch on it.
- **message** is for people and can change or be translated.
- **field** lets a form highlight the right input.

## One exception handler

In DRF, set `EXCEPTION_HANDLER` once and convert validation errors, permission errors and your own domain errors into that shape. No view should format its own errors.

## Pick status codes on purpose

400 for bad input, 401 when not signed in, 403 when signed in but not allowed, 404 for missing, 409 for conflicts such as a duplicate order, 429 for rate limits. Clients can handle each kind differently.

## Test the errors

An error format is part of your API. Write tests that assert the code and the field, not only the status."""),
    dict(title='Rate limiting a public form without a third-party service', cat='Security', accent='#c2410c', days=125,
         tags='Security, Django, Spam',
         excerpt='A contact form invites bots. A honeypot, a per-IP limit and a short delay stop most of them with no extra service.',
         body="""A portfolio contact form gets spam within days of going live. You do not need a paid service to cut most of it.

## Layer 1: a honeypot

Add a field real people never see. If it arrives filled in, pretend everything worked and store nothing. Bots tend to fill every input.

## Layer 2: a limit per IP

Count recent submissions from the same address and refuse after a few per hour.

```python
recent = Message.objects.filter(
    ip_address=ip, created_at__gte=timezone.now() - timedelta(hours=1)
).count()
if recent >= 5:
    return JsonResponse({'ok': False}, status=429)
```

Behind a proxy, read the client address from the forwarded header, and only trust that header when you set it yourself.

## Layer 3: validate everything

Cap lengths, strip control characters and reject obvious junk. Never put user text into an email header.

## What not to do

Do not show different messages for "blocked" and "saved" to suspected bots. A silent success wastes their time and tells them nothing.

## Watch it

Keep a read-only view of rejected attempts for a week after launch. If real people are caught, loosen the limit."""),
    dict(title='From PythonAnywhere to a VPS: when the free tier stops being enough', cat='DevOps', accent='#4338ca', days=100,
         tags='Deployment, PythonAnywhere, VPS',
         excerpt='PythonAnywhere is a great first home for a Django site. Here are the signs it is time to move, and what the move involves.',
         body="""PythonAnywhere gets a Django project online in an afternoon, with HTTPS and a database included. For a portfolio it can be all you ever need. These are the signs that you have outgrown it.

## Signs it is time

- You need background workers, such as Celery, running all the time.
- You want a custom domain with free-tier traffic limits lifted.
- You need Redis, WebSockets or a task that runs longer than the platform allows.
- You want the same environment locally and in production.

## What changes on a VPS

You own the whole stack: Nginx in front, Gunicorn for Django, PostgreSQL for data, and systemd to keep processes alive.

```bash
sudo systemctl enable --now gunicorn
sudo nginx -t && sudo systemctl reload nginx
```

## Make the move boring

1. Put everything in environment variables first. No secrets in the repo.
2. Dump the database, restore it on the new server, and compare row counts.
3. Lower your DNS TTL a day early, then switch.
4. Keep the old site running for a week as a fallback.

## Docker helps

If the project already has a `Dockerfile` and a compose file, the VPS is just a machine that runs `docker compose up -d`. That is the real advantage of containers: moving is a copy and a command."""),
    dict(title='Django admin or a custom dashboard? How I decide', cat='Architecture', accent='#6a4bff', days=80,
         tags='Django, Admin, Product',
         excerpt='The Django admin is brilliant for staff. It is the wrong tool when the person editing content is not a developer.',
         body="""I use the Django admin on almost every project, and I replace it on some. The deciding factor is who will use it every day.

## Keep the admin when

- The users are developers or technical staff.
- The forms are mostly one model per page.
- You need it working today, not polished.

## Build a dashboard when

- The owner is not technical and needs plain language, not model names.
- Several screens should feel like one workflow, such as an inbox, a calendar and a report.
- You want analytics next to the content, so decisions happen in one place.

## What a custom dashboard costs

Authentication, permissions, forms, validation, lists, search and pagination, all of which the admin gives you free. Budget for them honestly.

## A middle path

Reuse Django's forms and models, keep one small registry that describes each editable resource, and generate the list and edit screens from it. Adding a new section becomes a few lines, and the design stays consistent.

## My rule

If a non-developer will log in weekly, build for them. If only you will, use the admin and spend the time elsewhere."""),
    dict(title='Structured logging that makes 3 a.m. incidents shorter', cat='DevOps', accent='#0f766e', days=55,
         tags='Logging, Observability, Django',
         excerpt='Plain text logs are fine until something breaks. A few fields on every line turn searching into answering.',
         body="""When production breaks, you read logs in a hurry. The difference between ten minutes and two hours is usually whether each line can be filtered.

## Log events, not sentences

Instead of `Payment failed for order 812`, write an event with fields.

```python
logger.warning('payment_failed', extra={'order_id': 812, 'provider': 'stripe', 'code': 'card_declined'})
```

You can now count failures by provider or find every line for one order.

## Add a request id to everything

Generate an id in middleware, attach it to the request and include it in every log line and in the response header. When a user reports a problem, ask for that id.

## Levels with meaning

- **ERROR** needs a human soon.
- **WARNING** is unusual but handled.
- **INFO** records business events: order placed, user signed up.
- **DEBUG** stays off in production.

## Keep secrets out

Never log passwords, tokens, full card numbers or whole request bodies. Log ids and lengths instead.

## Ship them somewhere searchable

Even a simple setup helps: write JSON lines, rotate files, and use a free tier of a log service. The habit matters more than the tool."""),
    dict(title='How I scope and price a fixed-price backend project', cat='Career', accent='#a16207', days=30,
         tags='Freelance, Contract, Process',
         excerpt='Fixed price works when the scope is written down. This is the checklist I use before I quote a number.',
         body="""Fixed-price work can go wrong in two ways: the client expects more than was agreed, or I underestimate. A written scope fixes both.

## 1. Write the outcome, not the tasks

"Customers can pay by card and see their order history" is an outcome. "Build a payment model" is a task. Outcomes are what a client can verify.

## 2. List what is out of scope

Admin panels, data migration, email design and mobile apps are the usual surprises. Naming them early avoids hard conversations later.

## 3. Break it into milestones

Three to five milestones, each with a demo and a payment. The client sees progress and I see money, and either side can pause cleanly.

## 4. Add a buffer

I add roughly 20 to 30 percent for unknowns such as third-party APIs and unclear requirements. The riskier the integration, the larger the buffer.

## 5. Agree how change works

Small tweaks inside a milestone are free. New features go on a list, are priced separately and are scheduled after the current milestone.

## When I say no to fixed price

If the requirements are still being discovered, I propose time and materials with weekly demos. Honest uncertainty beats a fake number."""),
]

PROJECTS = [
    dict(title='Orbit CRM — Lightweight Sales Pipeline', status='progress', year='2026', kind='saas',
         summary='A small CRM for freelancers: contacts, deals on a kanban board, reminders and weekly email summaries.',
         body='Orbit keeps a one-person sales pipeline in one place. Deals move across stages, every contact has a timeline, and a weekly summary shows what needs attention.',
         tags=['Django', 'DRF', 'PostgreSQL', 'Celery', 'Redis'],
         features=['Kanban pipeline with drag and drop', 'Contact timeline with notes and emails', 'Reminders sent by Celery', 'Weekly summary email', 'CSV import and export']),
    dict(title='LedgerLite — Invoicing API', status='live', year='2025', kind='tool',
         summary='A REST API for creating invoices, recording payments and exporting statements, built for small agencies.',
         body='LedgerLite handles the boring parts of billing: numbered invoices, tax lines, partial payments and PDF statements, behind a documented API.',
         tags=['Django', 'DRF', 'PostgreSQL', 'Docker'],
         features=['Sequential invoice numbers per client', 'Partial payments and credit notes', 'PDF statements', 'OpenAPI documentation', 'Token authentication with scopes']),
    dict(title='ShiftBoard — Staff Scheduling Tool', status='deployment', year='2025', kind='saas',
         summary='Weekly rosters for shops and clinics, with shift swaps, availability and overtime warnings.',
         body='ShiftBoard replaces spreadsheets for small teams. Managers build a roster in minutes, staff request swaps from their phones and the system flags overtime before it happens.',
         tags=['Django', 'HTMX', 'PostgreSQL', 'Tailwind'],
         features=['Drag and drop weekly roster', 'Availability and leave requests', 'Shift swap approvals', 'Overtime warnings', 'SMS and email reminders']),
]

EXPERIENCE = [
    dict(role='Freelance Django Developer', org='Self-employed', dates='2023 — 2025',
         points=['Built and deployed five client sites and APIs end to end', 'Set up Docker, Nginx and CI for every project', 'Handled support and fixes after launch']),
    dict(role='Junior Python Developer', org='Sample Software House', dates='2022 — 2023',
         points=['Shipped features in a Django monolith with a team of six', 'Wrote tests and reviewed pull requests', 'Reduced slow queries on the orders list page']),
    dict(role='Backend Intern', org='Sample Tech Labs', dates='2021 — 2022',
         points=['Built internal REST endpoints in Django REST Framework', 'Learned code review, Git flow and deployment basics']),
    dict(role='Open Source Contributor', org='Django community', dates='2021 — Present',
         points=['Fixed documentation and small bugs in Python packages', 'Answers questions in developer communities']),
]

MESSAGES = [
    ('Sara Malik', 'sara.malik@example.com', 'Hiring: Full-time role', 'Hi, we are hiring a Django backend engineer for a remote team. Could we schedule a call this week?'),
    ('Daniel Foster', 'daniel@example.com', 'Contract: API for mobile app', 'We need a REST API for a new mobile app. Roughly 8 weeks. What is your availability and rate?'),
    ('Hina Raza', 'hina.raza@example.com', 'Question about BTR Mall', 'Great case study. How did you handle splitting one order across several sellers?'),
    ('Omar Siddiqui', 'omar@example.com', 'Hiring: Contract role', 'Hello, a fintech startup in Dubai is looking for a contract Python developer. Are you open to that?'),
    ('Priya Nair', 'priya.nair@example.com', 'Freelance help with Celery', 'Our Celery tasks sometimes run twice. Could you review the setup for a day?'),
    ('Mark Ellis', 'mark.ellis@example.com', 'Feedback on your blog', 'Loved the migrations article. Would you consider writing about zero-downtime Redis upgrades?'),
    ('Ayesha Tariq', 'ayesha.t@example.com', 'Internship question', 'I am a student learning Django. Do you mentor or have any advice on a first project?'),
    ('Luca Bianchi', 'luca@example.com', 'Hiring: On-site role in Milan', 'We have an on-site backend position in Milan with relocation support. Can I send details?'),
]

SUBSCRIBERS = [
    'Ali Hassan', 'Fatima Noor', 'John Carter', 'Maria Gomez', 'Usman Tariq', 'Emma Wilson', 'Bilal Ahmed', 'Sofia Rossi',
    'Hamza Sheikh', 'Zara Khan', 'Noah Bennett', 'Aisha Iqbal', 'Liam Murphy', 'Maham Ali',
]
