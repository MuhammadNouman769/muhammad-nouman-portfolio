from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.about.models import Profile, Education
from apps.experience.models import Experience, ExperienceHighlight
from apps.projects.models import Project, ProjectTag, ProjectFeature
from apps.services.models import Service
from apps.siteconfig.models import SiteSettings
from apps.skills.models import SkillCategory, Skill


class Command(BaseCommand):
    help = "Seed the database with Muhammad Nouman's portfolio content (idempotent)."

    def handle(self, *args, **options):
        SiteSettings.load()
        self.stdout.write('  site settings ready')
        self.seed_profile()
        self.seed_education()
        self.seed_experience()
        self.seed_projects()
        self.seed_services()
        self.seed_skills()
        from django.core.management import call_command
        call_command('seed_projects')
        call_command('seed_blog', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('Portfolio data seeded successfully.'))

    # ------------------------------------------------------------------
    def seed_profile(self):
        Profile.objects.get_or_create(
            id=1,
            defaults=dict(
                headline='Backend Engineer',
                bio_paragraph_1=(
                    "I'm a backend engineer specializing in Python, Django, and the Django REST "
                    "Framework, with a focus on building scalable, production-ready web applications. "
                    "My day-to-day work spans multi-vendor e-commerce platforms, content management "
                    "systems, authentication and authorization workflows, caching, and background "
                    "task processing."
                ),
                bio_paragraph_2=(
                    "Hands-on with PostgreSQL, Redis, Celery, Docker, JWT authentication, and Linux "
                    "deployment environments — I care about writing clean, maintainable code and "
                    "shipping systems that hold up in production, not just in a demo."
                ),
                bio_paragraph_3=(
                    "Alongside my engineering role, I run Xvera Labs, an independent software "
                    "practice where I take projects from requirements through architecture, "
                    "development, deployment, and client support."
                ),
            ),
        )
        self.stdout.write('  profile ready')

    def seed_education(self):
        rows = [
            ('BSIT', 'University of Education', '2020 — 2024', 1),
            ('FSC', 'Govt. Higher Secondary School, Farooqabad', '2018 — 2020', 2),
            ('Matric', 'Govt. High School, Village Butter', '2016 — 2018', 3),
        ]
        for degree, institution, date_range, order in rows:
            Education.objects.get_or_create(
                degree=degree, institution=institution,
                defaults=dict(date_range=date_range, order=order),
            )
        self.stdout.write('  education ready')

    def seed_experience(self):
        exp_data = [
            dict(
                role='Founder & CEO', organization='Xvera Labs',
                date_range='2026 — Present', order=1,
                highlights=[
                    'Founded an independent software practice delivering end-to-end digital solutions — e-commerce platforms, web apps, mobile apps, and custom software — for local clients across industries.',
                    'Own the full project lifecycle: requirements, architecture, development, deployment, and client support.',
                    'Built cross-platform mobile apps integrated with backend APIs, and currently developing a proprietary in-house product not yet publicly launched.',
                    'Handle client relationships, project timelines, and technical decision-making as founder.',
                ],
            ),
            dict(
                role='Python Backend Engineer', organization='TheTechFury',
                date_range='May 2025 — Present', order=2,
                highlights=[
                    'Design scalable, modular backend architectures using Django and DRF for e-commerce, content management, and corporate platforms.',
                    'Build secure RESTful APIs for web and mobile applications, with role-based access control and JWT authentication.',
                    'Work with PostgreSQL database design and the Django ORM.',
                    'Implement Redis caching and Celery background task processing.',
                    'Use Docker and Docker Compose across development and deployment environments.',
                    'Build and customize Django Admin dashboards and CMS workflows.',
                ],
            ),
        ]
        for data in exp_data:
            highlights = data.pop('highlights')
            exp, _ = Experience.objects.get_or_create(
                role=data['role'], organization=data['organization'],
                defaults=data,
            )
            if not exp.highlights.exists():
                for i, text in enumerate(highlights, start=1):
                    ExperienceHighlight.objects.create(experience=exp, text=text, order=i)
        self.stdout.write('  experience ready')

    def seed_projects(self):
        projects_data = [
            dict(
                title='BTR Mall — Multi-Vendor E-Commerce Platform', slug='btr-mall',
                status=Project.STATUS_PROGRESS, order=1,
                github_url='https://github.com/MuhammadNouman769/BTR-Mall',
                summary=(
                    'A scalable marketplace inspired by Daraz and Amazon: seller onboarding, product '
                    'catalog with categories, brands, variants and inventory, cart/wishlist/checkout/'
                    'order/shipment/delivery workflows, JWT auth with role-based access, Redis caching '
                    'and Celery background tasks, Dockerized environments, and Swagger-documented APIs '
                    'powering both a React web app and a React Native mobile app.'
                ),
                tags=['Django', 'DRF', 'PostgreSQL', 'Redis', 'Celery', 'Docker', 'React', 'React Native'],
            ),
            dict(
                title='XVeraLabs — Corporate Platform', slug='xveralabs',
                status=Project.STATUS_PROGRESS, order=2,
                github_url='https://github.com/MuhammadNouman769/xveralabs',
                summary=(
                    'Enterprise-grade corporate platform for a technology consulting brand, built on '
                    'Django with a clean, app-based architecture. Currently powers the public-facing '
                    'presence (marketing, services, portfolio, blogs, careers, authentication) and is '
                    'structured from day one to grow into a CRM, client dashboards, and API-driven '
                    'services.'
                ),
                tags=['Django', 'Django REST Framework', 'SQLite', 'PostgreSQL (planned)', 'HTML5/CSS3'],
            ),
            dict(
                title='Dinex POS — The MN Kitchen POS', slug='dinex-pos',
                status=Project.STATUS_PROGRESS, order=3,
                github_url='https://github.com/MuhammadNouman769/Dinex-pos',
                summary=(
                    'A multi-tenant, enterprise-grade restaurant management & POS platform: a Django '
                    'REST Framework backend serving Electron desktop, React web, and React Native '
                    'mobile clients. Modules cover organizations/locations, onboarding, catalog, '
                    'customers, orders, and inventory, secured with JWT (rotation + blacklist) and '
                    'documented via drf-spectacular.'
                ),
                tags=['Django', 'DRF', 'PostgreSQL', 'SimpleJWT', 'drf-spectacular', 'Electron', 'React', 'React Native'],
            ),
            dict(
                title='Goal Line Report — Content & Editorial Platform', slug='goal-line-report',
                status=Project.STATUS_LIVE, order=4,
                live_url='https://goallinereport.com/',
                summary=(
                    'A content platform for publishing stories and posts with a full editorial '
                    'workflow — draft, review, approval, publish — role-based access for chief '
                    'editors, editors, and end users, scheduled publishing via Celery, and a '
                    'Jazzmin-customized Django admin.'
                ),
                tags=['Django', 'PostgreSQL', 'Celery', 'Jazzmin', 'CKEditor', 'Bootstrap 5'],
            ),
            dict(
                title='Tahir Rafique Clothe House — Clothing E-Commerce', slug='tahir-rafique-clothe-house',
                status=Project.STATUS_PROGRESS, order=5,
                github_url='https://github.com/MuhammadNouman769/Tahirrafiqueclothehouse',
                summary=(
                    'A premium clothing e-commerce platform with a frictionless, account-free '
                    'WhatsApp checkout flow — session-based cart, multi-attribute variants (size, '
                    'color, fabric), and order details delivered straight to the store\'s WhatsApp '
                    'for confirmation. Built under a commercial agreement via BTR Solutions.'
                ),
                tags=['Django', 'Bootstrap 5', 'jQuery', 'SQLite/PostgreSQL'],
            ),
            dict(
                title='Hadi Sports — Sports E-Commerce Platform', slug='hadi-sports',
                status=Project.STATUS_DEPLOYMENT, order=6,
                github_url='https://github.com/MuhammadNouman769/hadisports',
                summary=(
                    'A sports retail e-commerce platform following the same WhatsApp-first checkout '
                    'model, extended with PDF receipt generation at checkout for a more complete '
                    'order-confirmation experience. Currently in its deployment phase.'
                ),
                tags=['Django', 'Bootstrap 5', 'PDF generation', 'SQLite/PostgreSQL'],
            ),
            dict(
                title='ElecMech — Engineering Services & Machinery Platform', slug='elecmech',
                status=Project.STATUS_LIVE, order=7,
                live_url='https://elecmech.com.pk/',
                summary=(
                    'A corporate website and machinery catalog for an engineering services company, '
                    'with a product inquiry and WhatsApp ordering integration, contact and inquiry '
                    'management, and automated email notifications.'
                ),
                tags=['Django', 'MariaDB', 'Bootstrap 5', 'JavaScript'],
            ),
        ]

        for data in projects_data:
            tags = data.pop('tags')
            project, _ = Project.objects.get_or_create(slug=data['slug'], defaults=data)
            if not project.tags.exists():
                for tag_name in tags:
                    ProjectTag.objects.create(project=project, name=tag_name)

        # ------------------------------------------------------------
        # Per-project feature/capability lists — separate from tags,
        # which stay as the short tech-stack pills.
        # ------------------------------------------------------------
        features_by_slug = {

            'btr-mall': [
                'Python', 'Django', 'Django REST Framework (DRF)', 'RESTful APIs',
                'API Design & Integration', 'Authentication & Authorization',
                'Role-Based Access Control (RBAC)', 'Database Design', 'Complex Business Logic',
                'Multi-vendor Marketplace', 'Product Management', 'Categories & Attributes',
                'Product Variants', 'Shopping Cart', 'Checkout', 'Order Management',
                'Order Status / Tracking', 'Inventory / Stock Management', 'Vendor Management',
                'Customer Management', 'Discounts / Coupons', 'Pricing & Promotions',
                'Reviews & Ratings', 'Wishlist', 'Search & Filtering',
                'Payment Gateway Integration', 'Payment Processing', 'Transaction Management',
                'Refund / Cancellation Logic', 'Invoicing', 'Commission / Vendor Settlement',
                'Relational Database Design', 'Database Optimization', 'Query Optimization',
                'Transactions', 'Data Validation', 'Scalable Backend Architecture',
                'REST APIs', 'Pagination', 'Filtering & Sorting', 'Search APIs',
                'File/Image Uploads', 'Notifications', 'Email/SMS Integrations',
                'Background Tasks', 'Third-party API Integration',
                'Admin Dashboard', 'Vendor Dashboard', 'Customer Dashboard',
                'Product & Inventory Administration', 'Order Administration', 'Reports & Analytics',
                'Git / Version Control', 'Debugging', 'Testing', 'Security',
                'Performance Optimization', 'Production Backend Development',
            ],

            'xveralabs': [
                'App-Based Modular Architecture', 'Marketing Homepage & Landing Experience',
                'Company Profile / About Us Suite', 'Careers & DEI Pages', 'Why-Choose-Us Section',
                'Service Catalog (Strategy & Consulting)',
                'Advanced Technology Services (RPA, IoT, Blockchain, AR/VR)',
                'SQA, Web & Product Development Service Lines', 'DevOps & Staff Augmentation Listings',
                'Project & Portfolio Showcase', 'Blog & Case-Study Content System',
                'FAQ, Privacy Policy & Terms Pages', 'User Authentication (Sign In / Sign Up)',
                'Django Admin Content Management', 'Contact & Lead-Capture Flow',
                'REST-Ready Backend Foundation (DRF)', 'Environment-Based Settings Structure',
                'Image Handling (Pillow)', 'Responsive Static-Asset-Driven UI',
                'CRM Layer (Planned)', 'Client Dashboard / Portal (Planned)',
                'Expanded API Surface for Headless/Mobile (Planned)',
                'CI/CD & Containerized Deployment (Planned)',
                'Analytics & Reporting Dashboards (Planned)',
            ],

            'dinex-pos': [
                'Multi-Tenant Architecture (Platform / Organization / Location)',
                'Custom User Model & Authentication', 'JWT Authentication',
                'Refresh Token Rotation & Blacklisting', 'Organization & Location Management',
                'Location-Level Staff & Membership Management', 'Guided Restaurant Onboarding Flow',
                'Product Catalog (Categories, Variants, Modifiers)', 'Dietary Tags', 'Deals & Promotions',
                'Location-Based Product Assignment', 'Customer Records & Tracking',
                'Order Lifecycle Management', 'Order Items & Table Management', 'Table Occupancy Tracking',
                'Order Statistics', 'Inventory / Stock Workflows', 'Analytics & Reporting Endpoints',
                'Custom Organization Middleware (Tenant Resolution)',
                'OpenAPI Schema Generation (drf-spectacular)', 'Swagger UI API Documentation',
                'Electron Desktop POS Terminal', 'React Web Admin Dashboard',
                'React Native Mobile App', 'Selectors / Validators / Serializers Layered Architecture',
            ],

            'goal-line-report': [
                'Story & Post Management', 'Categories & Tags', 'File Attachments',
                'Rich-Text Editing (CKEditor)', 'Editorial Workflow (Draft → Review → Approval → Published)',
                'Role-Based Access (Chief Editor, Editor, End User)',
                'Jazzmin-Customized Django Admin', 'Custom Admin Filters, Search & Actions',
                'Scheduled Publishing (Celery)', 'Automated Background Tasks',
                'Commenting System', 'Likes & Bookmarks', 'Subscriptions',
                'Email Notifications', 'Secure Authentication & Permission Management',
            ],

            'tahir-rafique-clothe-house': [
                'Curated Catalog (Trending, New Arrivals, Unstitched, Formals)',
                'Category-Based Filtering', 'Product Detail Pages with Variant Preview',
                'Live Product Search with Suggestions', 'Session-Based Cart (No Login Required)',
                'Multi-Attribute Variant Selection (Size, Color, Fabric)',
                'One-Tap WhatsApp Order Checkout', 'Quantity Adjustment at Checkout',
                'Fully Responsive Design (Mobile / Tablet / Desktop)',
                'SEO-Conscious Page Structure', 'Modular Product Data Model (Options, Variants, Images)',
                'Collection Sliders (Owl Carousel)', 'Testimonials Module',
            ],

            'hadi-sports': [
                'Sports Product Catalog with Category Browsing', 'Detailed Product Pages',
                'Product Search', 'Session-Based Shopping Cart',
                'Multiple Product Selection & Quantity Updates', 'WhatsApp Order Checkout',
                'PDF Receipt Generation at Checkout', 'Persistent Order Records (Dedicated Orders App)',
                'Fully Responsive, Mobile-Friendly Design', 'Modular Product Options & Variants',
            ],

            'elecmech': [
                'Machinery & Industrial Product Catalog', 'Product Inquiry Management',
                'WhatsApp Ordering Integration', 'Contact & Inquiry Management',
                'Automated Email Notifications', 'Responsive Layouts (Desktop / Tablet / Mobile)',
                'SEO-Friendly Pages & Performance Optimization', 'Project & Portfolio Showcase',
            ],
        }

        for slug, feature_list in features_by_slug.items():
            project = Project.objects.filter(slug=slug).first()
            if project and not project.features.exists():
                for i, feature in enumerate(feature_list, start=1):
                    ProjectFeature.objects.create(project=project, text=feature, order=i)

        self.stdout.write('  projects ready')

    def seed_services(self):
        services = [
            ('Strategy & Consulting', 'Technology roadmaps and consulting to align systems with business goals.'),
            ('AI Solutions & Engineering', 'Practical AI/ML features built into real products, not just prototypes.'),
            ('Cloud & DevOps', 'Cloud infrastructure, CI/CD, and deployment pipelines that scale.'),
            ('Cyber Security', 'Securing applications, APIs, and infrastructure against common threats.'),
            ('Custom Software Development', 'Bespoke software built around your exact workflow.'),
            ('Mobile App Development', 'Cross-platform apps with React Native, backed by solid APIs.'),
            ('E-Commerce Solutions', 'Multi-vendor marketplaces and storefronts, from catalog to checkout.'),
            ('Data & Analytics', 'Turning raw data into dashboards and decisions.'),
            ('UI/UX Design', 'Clean, usable interfaces designed around real user flows.'),
            ('ERP & CRM Solutions', 'Business systems for managing operations, leads, and clients.'),
            ('Custom Billing Software System', 'Billing and invoicing systems tailored to your business rules.'),
            ('IoT & Emerging Technologies', 'Connecting hardware and software for smarter systems.'),
            ('Quality Assurance', 'Testing practices that catch issues before your users do.'),
            ('Digital Transformation', 'Modernizing legacy processes into digital-first systems.'),
            ('IT Managed Services', 'Ongoing IT support so your systems keep running smoothly.'),
            ('Web & Portal Development', 'Corporate sites, portals, and dashboards built on Django.'),
            ('Blockchain Solutions', 'Blockchain-backed features where transparency and trust matter.'),
            ('Automation & RPA', 'Automating repetitive workflows with background tasks and bots.'),
            ('Staff Augmentation', 'Extending your team with backend and full-stack engineers.'),
            ('Support & Maintenance', 'Long-term support to keep production systems healthy.'),
        ]
        for i, (title, description) in enumerate(services, start=1):
            Service.objects.get_or_create(title=title, defaults=dict(description=description, order=i))
        self.stdout.write('  services ready')

    def seed_skills(self):
        data = {
            'Languages & Databases': ['Python', 'JavaScript', 'SQL', 'PostgreSQL', 'MariaDB', 'SQLite'],
            'Backend': ['Django', 'Django REST Framework', 'FastAPI', 'Django ORM', 'Django Signals'],
            'Background & Caching': ['Celery', 'Redis', 'Query Optimization'],
            'DevOps & Deployment': ['Docker', 'Docker Compose', 'Gunicorn', 'Nginx', 'Linux / Ubuntu', 'SSH'],
            'Auth & Security': ['JWT', 'Role-Based Access Control', 'Django Permissions & Groups'],
            'Tools & Frontend': ['Swagger / OpenAPI', 'Postman', 'Git / GitHub', 'Bootstrap 5', 'Tailwind CSS', 'CKEditor'],
            'Architecture & Practices': ['REST API Design', 'MVC / MVT', 'Modular Architecture', 'Code Refactoring', 'Logging'],
            'Admin & CMS': ['Django Admin', 'Jazzmin'],

            'E-Commerce / Marketplace': [
                'Multi-vendor Marketplace', 'Product Management', 'Categories & Attributes',
                'Product Variants', 'Shopping Cart', 'Checkout', 'Order Management',
                'Order Status / Tracking', 'Inventory / Stock Management', 'Vendor Management',
                'Customer Management', 'Discounts / Coupons', 'Pricing & Promotions',
                'Reviews & Ratings', 'Wishlist', 'Search & Filtering',
            ],
            'Payments & Commerce': [
                'Payment Gateway Integration', 'Payment Processing', 'Transaction Management',
                'Refund / Cancellation Logic', 'Invoicing', 'Commission / Vendor Settlement',
            ],
            'Database & Backend Architecture': [
                'Relational Database Design', 'Database Optimization', 'Query Optimization',
                'Transactions', 'Data Validation', 'Scalable Backend Architecture',
            ],
            'API / System Features': [
                'REST APIs', 'Pagination', 'Filtering & Sorting', 'Search APIs',
                'File/Image Uploads', 'Notifications', 'Email/SMS Integrations',
                'Background Tasks', 'Third-party API Integration',
            ],
            'Admin / Management': [
                'Admin Dashboard', 'Vendor Dashboard', 'Customer Dashboard',
                'Product & Inventory Administration', 'Order Administration', 'Reports & Analytics',
            ],
            'Engineering': [
                'Git / Version Control', 'Debugging', 'Testing', 'Security',
                'Performance Optimization', 'Production Backend Development',
            ],
        }
        for i, (cat_name, skills) in enumerate(data.items(), start=1):
            category, _ = SkillCategory.objects.get_or_create(name=cat_name, defaults=dict(order=i))
            if not category.skills.exists():
                for j, skill_name in enumerate(skills, start=1):
                    Skill.objects.create(category=category, name=skill_name, order=j)
        self.stdout.write('  skills ready')