from app import create_app
from utils.anchor_store import get_anchor_store
from utils.anchor_job import anchor_pending

app = create_app()
with app.app_context():
    print(anchor_pending(get_anchor_store()))