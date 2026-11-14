from datetime import datetime, timedelta, timezone as dt_tz

from django.core.management.base import BaseCommand

from apps.blog.models import Category, Post

CATEGORIES = ['Django', 'Architecture', 'DevOps', 'Career']

POSTS = [
    dict(
        slug='tenant-isolation-in-django-without-schema-per-tenant', category='Architecture', accent='#3452e8',
        featured=True, days_ago=118,
        title='Tenant isolation in Django without schema-per-tenant',
        excerpt='How I keep one restaurant\'s data invisible to another in a shared-database SaaS: a scoped manager, one middleware, and tests that try to break it.',
        tags='Django, Multi-tenancy, Security, Testing',
        body='''When I built DineX, a subscription restaurant platform, every restaurant needed to see only its own orders, menu, staff and cash shifts. There are two common ways to do that in Django: a database schema per tenant, or one shared schema with a tenant column on every table. I chose the shared schema. It is simpler to migrate, simpler to back up, and cheap to run. The price is that **isolation becomes your code's job**, so it has to be hard to get wrong.

## Make the safe path the default

The biggest risk is a forgotten filter. If every view has to remember `.filter(restaurant=request.restaurant)`, one day somebody will not. So I moved the filter into the model layer.

```python
# tenancy.py
import contextvars

_current = contextvars.ContextVar("current_restaurant", default=None)

def set_current(restaurant):
    return _current.set(restaurant)

def get_current():
    return _current.get()


class TenantQuerySet(models.QuerySet):
    def for_current(self):
        restaurant = get_current()
        if restaurant is None:
            return self.none()          # fail closed
        return self.filter(restaurant=restaurant)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    def get_queryset(self):
        return super().get_queryset().for_current()
```

Two details matter here. First, with no tenant set the manager returns an empty queryset rather than everything. A bug then shows up as "no data", not as a data leak. Second, I use a `ContextVar` instead of a module global so concurrent requests and async code never see each other's tenant.

## Set the tenant in exactly one place

A small middleware resolves the restaurant from the authenticated user (or from the subdomain for the kiosk screens) and sets the context variable. It also resets it after the response, so a worker thread never carries a tenant into the next request.

```python
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current(resolve_restaurant(request))
        try:
            return self.get_response(request)
        finally:
            _current.reset(token)
```

Background jobs do not pass through middleware. Every Celery task that touches tenant data takes a `restaurant_id` argument and sets the context itself. I keep an unscoped manager named `all_tenants` for the few places that really need a cross-tenant view, such as the billing job, and I keep those places easy to grep.

## Enforce it at the database too

Application code can be bypassed by a raw query or a shell session. I add a composite foreign key habit: child rows (an order line, for example) store the restaurant too, and a check in `save()` refuses to attach a line to an order from another restaurant. Unique constraints include the tenant column, so two restaurants can both have a menu item called "Zinger Burger" without clashing.

## Write tests that try to break it

This is the part that gives me confidence. For every tenant-owned model I have a test that creates data for two restaurants and asserts that each one can only see its own.

```python
def test_orders_are_isolated(self):
    a, b = make_restaurant("A"), make_restaurant("B")
    OrderFactory(restaurant=a); OrderFactory(restaurant=b)

    set_current(a)
    self.assertEqual(Order.objects.count(), 1)

    set_current(None)
    self.assertEqual(Order.objects.count(), 0)   # fails closed
```

I also test the API layer: log in as restaurant A, request the URL of restaurant B's order by id, and expect a 404, not a 403. A 404 does not confirm that the object exists.

## What I would check in any multi-tenant codebase

- Is there a default scoped manager, or does every query rely on memory?
- What happens when no tenant is set: empty result or everything?
- Do background tasks and management commands set the tenant explicitly?
- Are unique constraints and indexes tenant-aware?
- Is there a test that proves one tenant cannot read another's rows, for every model?

Schema-per-tenant is a fine choice when you need hard separation for compliance. For most small SaaS products, a scoped manager plus honest tests gives you the isolation you need with far less operational weight.''',
    ),
    dict(
        slug='idempotent-celery-tasks-for-scheduled-publishing-and-billing', category='Django', accent='#12a8d0',
        featured=True, days_ago=96,
        title='Idempotent Celery tasks for scheduled publishing and billing',
        excerpt='Tasks run twice, late, or not at all. Here is how I write the ones behind scheduled publishing and subscription billing so a retry never does damage.',
        tags='Celery, Django, Reliability, Redis',
        body='''Two of my projects lean on scheduled work. Goal Line Report publishes stories at a chosen time after an editor approves them. DineX runs a billing job that charges restaurants on their plan's renewal date. Both look simple, and both go wrong in the same way: **the task runs twice**. A worker restarts mid-job, the broker redelivers, or someone presses "run now" while the schedule fires. If running twice means a duplicate invoice or a story published a second time, you have a bug.

The rule I follow: a task must be safe to run any number of times with the same input. That property is called idempotency.

## Pass ids, not objects

Send the primary key and re-read the row inside the task. The row may have changed since the task was queued, and you want the current truth.

```python
@shared_task(bind=True, max_retries=5, acks_late=True)
def publish_story(self, story_id):
    with transaction.atomic():
        story = Story.objects.select_for_update().get(pk=story_id)
        if story.status != Story.APPROVED:
            return "skipped"             # already published, or pulled back
        if story.publish_at > timezone.now():
            return "too early"           # schedule moved; a newer task owns it
        story.status = Story.PUBLISHED
        story.published_at = timezone.now()
        story.save(update_fields=["status", "published_at"])
    notify_subscribers.delay(story_id)
```

The status check is the idempotency. A second run finds the story already published and exits. `select_for_update` stops two workers from passing that check at the same moment.

## Use a unique key for money

Status flags are enough for publishing. For billing I want something stronger, so the database itself refuses a duplicate. Each billing period gets a unique constraint.

```python
class Invoice(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT)
    period_start = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "period_start"], name="one_invoice_per_period")
        ]
```

```python
def bill_restaurant(restaurant_id, period_start):
    try:
        with transaction.atomic():
            Invoice.objects.create(restaurant_id=restaurant_id, period_start=period_start, amount=...)
    except IntegrityError:
        return "already billed"
```

Even if the task fires ten times, one invoice exists. If you talk to an external payment provider, send an idempotency key derived from the same pair of values so the provider also ignores repeats.

## Make the scheduler a dispatcher, not a worker

The periodic task should only find work and queue small tasks, one per item. A single giant "bill everyone" task that fails at restaurant 40 leaves you guessing about the first 39. Small tasks retry on their own and show up clearly in logs.

```python
@shared_task
def dispatch_due_billing():
    today = timezone.localdate()
    for rid in Restaurant.objects.filter(next_billing_date__lte=today).values_list("id", flat=True):
        bill_restaurant.delay(rid, today)
```

## Retry only what can recover

Network errors and timeouts deserve a retry with backoff. A validation error will fail the same way every time, so let it fail loudly instead of retrying five times. I set `autoretry_for` to a narrow tuple of exceptions and `retry_backoff=True`.

## Checklist

- Tasks take ids and re-read the data.
- Every task has a "nothing to do" exit that returns safely.
- Anything involving money has a database-level uniqueness guarantee.
- The periodic task dispatches; it does not do the work.
- You have a test that calls the task twice and asserts a single outcome.

That last test is cheap and catches most of the real-world problems before production does.''',
    ),
    dict(
        slug='designing-a-multi-vendor-order-model', category='Architecture', accent='#6a4bff',
        featured=False, days_ago=74,
        title='Designing a multi-vendor order model: one order, many shipments',
        excerpt='A customer pays once, but three sellers ship three parcels. How I split orders into per-seller shipments in BTR Mall and keep each state machine honest.',
        tags='E-commerce, Django, Data modeling, REST',
        body='''BTR Mall is a multi-vendor marketplace in the spirit of Daraz or Amazon. The first design question is deceptively small: what is an order? A customer sees one checkout and one payment. But a cart with items from three sellers means three people packing three parcels on different days. If you model it as a single order with a single status, you cannot answer "has seller B shipped yet?" without hacks.

## Split into three levels

I model it in layers, each with its own job.

- **Order**: what the customer paid for. Owns the total, the payment, the delivery address and the customer-facing reference.
- **SubOrder** (one per seller): the seller's share. Owns that seller's items, subtotal, commission and fulfilment status.
- **Shipment**: a physical parcel for a sub-order, with a courier and tracking number. One sub-order can have more than one shipment if it ships in parts.

```python
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=20, default="pending")
    address_snapshot = models.JSONField()

class SubOrder(models.Model):
    order = models.ForeignKey(Order, related_name="sub_orders", on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="placed")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=12, decimal_places=2)

class OrderItem(models.Model):
    sub_order = models.ForeignKey(SubOrder, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)   # price at purchase time
    product_name = models.CharField(max_length=200)                      # snapshot
```

## Snapshot what must not change

Prices, product names and the delivery address change after purchase. The order must keep what the customer actually agreed to, so I copy those values onto the order rows instead of pointing at live product data. Reports and refunds later depend on this.

## Give each sub-order a state machine

Seller-side status moves through a small, explicit set of steps: `placed → confirmed → packed → shipped → delivered`, with `cancelled` and `returned` as side exits. I keep the allowed transitions in one dictionary and route every change through one method.

```python
TRANSITIONS = {
    "placed": {"confirmed", "cancelled"},
    "confirmed": {"packed", "cancelled"},
    "packed": {"shipped", "cancelled"},
    "shipped": {"delivered", "returned"},
}

def move_to(self, new_status):
    if new_status not in TRANSITIONS.get(self.status, set()):
        raise InvalidTransition(f"{self.status} -> {new_status}")
    self.status = new_status
    self.save(update_fields=["status"])
    self.order.refresh_overall_status()
```

Views and serializers never assign `status` directly. This single choke point also gives you one place to send notifications and write an audit row.

## Derive the customer-facing status

The customer does not see seven statuses per seller. The order computes a summary from its sub-orders: all delivered means "Delivered", a mix means "Partially shipped", and so on. Because it is derived, it can never disagree with the underlying data.

## Stock and money

Reserve stock when the order is placed, inside the same transaction, using `select_for_update` on the variant rows so two buyers cannot take the last unit. Keep commission on the sub-order so seller payouts are a plain sum over delivered sub-orders.

## Takeaways

Model the real-world units: payment, seller fulfilment and parcels are different things. Snapshot what the customer agreed to. Put transitions in one place. Derive summaries instead of storing them twice.''',
    ),
    dict(
        slug='redis-caching-in-drf-what-to-cache-and-how-to-invalidate', category='Django', accent='#0b8a70',
        featured=False, days_ago=52,
        title='Redis caching in DRF: what to cache and how to invalidate it',
        excerpt='Caching is easy to add and hard to trust. A practical approach for Django REST Framework: pick the right targets, key them well, and invalidate on write.',
        tags='Redis, DRF, Performance, Django',
        body='''Adding a cache to a Django REST Framework API takes ten minutes. Trusting it takes more thought. Stale prices, one user seeing another user's data, and "why is my change not showing" are the usual regrets. This is the approach I use on catalog-heavy projects such as a marketplace backend.

## Cache the right things

Not every endpoint deserves a cache. I look for responses that are **read often, change rarely and are identical for many users**: category trees, brand lists, product listing pages for anonymous visitors, site configuration. I do not cache carts, orders or anything shaped by the logged-in user unless the user id is part of the key.

Before caching, check the database first. A missing index or an N+1 query is better fixed than hidden. I use `select_related` and `prefetch_related`, and look at the query count with Django Debug Toolbar or `assertNumQueries`. A cache in front of a slow query is a slow query that is sometimes fast.

## Build keys you can reason about

A key should contain everything that changes the response: the resource, the query parameters, the language, and a version.

```python
from django.core.cache import cache

def category_tree_key():
    version = cache.get_or_set("catalog:version", 1, None)
    return f"catalog:v{version}:category-tree"
```

Putting a **version number** in the key gives you a cheap way to invalidate a whole family of keys at once: increment the version and all old keys become unreachable and expire on their own.

## Use the cache in the view

```python
class CategoryTreeView(APIView):
    def get(self, request):
        key = category_tree_key()
        data = cache.get(key)
        if data is None:
            data = CategorySerializer(Category.objects.roots().prefetch_related("children"), many=True).data
            cache.set(key, data, timeout=60 * 15)
        return Response(data)
```

For simple cases, `cache_page` with `vary_on_headers("Authorization")` or `vary_on_cookie` works too, but be careful: without the right `Vary`, a response built for one user can be served to another.

## Invalidate on write

A timeout alone means users wait up to fifteen minutes to see an edit. I invalidate when data changes, using signals kept in one module.

```python
@receiver([post_save, post_delete], sender=Category)
def bump_catalog_version(sender, **kwargs):
    try:
        cache.incr("catalog:version")
    except ValueError:
        cache.set("catalog:version", 1, None)
```

If a write happens inside a transaction, invalidate in `transaction.on_commit`. Otherwise a request can repopulate the cache with old data in the gap between your signal and the commit.

## Guard against a stampede

When a hot key expires, many requests may rebuild it at once. For expensive builds, take a short lock with `cache.add` (it only sets if the key is absent) and let one request rebuild while others serve slightly old data or wait briefly.

## Make caching observable

Log hit and miss counts, or at least expose them in a debug header in staging. If you cannot tell whether the cache is working, you will not notice when it stops.

## Checklist

- Fix slow queries first.
- Cache shared, rarely changing, read-heavy responses.
- Put resource, params and a version in every key.
- Invalidate on write, after the transaction commits.
- Never cache per-user responses under a shared key.
- Write one test that changes data and asserts the API shows the change.''',
    ),
    dict(
        slug='a-pragmatic-docker-compose-nginx-gunicorn-deployment-checklist', category='DevOps', accent='#f5b642',
        featured=False, days_ago=33,
        title='A pragmatic Docker Compose + Nginx + Gunicorn deployment checklist',
        excerpt='Not every Django app needs Kubernetes. The checklist I follow to put a small production service on a single VPS and still sleep at night.',
        tags='Docker, Nginx, Gunicorn, Deployment',
        body='''For a lot of client projects, a single virtual server running Docker Compose is the right amount of infrastructure. It is easy to understand, cheap, and fast to rebuild. I use the same shape for a corporate site such as ElecMech and for heavier API backends. This is the checklist, in the order I work through it.

## 1. Settings from the environment

No secrets in the repository. `SECRET_KEY`, database credentials, `ALLOWED_HOSTS` and email settings come from environment variables (I use python-decouple and a `.env` file that is never committed). `DEBUG` defaults to `False`, so forgetting to set it fails safe.

## 2. A small, boring image

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
RUN useradd -m app && chown -R app /app
USER app
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
```

Run as a non-root user. Install dependencies before copying the code so rebuilds use the layer cache. A common starting point for workers is two to four per CPU core; measure instead of guessing.

## 3. Compose the services

```yaml
services:
  web:
    build: .
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
    volumes: ["media:/app/media"]
    restart: unless-stopped
  db:
    image: postgres:16
    env_file: .env
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $POSTGRES_USER"]
      interval: 5s
      retries: 10
    restart: unless-stopped
  nginx:
    image: nginx:1.27
    ports: ["80:80", "443:443"]
    volumes: ["./deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro", "media:/media:ro"]
    depends_on: [web]
    restart: unless-stopped
volumes: { pgdata: {}, media: {} }
```

Named volumes keep the database and uploads when containers are replaced. `restart: unless-stopped` brings everything back after a reboot.

## 4. Let Nginx do what it is good at

Nginx terminates TLS, serves static files and media directly, sets security headers and proxies the rest to Gunicorn. Behind a proxy, tell Django to trust the forwarded protocol with `SECURE_PROXY_SSL_HEADER`, otherwise it thinks every request is plain HTTP and redirect loops follow. Use Let's Encrypt for certificates and set up renewal on day one.

## 5. Production Django switches

Run `python manage.py check --deploy` and read every warning. At minimum: secure cookies, HSTS once you are sure about HTTPS, `CSRF_TRUSTED_ORIGINS` for your domain, and a real email backend.

## 6. Backups you have restored

A nightly `pg_dump` copied off the server is the minimum. A backup you have never restored is a hope, not a backup, so I do one test restore into a scratch database before calling the project done.

## 7. Health and visibility

Add a `/health/` endpoint that touches the database. Point an uptime monitor at it. Make sure logs go to stdout so `docker compose logs` works, and rotate them so the disk does not fill.

## 8. A repeatable deploy

Pull, build, run migrations, restart:

```bash
git pull && docker compose build web
docker compose run --rm web python manage.py migrate
docker compose up -d
```

Write that into a short script so deploys are the same every time. When traffic outgrows one server, this setup moves cleanly to a bigger machine or an orchestrator, because everything is already containerised and configured by environment.''',
    ),
    dict(
        slug='what-i-look-for-when-reviewing-a-django-pull-request', category='Career', accent='#d1477a',
        featured=False, days_ago=14,
        title='What I look for when I review a Django pull request',
        excerpt='A hiring-manager-friendly view of how I read someone else\'s Django code: correctness, data safety, queries, tests and whether the next person can understand it.',
        tags='Code review, Django, Engineering practice, Teamwork',
        body='''Code review is where a team's standards actually live. When I review a Django pull request, I am not hunting for style nits; formatters and linters do that. I am asking whether this change is safe to ship and easy to live with. Here is the order I read in.

## 1. Understand the intent first

I read the description and the linked ticket before the diff. A good pull request says what changed and why, and how to check it. If I cannot explain the change in one sentence after reading the title, the change may be doing too many things. Small, focused pull requests get better reviews and cause fewer incidents.

## 2. Migrations and data safety

Anything touching models gets the most attention, because mistakes there are the hardest to undo.

- Is the migration reversible, and does it work on a table with real data?
- Adding a non-null column without a default will fail on existing rows.
- Does a data migration loop over millions of rows in memory?
- Are new foreign keys using sensible `on_delete` behaviour? `CASCADE` on the wrong relation can delete far more than intended.
- Are the right indexes and unique constraints present?

## 3. Queries

Django makes it easy to write code that looks fine and runs hundreds of queries. I look for loops that touch related objects without `select_related` or `prefetch_related`, `.all()` results that are counted with `len()` instead of `.count()`, and filters on unindexed columns in hot paths. For list endpoints I want pagination. If something looks suspicious, I ask for an `assertNumQueries` test rather than arguing from opinion.

## 4. Security and permissions

```python
# Suspicious: any logged-in user can read any order
order = Order.objects.get(pk=pk)

# Better: scope to what this user may see
order = get_object_or_404(Order.objects.filter(customer=request.user), pk=pk)
```

I check that every new endpoint has authentication and object-level permission checks, that user input goes through serializers or forms, that nothing builds SQL from strings, and that secrets and tokens are not logged. Returning 404 instead of 403 for other people's objects avoids leaking that they exist.

## 5. Transactions and background work

Multi-step writes that must succeed together belong in `transaction.atomic()`. Tasks queued from inside a transaction should use `transaction.on_commit`, otherwise a worker may run before the data is saved. Celery tasks should be safe to run twice.

## 6. Tests

I do not count lines of coverage; I look for the behaviour that would hurt if it broke. Is there a test for the unhappy path, such as a user without permission or an invalid payload? Does the test fail without the change? Tests that only assert the status code 200 tell me very little.

## 7. Readability

Names should say what things are. Business rules should live in one clear place (a model method or service function), not be repeated across views. Comments should explain why, not restate the code.

## How I word comments

I try to ask questions and explain impact: "What happens if two requests hit this at once?" is more useful than "this is wrong". I separate must-fix issues from suggestions, and I say what I liked, because reviewers who only criticise teach people to hide their work.

A pull request that is small, tested and honest about its trade-offs gets approved quickly. That is the kind of code I try to write, and the kind I enjoy reading.''',
    ),
]


class Command(BaseCommand):
    help = 'Seed blog categories and articles (idempotent: matched by slug).'

    def handle(self, *args, **options):
        cats = {}
        for i, name in enumerate(CATEGORIES, start=1):
            cats[name], _ = Category.objects.update_or_create(name=name, defaults={'order': i})
        base = datetime(2026, 11, 1, 9, 0, tzinfo=dt_tz.utc)
        for i, p in enumerate(POSTS, start=1):
            Post.objects.update_or_create(
                slug=p['slug'],
                defaults=dict(
                    title=p['title'], excerpt=p['excerpt'], body=p['body'], category=cats[p['category']],
                    tags=p['tags'], cover_accent=p['accent'], featured=p['featured'], published=True,
                    published_at=base - timedelta(days=p['days_ago']), order=i,
                    meta_description=p['excerpt'][:170],
                ),
            )
        self.stdout.write(f'  blog ready ({len(POSTS)} posts)')
