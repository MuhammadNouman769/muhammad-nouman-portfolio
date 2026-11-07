"""Registry that drives every content screen (list, add/edit, delete, reorder) in the dashboard."""
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from apps.about.models import Education, Profile
from apps.blog.models import Category, Post
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.services.models import Service
from apps.siteconfig.models import Banner, SiteSettings
from apps.skills.models import SkillCategory

from . import forms as f


@dataclass
class Resource:
    key: str
    model: type
    form: type
    label: str            # singular, e.g. "Project"
    plural: str
    icon: str
    columns: List[Tuple[str, Callable]]
    fieldsets: List[Tuple[str, str, List[str]]] = field(default_factory=list)  # (title, help, fields)
    formsets: List[Tuple[str, type, str, str, bool]] = field(default_factory=list)  # (related_name, class, title, help, ordered)
    toggles: List[str] = field(default_factory=list)
    reorder: bool = True
    singleton: bool = False
    public_url: Optional[Callable] = None
    blurb: str = ''

    def queryset(self):
        qs = self.model.objects.all()
        return qs


STATUS_PILL = {'live': 'ok', 'progress': 'warn', 'deployment': 'info'}

RESOURCES = {r.key: r for r in [
    Resource(
        key='projects', model=Project, form=f.ProjectForm, label='Project', plural='Projects', icon='layers',
        blurb='Everything shown on the Projects page and its detail pages. Drag rows to change the order visitors see.',
        columns=[('Project', lambda o: o.short_title), ('Status', lambda o: o.get_status_display()),
                 ('Stack', lambda o: ', '.join(t.name for t in o.tags.all()[:4]))],
        fieldsets=[
            ('Basics', 'This is what visitors and Google see first.', ['title', 'slug', 'summary', 'status']),
            ('Case study', 'Optional. Adds depth to the project page and helps search rankings.', ['role', 'year', 'body']),
            ('Links and cover', '', ['github_url', 'live_url', 'image']),
            ('Card on the site', 'How this project looks as a card on the home page, Projects page and More work. Everything is optional: empty fields fall back to the project name, summary and cover.', ['card_title', 'card_description', 'card_badge', 'card_image']),
            ('Full case study', 'Tick "case study" to feature this project in the showcase with the sections below.',
             ['case_study', 'order_in_showcase', 'kind', 'accent', 'client_type', 'duration', 'team']),
            ('Story', 'Challenge, solution and lessons: a blank line starts a new paragraph.', ['challenge', 'solution', 'lessons']),
            ('Proof', 'Results: one per line. Metrics: one per line as value|label (e.g. 200+|automated tests). Architecture: one per line, in flow order, as Label|detail (e.g. Caddy|HTTPS and routing).',
             ['results', 'metrics', 'architecture']),
            ('Visibility', '', ['published', 'featured']),
        ],
        formsets=[
            ('tags', f.ProjectTagFormSet, 'Tech stack', 'Short tags shown on the card, like Django or Redis.', False),
            ('features', f.ProjectFeatureFormSet, 'Capabilities', 'What the project does. One line each.', True),
        ],
        toggles=['published', 'featured'],
        public_url=lambda o: o.get_absolute_url() if o.published else None,
    ),
    Resource(
        key='blog', model=Post, form=f.PostForm, label='Post', plural='Blog posts', icon='book',
        blurb='Articles shown on the Blog page. Newest first; write in Markdown. Untick Published to keep a draft (you can still preview it while signed in).',
        columns=[('Title', lambda o: o.title), ('Category', lambda o: o.category.name if o.category else ''),
                 ('Date', lambda o: f'{o.published_at:%d %b %Y}'), ('Read', lambda o: f'{o.read_minutes} min')],
        fieldsets=[
            ('Article', 'Title, a short summary for cards and Google, then the text.', ['title', 'slug', 'excerpt', 'body']),
            ('Organise', '', ['category', 'tags', 'published_at']),
            ('Cover and search', 'Without an image a cover is generated from the accent colour.', ['cover_image', 'cover_accent', 'meta_description']),
            ('Visibility', '', ['published', 'featured']),
        ],
        toggles=['published', 'featured'], reorder=False,
        public_url=lambda o: o.get_absolute_url() if o.published else None,
    ),
    Resource(
        key='blog-categories', model=Category, form=f.CategoryForm, label='Category', plural='Blog categories', icon='layers',
        blurb='Groups for blog posts. Drag to change the order of the filter chips.',
        columns=[('Category', lambda o: o.name), ('Posts', lambda o: f'{o.posts.count()} posts')],
        fieldsets=[('Category', '', ['name', 'slug'])],
    ),
    Resource(
        key='skills', model=SkillCategory, form=f.SkillCategoryForm, label='Skill group', plural='Skills', icon='cpu',
        blurb='Group skills by theme. Drag groups to reorder them on the Skills page.',
        columns=[('Group', lambda o: o.name), ('Skills', lambda o: f'{o.skills.count()} items'),
                 ('Preview', lambda o: ', '.join(s.name for s in o.skills.all()[:5]))],
        fieldsets=[('Group', '', ['name'])],
        formsets=[('skills', f.SkillFormSet, 'Skills in this group', 'Add as many as you need.', True)],
    ),
    Resource(
        key='experience', model=Experience, form=f.ExperienceForm, label='Role', plural='Experience', icon='briefcase',
        blurb='Your work history, newest first. Highlights appear as bullet points under each role.',
        columns=[('Role', lambda o: o.role), ('Organisation', lambda o: o.organization), ('Dates', lambda o: o.date_range)],
        fieldsets=[('Role', '', ['role', 'organization', 'date_range'])],
        formsets=[('highlights', f.HighlightFormSet, 'Highlights', 'What you built or owned. One line each.', True)],
    ),
    Resource(
        key='services', model=Service, form=f.ServiceForm, label='Service', plural='Services', icon='grid',
        blurb='What clients can hire you for.',
        columns=[('Service', lambda o: o.title), ('Description', lambda o: o.description)],
        fieldsets=[('Service', '', ['title', 'description'])],
    ),
    Resource(
        key='banners', model=Banner, form=f.BannerForm, label='Banner', plural='Banners', icon='grid',
        blurb='Picture banners. "Home page" adds a moving slide to the home slider; any other page shows the picture in that page\'s banner. Drag to change the slide order.',
        columns=[('Page', lambda o: o.get_placement_display()), ('Headline', lambda o: o.title or '(no headline)'),
                 ('Shown', lambda o: 'Yes' if o.active else 'Hidden')],
        fieldsets=[
            ('Where it appears', 'Pick the page. Home slides rotate; other pages use the first active banner.', ['placement', 'active']),
            ('Picture', 'Wide pictures (16:10) look best.', ['image', 'accent']),
            ('Words (home slider)', 'Optional headline, short text and a button. Leave empty for a picture-only slide.', ['title', 'text', 'button_text', 'button_url']),
        ],
        toggles=['active'],
    ),
    Resource(
        key='education', model=Education, form=f.EducationForm, label='Education', plural='Education', icon='book',
        blurb='Shown at the bottom of the About page.',
        columns=[('Degree', lambda o: o.degree), ('Institution', lambda o: o.institution), ('Years', lambda o: o.date_range)],
        fieldsets=[('Education', '', ['degree', 'institution', 'date_range'])],
    ),
]}

SINGLETONS = {
    'profile': Resource(
        key='profile', model=Profile, form=f.ProfileForm, label='About text', plural='About text', icon='user',
        columns=[], singleton=True, reorder=False,
        blurb='The bio shown on the About page.',
        fieldsets=[('Bio', 'Three short paragraphs read better than one long one.', ['headline', 'bio_paragraph_1', 'bio_paragraph_2', 'bio_paragraph_3'])],
    ),
    'settings': Resource(
        key='settings', model=SiteSettings, form=f.SiteSettingsForm, label='Site settings', plural='Site settings', icon='sliders',
        columns=[], singleton=True, reorder=False,
        blurb='Name, hero text, contact details, social links and search settings. Changes go live immediately.',
        fieldsets=[
            ('Identity', '', ['owner_name', 'brand_short', 'role_title', 'company_name', 'company_role']),
            ('Home page hero', 'The first thing a visitor reads.', ['hero_heading', 'hero_text', 'available', 'availability_text', 'open_remote', 'open_onsite', 'open_contract', 'timezone_note', 'lamp_default_on']),
            ('Contact', 'Shown on the Contact page and in the footer.', ['email', 'phone', 'whatsapp', 'location']),
            ('Social', '', ['github', 'linkedin', 'x_twitter']),
            ('Search and sharing', 'Controls the Google snippet and link previews.', ['meta_title', 'meta_description', 'keywords', 'google_site_verification', 'bing_site_verification']),
            ('Files', '', ['portrait', 'og_image', 'resume']),
        ],
    ),
}
