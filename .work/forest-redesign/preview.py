from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import create_app
from werkzeug.serving import run_simple
app = create_app({'TEMPLATES_AUTO_RELOAD': True})
run_simple('127.0.0.1', 5002, app, use_reloader=False, use_debugger=False, threaded=True)
