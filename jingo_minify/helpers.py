import os
import subprocess

from django.conf import settings

import jinja2
from jingo import register


try:
    from build import BUILD_ID_CSS, BUILD_ID_JS, BUILD_ID_IMG, BUNDLE_HASHES
except ImportError:
    BUILD_ID_CSS = BUILD_ID_JS = BUILD_ID_IMG = 'dev'
    BUNDLE_HASHES = {}

static_path_prefix = getattr(settings, 'STATIC_URL', None) or settings.MEDIA_URL
static_path = lambda *a: os.path.join(static_path_prefix, *a)


def _build_html(items, wrapping):
    """
    Wrap `items` in wrapping.
    """
    return jinja2.Markup("\n".join((wrapping % (static_path_prefix + item)
                                   for item in items)))


@register.function
def js(bundle, debug=settings.TEMPLATE_DEBUG, defer=False, async=False):
    """
    If we are in debug mode, just output a single script tag for each js file.
    If we are not in debug mode, return a script that points at bundle-min.js.
    """
    attrs = []

    if debug:
        items = settings.MINIFY_BUNDLES['js'][bundle]
    else:
        build_id = BUILD_ID_JS
        bundle_full = "js:%s" % bundle
        if bundle_full in BUNDLE_HASHES:
            build_id = BUNDLE_HASHES[bundle_full]
        items = ("js/%s-min.js?build=%s" % (bundle, build_id,),)

    attrs.append('src="%s"')

    if defer:
        attrs.append('defer')

    if async:
        attrs.append('async')

    string = '<script %s></script>' % ' '.join(attrs)
    return _build_html(items, string)


@register.function
def css(bundle, media=False, debug=settings.TEMPLATE_DEBUG):
    """
    If we are in debug mode, just output a single script tag for each css file.
    If we are not in debug mode, return a script that points at bundle-min.css.
    """
    if not media:
        media = getattr(settings, 'CSS_MEDIA_DEFAULT', "screen,projection,tv")

    if debug:
        items = []
        for item in settings.MINIFY_BUNDLES['css'][bundle]:
            if (item.endswith('.less') and
                getattr(settings, 'LESS_PREPROCESS', False)):
                build_less(item)
                items.append('%s.css' % item)
            else:
                items.append(item)
    else:
        build_id = BUILD_ID_CSS
        bundle_full = "css:%s" % bundle
        if bundle_full in BUNDLE_HASHES:
            build_id = BUNDLE_HASHES[bundle_full]

        items = ("css/%s-min.css?build=%s" % (bundle, build_id,),)

    return _build_html(items,
            '<link rel="stylesheet" media="%s" href="%%s" />' % media)


def build_less(item):
    path_css = static_path('%s.css' % item)
    path_less = static_path(item)

    updated_less = os.path.getmtime(static_path(item))
    updated_css = 0  # If the file doesn't exist, force a refresh.
    if os.path.exists(path_css):
        updated_css = os.path.getmtime(path_css)

    # Is the uncompiled version newer?  Then recompile!
    if updated_less > updated_css:
        with open(path_css, 'w') as output:
            subprocess.Popen([settings.LESS_BIN, path_less],
                             stdout=output)


def build_ids(request):
    """A context processor for injecting the css/js build ids."""
    return {'BUILD_ID_CSS': BUILD_ID_CSS, 'BUILD_ID_JS': BUILD_ID_JS,
            'BUILD_ID_IMG': BUILD_ID_IMG}
