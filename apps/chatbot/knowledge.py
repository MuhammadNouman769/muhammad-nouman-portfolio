import math
import re
from dataclasses import dataclass

from django.core.cache import cache

from apps.about.models import Education, Profile
from apps.blog.models import Post
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.services.models import Service
from apps.siteconfig.models import SiteSettings
from apps.skills.models import SkillCategory


INDEX_CACHE_KEY = 'chatbot:knowledge:v1'
INDEX_CACHE_SECONDS = 60
WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*", re.IGNORECASE)
SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')
STOP_WORDS = {
    'a', 'about', 'am', 'an', 'and', 'any', 'are', 'as', 'at', 'be', 'been',
    'but', 'by', 'can', 'could', 'days', 'did', 'do', 'does', 'doing', 'for',
    'from', 'give', 'have', 'he', 'her', 'here', 'his', 'how', 'i', 'in',
    'is', 'it', 'its', 'me', 'my', 'now', 'of', 'on', 'or', 'our', 'she',
    'show', 'tell', 'that', 'the',
    'their', 'them', 'there', 'these', 'they', 'this', 'to', 'us', 'was',
    'we', 'were', 'what', 'when', 'where', 'which', 'who', 'why', 'will',
    'with', 'would', 'you', 'your',
}
PROJECT_COUNT_RE = re.compile(
    r'\bhow many\b.*\bprojects?\b|\bnumber of projects?\b|\bcount of projects?\b|'
    r'\bprojects?\s+(?:have been\s+)?(?:done|completed|finished)\b',
    re.IGNORECASE,
)
OFFICE_RE = re.compile(r'\b(?:office|on[- ]site|in[- ]person|physical workplace)\b', re.IGNORECASE)


def _project_count_answer():
    projects = Project.objects.filter(published=True)
    total = projects.count()
    live = projects.filter(status=Project.STATUS_LIVE).count()
    answer = f'There are {total} published projects on the portfolio, and {live} are marked Live. '
    answer += 'The portfolio does not track a separate completed-project count.'
    return {
        'answer': answer,
        'sources': [{'title': 'Projects', 'url': '/projects/'}],
    }


def _office_work_answer():
    current_roles = [
        experience for experience in Experience.objects.all()
        if re.search(r'\bpresent\b|current', experience.date_range, re.IGNORECASE)
    ]
    if current_roles:
        roles = '; '.join(
            f'{experience.role} at {experience.organization} ({experience.date_range})'
            for experience in current_roles
        )
        answer = f'The portfolio lists these current roles: {roles}. '
    else:
        answer = 'The portfolio does not list a current job or role. '

    answer += 'It does not say whether Nouman currently works from a physical office.'
    site = SiteSettings.objects.first()
    if site and site.open_onsite:
        answer += ' It does say he is open to on-site roles.'

    sources = []
    if current_roles:
        sources.append({'title': 'Experience', 'url': '/experience/'})
    if site and site.open_onsite:
        sources.append({'title': 'About', 'url': '/about/'})
    return {'answer': answer, 'sources': sources}


@dataclass(frozen=True)
class Document:
    title: str
    text: str
    url: str


def _clean(text):
    text = re.sub(r'```.*?```', ' ', text or '', flags=re.DOTALL)
    text = re.sub(r'!\[[^]]*]\([^)]*\)|\[([^]]+)]\([^)]*\)', r'\1', text)
    text = re.sub(r'[#>*_`~|]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _document(title, text, url):
    text = _clean(text)
    if title and text:
        return Document(title=title, text=text, url=url)
    return None


def _build_index():
    documents = []

    site = SiteSettings.objects.first()
    if site:
        documents.append(_document(
            'About ' + site.owner_name,
            ' '.join(filter(None, [
                site.role_title, site.company_name, site.company_role,
                site.hero_heading, site.hero_text, site.location,
                site.availability_text if site.available else 'Not currently available for new projects',
                site.timezone_note,
            ])),
            '/about/',
        ))

    for profile in Profile.objects.all():
        documents.append(_document(
            profile.headline,
            ' '.join((profile.bio_paragraph_1, profile.bio_paragraph_2, profile.bio_paragraph_3)),
            '/about/',
        ))
    for education in Education.objects.all():
        documents.append(_document(
            education.degree,
            f'{education.institution}. {education.date_range}',
            '/about/',
        ))
    for experience in Experience.objects.prefetch_related('highlights'):
        highlights = ' '.join(item.text for item in experience.highlights.all())
        documents.append(_document(
            experience.role,
            f'{experience.organization}. {experience.date_range}. {highlights}',
            '/experience/',
        ))

    projects = Project.objects.filter(published=True).prefetch_related('tags', 'features')
    for project in projects:
        tags = ' '.join(tag.name for tag in project.tags.all())
        features = ' '.join(feature.text for feature in project.features.all())
        details = ' '.join(filter(None, [
            project.summary, project.body, project.role, project.get_status_display(),
            str(project.year or ''), project.client_type, project.duration,
            project.challenge, project.solution, project.results, tags, features,
        ]))
        documents.append(_document(project.title, details, project.get_absolute_url()))

    posts = Post.objects.filter(published=True).select_related('category')
    for post in posts:
        details = ' '.join(filter(None, [
            post.excerpt, post.body, post.tags,
            post.category.name if post.category else '',
        ]))
        documents.append(_document(post.title, details, post.get_absolute_url()))

    for service in Service.objects.all():
        documents.append(_document(service.title, service.description, '/services/'))

    for category in SkillCategory.objects.prefetch_related('skills'):
        skills = ', '.join(skill.name for skill in category.skills.all())
        documents.append(_document(category.name, skills, '/skills/'))

    return tuple(document for document in documents if document)


def _get_index():
    index = cache.get(INDEX_CACHE_KEY)
    if index is None:
        index = _build_index()
        cache.set(INDEX_CACHE_KEY, index, INDEX_CACHE_SECONDS)
    return index


def answer_question(question):
    if PROJECT_COUNT_RE.search(question):
        return _project_count_answer()
    if OFFICE_RE.search(question):
        return _office_work_answer()

    site = SiteSettings.objects.first()
    owner_words = {
        word.lower() for word in WORD_RE.findall(site.owner_name)
    } if site else set()
    query_words = {
        word.lower() for word in WORD_RE.findall(question)
        if word.lower() not in STOP_WORDS and word.lower() not in owner_words and len(word) > 1
    }
    if not query_words:
        return {
            'answer': 'Please ask a question about the portfolio, projects, services, experience, skills, or articles.',
            'sources': [],
        }

    documents = _get_index()
    document_words = [
        {word.lower() for word in WORD_RE.findall(document.title + ' ' + document.text)}
        for document in documents
    ]
    document_frequency = {
        word: sum(word in words for words in document_words)
        for word in query_words
    }
    query_weights = {
        word: 1 + math.log1p(len(documents) / (1 + document_frequency[word]))
        for word in query_words
    }
    total_query_weight = sum(query_weights.values())
    matches = []
    for document, all_words in zip(documents, document_words):
        title_words = {word.lower() for word in WORD_RE.findall(document.title)}
        sentences = [sentence.strip() for sentence in SENTENCE_RE.split(document.text) if sentence.strip()]
        ranked_sentences = []
        for sentence in sentences:
            sentence_words = {word.lower() for word in WORD_RE.findall(sentence)}
            hits = query_words & sentence_words
            if hits:
                ranked_sentences.append((len(hits), sentence))
        if not ranked_sentences:
            continue

        title_hits = query_words & title_words
        content_hits = query_words & all_words
        hit_count = len(title_hits | content_hits)
        matched_weight = sum(query_weights[word] for word in title_hits | content_hits)
        coverage = matched_weight / total_query_weight
        score = coverage + sum(query_weights[word] for word in title_hits) / total_query_weight
        selected = sorted(ranked_sentences, key=lambda match: match[0], reverse=True)[:2]
        excerpt = ' '.join(sentence for _, sentence in selected)[:600].rsplit(' ', 1)[0]
        matches.append((score, hit_count, document, excerpt))

    matches.sort(key=lambda match: (match[0], match[1]), reverse=True)
    minimum_matches = 2 if len(query_words) >= 3 else 1
    if not matches or matches[0][1] < minimum_matches or matches[0][0] < 0.35:
        return {
            'answer': "I couldn't find that information in the public portfolio content. Try asking about a project, skill, service, experience, or article.",
            'sources': [],
        }

    _, _, document, excerpt = matches[0]
    return {
        'answer': f'{document.title}: {excerpt}',
        'sources': [{'title': document.title, 'url': document.url}],
    }
