# update_verified.py
from models.restaurant import RestaurantModel
import json
import os
from config import Config

# Cargar todos los restaurantes
restaurants = RestaurantModel.all()

# Actualizar cada restaurante con verified false si no existe
for r in restaurants:
    if 'verified' not in r:
        r['verified'] = False
        RestaurantModel.update(r['id'], r)
        print(f"✅ Actualizado: {r['name']} - verified: False")

print("✅ Todos los restaurantes actualizados")