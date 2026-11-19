# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, r"C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant")
os.chdir(r"C:\Users\Nancy Sandoval\Downloads\SISRESTAURANTE\RecomenRestaurant")
from dotenv import load_dotenv
load_dotenv(".env", override=False)
from models.user import UserModel
users = UserModel.all()
print("total users:", len(users))
for u in users:
    print({k: u.get(k) for k in ("id", "username", "role", "status") if k in u})
