"""Loopback-only HTTP smoke, no dotenv, credentials or database connections."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DATABASE_URL'] = ''
os.environ['SECRET_KEY'] = 'loopback-smoke-only-not-a-production-key'
for name in ('OPENROUTER_API_KEY', 'AI_API_KEY', 'GEMINI_API_KEY'):
    os.environ[name] = ''

from app import create_app
from config import Config
from werkzeug.serving import make_server
from threading import Thread
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

Config.DATABASE_URL = None
app = create_app({'TESTING': True, 'SECRET_KEY': os.environ['SECRET_KEY']})


def run():
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    print('Smoke URL:', base)
    checks = [('/auth/login', None, 200), ('/static/js/catalog-explore.js', None, 200),
              ('/informacion/privacidad', None, 200), ('/auth/api/favorites', None, 401),
              ('/api/catalog/compare?ids=1', None, 400),
              ('/api/ai/interpret', {'text':'cafe'}, 400),
              ('/explorar', None, 503), ('/api/search', {}, 503)]
    try:
        for path, body, expected in checks:
            request = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                              headers={'Content-Type':'application/json'} if body is not None else {})
            try:
                response = urlopen(request, timeout=10)
            except HTTPError as error:
                response = error
            assert response.code == expected, (path, response.code, expected)
            content = response.read()
            assert b'loopback-smoke-only-not-a-production-key' not in content
            print(response.code, path)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print('8 real HTTP checks passed; server stopped; DB intentionally unavailable')


if __name__ == '__main__':
    run()
