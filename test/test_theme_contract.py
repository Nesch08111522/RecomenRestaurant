"""Theme regressions independent of database, fonts, map providers and AI services."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def luminance(value):
    channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    return sum(v * weight for v, weight in zip(linear, [.2126, .7152, .0722]))


def test_semantic_text_palette_passes_aa_on_all_surfaces():
    css = (ROOT / 'static/css/theme-tokens.css').read_text(encoding='utf-8')
    for block in css.split('}')[:2]:
        tokens = dict(re.findall(r'--theme-([\w-]+):\s*(#[0-9a-f]{6});', block))
        for fg in ('text', 'muted', 'accent', 'success', 'warning', 'danger', 'info'):
            for bg in ('bg', 'surface', 'elevated', 'accent-bg', 'success-bg', 'warning-bg', 'danger-bg', 'info-bg'):
                a, b = sorted([luminance(tokens[fg]), luminance(tokens[bg])])
                assert (b + .05) / (a + .05) >= 4.5, (fg, bg)
        assert tokens['bg'] != '#000000'


def test_bootstrap_precedes_styles_in_both_documents():
    for template in ('base.html', 'sites/public.html'):
        text = (ROOT / 'templates' / template).read_text(encoding='utf-8')
        assert text.index("include 'partials/theme_head.html'") < text.index('<link')
        assert 'data-theme="dark"' in text
    bootstrap = (ROOT / 'templates/partials/theme_head.html').read_text(encoding='utf-8')
    assert bootstrap.index('<script>') < bootstrap.index('<link')
    for filename in ('static/js/theme.js', 'static/js/app.js', 'static/js/business-sites.js', 'static/js/shell.js'):
        text = (ROOT / filename).read_text(encoding='utf-8')
        assert 'prefers-color-scheme' not in text
        assert 'bs-editor-theme' not in text


def test_ui_has_no_literal_colors_outside_token_and_brand_data_sources():
    files = list((ROOT / 'static/css').glob('*.css')) + list((ROOT / 'templates').rglob('*.html')) + list((ROOT / 'static/js').rglob('*.js'))
    exceptions = {'theme-tokens.css', 'brand_defaults.html', 'food-scene.js'}
    literal = re.compile(r'#[\da-fA-F]{3,8}\b|\brgba?\(\s*\d|\b(?:fill|stroke)=[\"\'](?:white|black|red|green)[\"\']')
    for file in files:
        if file.name not in exceptions:
            text = file.read_text(encoding='utf-8')
            assert not literal.search(text), str(file.relative_to(ROOT))
            assert not re.search(r'var\(--[\w-]*var\(', text), str(file.relative_to(ROOT))


def test_theme_runtime_and_chart_refresh():
    subprocess.run(['node', str(ROOT / 'test/theme_runtime.cjs')], cwd=ROOT, check=True)
