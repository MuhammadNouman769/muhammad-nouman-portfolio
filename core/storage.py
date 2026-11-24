"""Static file storage that can never take a page down.

`CompressedManifestStaticFilesStorage` raises ``ValueError: Missing staticfiles
manifest entry`` (a 500 on every page that uses the file) whenever a template
references a static file that was added after the last ``collectstatic``.
This subclass falls back to the plain, un-hashed URL instead, so a forgotten
``collectstatic`` costs you cache-busting for a minute, not a broken site.
"""
from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            return name
