# test_import.py
import sys
print("Python path:", sys.path)

try:
    from models.favorite import FavoriteModel
    print("✅ FavoriteModel importado correctamente")
    print("Colección PostgreSQL:", FavoriteModel.collection)
except ImportError as e:
    print("❌ Error importando FavoriteModel:", e)

try:
    from config import Config
    print("✅ Config importado correctamente")
    print("Backend configurado:", Config.DATA_BACKEND)
except ImportError as e:
    print("❌ Error importando Config:", e)
