from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
p = ROOT / 'templates/index.html'
s = p.read_text(encoding='utf-8')
start = s.index("{% include 'partials/discover_hero.html' %}")
end = s.index('<!-- Recomendación Inteligente', start)
s = s[:start] + "{% include 'partials/forest_home.html' %}\n\n" + s[end:]
s = s.replace("{% include 'partials/discover_more.html' %}", "{% include 'partials/forest_extras.html' %}")
s = s.replace("{% block content %}", """{% block body_class %}sr-discover{% endblock %}
{% block page_styles %}
<link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url_for('static', filename='css/forest-home.css') }}">
{% endblock %}

{% block content %}""", 1)
s = s.replace("    function init() {\n", "    function init() {\n        if (document.getElementById('forest-map-panel')?.hidden || window.mapGL) return;\n", 1)
s = s.replace("    window.addEventListener('load', init);", "    window.addEventListener('load', init);\n    window.addEventListener('forest:map-open', init);")
s = s.replace("<!-- Asistente de IA (Qwen): búsqueda inteligente + chat -->", """{% for module in ['processor', 'logic-rules', 'ui', 'controller'] %}
<script src="{{ url_for('static', filename='js/forest/' ~ module ~ '.js') }}"></script>
{% endfor %}
<!-- Asistente de IA (Qwen): búsqueda inteligente + chat -->""")
p.write_text(s, encoding='utf-8')
p = ROOT / 'templates/partials/forest_home.html'
s = p.read_text(encoding='utf-8').replace('Descubre recetas y aprovecha los ingredientes de tu despensa.', 'Encuentra ingredientes y productos para preparar algo delicioso.')
s = s.replace("url_for('market.kitchen')", "url_for('market.browse', q='ingredientes')").replace('Explorar mi cocina', 'Ver ingredientes')
p.write_text(s, encoding='utf-8')
images = ROOT / 'static/images/forest'
for source, target, width in [('marine.jpg','marine-inspiration.webp',1000),('creole.jpg','creole-inspiration.webp',1000),('lunch.jpg','food-inspiration.webp',1000),('chef.png','chef-reference.webp',500),('shop.png','shop-reference.webp',600)]:
    im = Image.open(images/source)
    im.thumbnail((width, width))
    im.save(images/target, quality=88, method=6)
print('Portada integrada; recursos optimizados sin alterar los originales.')
