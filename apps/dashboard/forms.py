import re

from django import forms
from django.forms import inlineformset_factory

from apps.about.models import Education, Profile
from apps.blog.models import Category, Post
from apps.books.models import Book
from apps.experience.models import Experience, ExperienceHighlight
from apps.projects.models import Project, ProjectFeature, ProjectTag
from apps.services.models import Service
from apps.siteconfig.models import Banner, SiteSettings
from apps.skills.models import Skill, SkillCategory

MAX_UPLOAD = 5 * 1024 * 1024


class StyledMixin:
    """Gives every widget the dashboard CSS classes so templates stay free of per-field markup."""

    def _style(self):
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs['class'] = 'switch'
            elif isinstance(w, (forms.FileInput, forms.ClearableFileInput)):
                w.attrs['class'] = 'file'
            elif isinstance(w, forms.Select):
                w.attrs['class'] = 'inp'
            elif isinstance(w, forms.HiddenInput):
                pass
            else:
                w.attrs['class'] = 'inp'


class DashModelForm(StyledMixin, forms.ModelForm):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()

    def _check_upload(self, name):
        f = self.cleaned_data.get(name)
        if f and hasattr(f, 'size') and f.size > MAX_UPLOAD:
            raise forms.ValidationError('File is larger than 5 MB. Compress it and try again.')
        return f


class ProjectForm(DashModelForm):
    class Meta:
        model = Project
        fields = ['title', 'slug', 'summary', 'body', 'role', 'year', 'status', 'github_url', 'live_url',
                  'image', 'card_title', 'card_description', 'card_badge', 'card_image', 'featured', 'published', 'case_study', 'kind', 'accent', 'client_type', 'duration', 'team',
                  'challenge', 'solution', 'results', 'metrics', 'architecture', 'lessons', 'order_in_showcase']
        widgets = {'summary': forms.Textarea(attrs={'rows': 4}), 'body': forms.Textarea(attrs={'rows': 8}),
                   'challenge': forms.Textarea(attrs={'rows': 7}), 'solution': forms.Textarea(attrs={'rows': 7}),
                   'results': forms.Textarea(attrs={'rows': 5}), 'metrics': forms.Textarea(attrs={'rows': 5}),
                   'architecture': forms.Textarea(attrs={'rows': 6}), 'lessons': forms.Textarea(attrs={'rows': 5}),
                   'accent': forms.TextInput(attrs={'type': 'color'})}

    clean_image = lambda self: self._check_upload('image')  # noqa: E731
    clean_card_image = lambda self: self._check_upload('card_image')  # noqa: E731

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('kind', 'accent', 'order_in_showcase'):
            self.fields[name].required = False

    def clean_kind(self):
        return self.cleaned_data.get('kind') or 'other'

    def clean_accent(self):
        import re
        v = (self.cleaned_data.get('accent') or '').strip()
        if not v:
            return '#3452e8'
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            raise forms.ValidationError('Use a hex colour like #3452e8.')
        return v

    def clean_order_in_showcase(self):
        return self.cleaned_data.get('order_in_showcase') or 0


class ProfileForm(DashModelForm):
    class Meta:
        model = Profile
        fields = ['headline', 'bio_paragraph_1', 'bio_paragraph_2', 'bio_paragraph_3']
        widgets = {f'bio_paragraph_{i}': forms.Textarea(attrs={'rows': 5}) for i in (1, 2, 3)}


class SiteSettingsForm(DashModelForm):
    class Meta:
        model = SiteSettings
        exclude = ['updated_at']
        widgets = {'hero_text': forms.Textarea(attrs={'rows': 4}), 'meta_description': forms.Textarea(attrs={'rows': 3})}

    clean_portrait = lambda self: self._check_upload('portrait')  # noqa: E731
    clean_og_image = lambda self: self._check_upload('og_image')  # noqa: E731
    clean_resume = lambda self: self._check_upload('resume')  # noqa: E731


class SkillCategoryForm(DashModelForm):
    class Meta:
        model = SkillCategory
        fields = ['name']


class ExperienceForm(DashModelForm):
    class Meta:
        model = Experience
        fields = ['role', 'organization', 'date_range']


class ServiceForm(DashModelForm):
    class Meta:
        model = Service
        fields = ['title', 'description']


class BannerForm(DashModelForm):
    class Meta:
        model = Banner
        fields = ['placement', 'title', 'text', 'image', 'button_text', 'button_url', 'accent', 'active']
        widgets = {'accent': forms.TextInput(attrs={'type': 'color'})}

    clean_image = lambda self: self._check_upload('image')  # noqa: E731

    def clean_accent(self):
        v = (self.cleaned_data.get('accent') or '#3452e8').strip()
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            raise forms.ValidationError('Use a hex colour like #3452e8.')
        return v

    def clean_button_url(self):
        v = (self.cleaned_data.get('button_url') or '').strip()
        if v and not (v.startswith('/') or v.startswith('https://') or v.startswith('http://')):
            raise forms.ValidationError('Start with / for a page on this site, or https:// for another site.')
        return v


class EducationForm(DashModelForm):
    class Meta:
        model = Education
        fields = ['degree', 'institution', 'date_range']


# ---- inline rows -------------------------------------------------
class RowForm(StyledMixin, forms.ModelForm):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()


def _fs(parent, child, fields, **kw):
    class _F(RowForm):
        class Meta:
            model = child
            fields = ()

    _F.Meta.fields = fields
    if 'order' in fields:
        _F.Meta.widgets = {'order': forms.HiddenInput()}
    return inlineformset_factory(parent, child, form=_F, fields=fields, extra=kw.pop('extra', 0), can_delete=True, **kw)


ProjectTagFormSet = _fs(Project, ProjectTag, ['name'])
ProjectFeatureFormSet = _fs(Project, ProjectFeature, ['text', 'order'])
SkillFormSet = _fs(SkillCategory, Skill, ['name', 'order'])
HighlightFormSet = _fs(Experience, ExperienceHighlight, ['text', 'order'])


class PostForm(DashModelForm):
    published_at = forms.DateTimeField(
        label='Publish date', input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'))

    class Meta:
        model = Post
        fields = ['title', 'slug', 'excerpt', 'body', 'category', 'tags', 'cover_image', 'cover_accent',
                  'meta_description', 'published_at', 'featured', 'published']
        widgets = {'excerpt': forms.Textarea(attrs={'rows': 3, 'maxlength': 220}),
                   'body': forms.Textarea(attrs={'rows': 22}),
                   'cover_accent': forms.TextInput(attrs={'type': 'color'})}

    clean_cover_image = lambda self: self._check_upload('cover_image')  # noqa: E731

    def clean_cover_accent(self):
        import re
        v = (self.cleaned_data.get('cover_accent') or '').strip()
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            raise forms.ValidationError('Use a hex colour like #3452e8.')
        return v.lower()


class CategoryForm(DashModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug']


class BookForm(DashModelForm):
    published_on = forms.DateField(label='Publication date', input_formats=['%Y-%m-%d'],
                                   widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    class Meta:
        model = Book
        fields = ['title', 'slug', 'subtitle', 'summary', 'description', 'category', 'language', 'pages', 'published_on',
                  'cover_image', 'cover_accent', 'pdf_file', 'featured', 'published']
        widgets = {'summary': forms.Textarea(attrs={'rows': 3, 'maxlength': 260}),
                   'description': forms.Textarea(attrs={'rows': 12}),
                   'cover_accent': forms.TextInput(attrs={'type': 'color'})}

    clean_cover_image = lambda self: self._check_upload('cover_image')  # noqa: E731

    def clean_cover_accent(self):
        v = (self.cleaned_data.get('cover_accent') or '').strip()
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            raise forms.ValidationError('Use a hex colour like #c2410c.')
        return v.lower()

    def clean_pdf_file(self):
        f = self.cleaned_data.get('pdf_file')
        if f and hasattr(f, 'size') and hasattr(f, 'read'):
            if not f.name.lower().endswith('.pdf'):
                raise forms.ValidationError('Please upload a PDF file (.pdf).')
            if f.size > 50 * 1024 * 1024:
                raise forms.ValidationError('PDF is larger than 50 MB. Compress it and try again.')
            head = f.read(5)
            f.seek(0)
            if head != b'%PDF-':
                raise forms.ValidationError('This file does not look like a valid PDF.')
        return f
