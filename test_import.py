# test_import.py
import sys
print("Python path:", sys.path)

try:
    from models.favorite import FavoriteModel
    print("✅ FavoriteModel importado correctamente")
    print("FavoriteModel.file_path:", FavoriteModel.file_path)
except ImportError as e:
    print("❌ Error importando FavoriteModel:", e)

try:
    from config import Config
    print("✅ Config importado correctamente")
    print("Config.FAVORITES_FILE:", Config.FAVORITES_FILE)
except ImportError as e:
    print("❌ Error importando Config:", e)