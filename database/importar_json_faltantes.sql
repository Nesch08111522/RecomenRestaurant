-- Importa los JSON complementarios a restaurantes. Ejecutar app_records.sql primero.
-- Los registros existentes conservan su versión actual.
BEGIN;
LOCK TABLE public.app_records IN SHARE ROW EXCLUSIVE MODE;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "restaurant",
    "resource_id": 12,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "action": "approve",
      "status": "APROBADO_AUTOMATICAMENTE",
      "moderation_id": 1,
      "has_notes": true
    },
    "created_at": "2026-10-14T17:13:30.963285+00:00",
    "id": 1
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "moderation_batch",
    "resource_id": null,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "total_checked": 24,
      "flagged": 24,
      "action": "preliminary_filter"
    },
    "created_at": "2026-10-14T05:40:34.579932+00:00",
    "id": 2
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "moderation_batch",
    "resource_id": null,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "total_checked": 24,
      "flagged": 24,
      "action": "preliminary_filter"
    },
    "created_at": "2026-10-14T05:40:37.588687+00:00",
    "id": 3
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_USER_DELETE",
    "resource_type": "user",
    "resource_id": 4,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "username": "enriqeu"
    },
    "created_at": "2026-10-15T16:27:41.295228+00:00",
    "id": 4
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "restaurant",
    "resource_id": 27,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "action": "approve",
      "status": "APROBADO_AUTOMATICAMENTE",
      "moderation_id": 25,
      "has_notes": true
    },
    "created_at": "2026-10-15T17:07:11.088036+00:00",
    "id": 5
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "restaurant",
    "resource_id": 25,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "action": "approve",
      "status": "APROBADO_AUTOMATICAMENTE",
      "moderation_id": 15,
      "has_notes": true
    },
    "created_at": "2026-10-15T18:49:12.539308+00:00",
    "id": 6
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "restaurant",
    "resource_id": 28,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "action": "approve",
      "status": "APROBADO_AUTOMATICAMENTE",
      "moderation_id": 26,
      "has_notes": true
    },
    "created_at": "2026-10-15T18:51:06.878243+00:00",
    "id": 7
  },
  {
    "actor_user_id": 1,
    "action": "ADMIN_APPROVAL_DECISION",
    "resource_type": "restaurant",
    "resource_id": 29,
    "request_id": "",
    "ip_hash": "d72a839cb92de3ab9ec176ff6eeda8cad7beccc49644145534bcbee43644ace1",
    "metadata": {
      "action": "approve",
      "status": "APROBADO_AUTOMATICAMENTE",
      "moderation_id": 27,
      "has_notes": true
    },
    "created_at": "2026-10-15T18:55:31.833397+00:00",
    "id": 8
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'audit_events', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'audit_events' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "id": 1,
    "slug": "cevicheria",
    "name": "Cevichería",
    "icon": "waves",
    "image_url": "https://images.unsplash.com/photo-1535450710542-3756993a6240?q=80&w=500"
  },
  {
    "id": 2,
    "slug": "polleria",
    "name": "Pollería",
    "icon": "restaurant",
    "image_url": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?q=80&w=500"
  },
  {
    "id": 3,
    "slug": "italiana",
    "name": "Italiana",
    "icon": "local_pizza",
    "image_url": "https://images.unsplash.com/photo-1574071318508-1cdbad80ad38?q=80&w=500"
  },
  {
    "id": 4,
    "slug": "chifa",
    "name": "Chifa",
    "icon": "rice_bowl",
    "image_url": "https://images.unsplash.com/photo-1512058560366-cd24270083cd?q=80&w=500"
  },
  {
    "id": 5,
    "slug": "criolla",
    "name": "Criolla",
    "icon": "soup_kitchen",
    "image_url": "https://images.unsplash.com/photo-1589113103553-4958034060ee?q=80&w=500"
  },
  {
    "id": 6,
    "slug": "parrillas",
    "name": "Parrillas",
    "icon": "outdoor_grill",
    "image_url": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?q=80&w=500"
  },
  {
    "id": 7,
    "slug": "cafe",
    "name": "Café",
    "icon": "local_cafe",
    "image_url": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=500"
  },
  {
    "id": 8,
    "slug": "saludable",
    "name": "Saludable",
    "icon": "eco",
    "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=500"
  },
  {
    "id": 9,
    "slug": "japonesa",
    "name": "Japonesa",
    "icon": "set_meal",
    "image_url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=500"
  },
  {
    "id": 10,
    "slug": "mexicana",
    "name": "Mexicana",
    "icon": "taco",
    "image_url": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?q=80&w=500"
  },
  {
    "name": "Prueba",
    "slug": "cevicheria",
    "icon": "pizza",
    "image_url": "",
    "id": 11
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'categories', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'categories' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "id": 1,
    "restaurant_id": 1,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 2,
        "name": "Ceviche de Pescado",
        "price": 32
      },
      {
        "dish_id": 5,
        "name": "Arroz con Pato",
        "price": 40
      },
      {
        "dish_id": 1,
        "name": "Cabrito a la Norteña",
        "price": 35
      },
      {
        "dish_id": 6,
        "name": "Papa a la Huancaína",
        "price": 22
      },
      {
        "dish_id": 9,
        "name": "Suspiro a la Limeña",
        "price": 15
      }
    ],
    "specials": [
      "Pescado del día",
      "Sopa del día"
    ],
    "price": 45,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 2,
    "restaurant_id": 1,
    "date": "2026-07-01",
    "day_of_week": "martes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 3,
        "name": "Seco de Cabrito",
        "price": 38
      },
      {
        "dish_id": 4,
        "name": "Sopa Criolla",
        "price": 18
      },
      {
        "dish_id": 8,
        "name": "Lomo Saltado",
        "price": 35
      },
      {
        "dish_id": 7,
        "name": "Causa Rellena",
        "price": 25
      },
      {
        "dish_id": 12,
        "name": "Arroz con Leche",
        "price": 12
      }
    ],
    "specials": [
      "Cabrito al horno",
      "Crema de espárragos"
    ],
    "price": 42,
    "is_active": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 3,
    "restaurant_id": 2,
    "date": "2026-06-30",
    "day_of_week": "tuesday",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 19,
        "name": "Pulpo al Olivo",
        "price": 38
      },
      {
        "dish_id": 18,
        "name": "Chilcano de Pescado",
        "price": 35
      },
      {
        "dish_id": 20,
        "name": "Tortilla de Mariscos",
        "price": 30
      },
      {
        "dish_id": 17,
        "name": "Sudado de Pescado",
        "price": 42
      },
      {
        "dish_id": 16,
        "name": "Ceviche Mixto",
        "price": 48
      },
      {
        "dish_id": 14,
        "name": "Arroz con Mariscos",
        "price": 50
      },
      {
        "dish_id": 21,
        "name": "Camarones al Ajo",
        "price": 35
      },
      {
        "dish_id": 13,
        "name": "Ceviche de Pescado",
        "price": 45
      },
      {
        "dish_id": 25,
        "name": "Torta de Chocolate",
        "price": 15
      },
      {
        "dish_id": 24,
        "name": "Chicha de Jora",
        "price": 8
      },
      {
        "dish_id": 23,
        "name": "Pisco Sour de Maracuyá",
        "price": 18
      }
    ],
    "specials": [
      "Recomendación del chef"
    ],
    "price": 0,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00",
    "updated_at": "2026-06-30T17:16:29.685478"
  },
  {
    "id": 4,
    "restaurant_id": 2,
    "date": "2026-07-02",
    "day_of_week": "jueves",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 17,
        "name": "Sudado de Pescado",
        "price": 42
      },
      {
        "dish_id": 18,
        "name": "Chilcano de Pescado",
        "price": 35
      },
      {
        "dish_id": 21,
        "name": "Camarones al Ajo",
        "price": 35
      },
      {
        "dish_id": 19,
        "name": "Pulpo al Olivo",
        "price": 38
      },
      {
        "dish_id": 20,
        "name": "Tortilla de Mariscos",
        "price": 30
      }
    ],
    "specials": [
      "Ceviche de conchas negras",
      "Arroz con pato"
    ],
    "price": 50,
    "is_active": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 5,
    "restaurant_id": 3,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 26,
        "name": "Seco de Res",
        "price": 30
      },
      {
        "dish_id": 27,
        "name": "Tallarín Saltado",
        "price": 25
      },
      {
        "dish_id": 29,
        "name": "Rocoto Relleno",
        "price": 28
      },
      {
        "dish_id": 30,
        "name": "Sopa de Pollo",
        "price": 18
      },
      {
        "dish_id": 31,
        "name": "Ensalada Mixta",
        "price": 15
      }
    ],
    "specials": [
      "Guiso de quinua",
      "Jugo de frutas"
    ],
    "price": 35,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 6,
    "restaurant_id": 4,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 35,
        "name": "Pizza Margherita",
        "price": 25
      },
      {
        "dish_id": 36,
        "name": "Pizza Pepperoni",
        "price": 28
      },
      {
        "dish_id": 38,
        "name": "Pizza 4 Quesos",
        "price": 30
      },
      {
        "dish_id": 39,
        "name": "Pizza Vegetariana",
        "price": 26
      },
      {
        "dish_id": 43,
        "name": "Tiramisú",
        "price": 14
      }
    ],
    "specials": [
      "Pizza del día",
      "Lasagna"
    ],
    "price": 30,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 7,
    "restaurant_id": 5,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 45,
        "name": "Chaufa de Pollo",
        "price": 20
      },
      {
        "dish_id": 46,
        "name": "Chaufa de Carne",
        "price": 22
      },
      {
        "dish_id": 47,
        "name": "Chaufa de Mariscos",
        "price": 25
      },
      {
        "dish_id": 48,
        "name": "Wantán Frito",
        "price": 15
      },
      {
        "dish_id": 49,
        "name": "Sopa Wantán",
        "price": 16
      }
    ],
    "specials": [
      "Arroz chifa",
      "Té de jengibre"
    ],
    "price": 28,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 8,
    "restaurant_id": 6,
    "date": "2026-06-30",
    "day_of_week": "tuesday",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 59,
        "name": "Miso Soup",
        "price": 12
      },
      {
        "dish_id": 55,
        "name": "Tempura de Camarón",
        "price": 32
      },
      {
        "dish_id": 58,
        "name": "Gyoza",
        "price": 18
      },
      {
        "dish_id": 56,
        "name": "Ramen Tradicional",
        "price": 35
      },
      {
        "dish_id": 60,
        "name": "Sake",
        "price": 25
      },
      {
        "dish_id": 61,
        "name": "Té Verde",
        "price": 8
      }
    ],
    "specials": [
      "Recomendación del chef"
    ],
    "price": 0,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00",
    "updated_at": "2026-06-30T17:50:33.289715"
  },
  {
    "id": 9,
    "restaurant_id": 7,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 62,
        "name": "Lomo Fino a la Parrilla",
        "price": 60
      },
      {
        "dish_id": 63,
        "name": "Costillar de Cerdo",
        "price": 55
      },
      {
        "dish_id": 64,
        "name": "Parrilla Mixta",
        "price": 65
      },
      {
        "dish_id": 65,
        "name": "Ensalada César",
        "price": 20
      },
      {
        "dish_id": 66,
        "name": "Puré de Papas",
        "price": 12
      }
    ],
    "specials": [
      "Torta de queso",
      "Vino tinto"
    ],
    "price": 50,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 10,
    "restaurant_id": 8,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 70,
        "name": "Café Americano",
        "price": 8
      },
      {
        "dish_id": 71,
        "name": "Café Latte",
        "price": 12
      },
      {
        "dish_id": 72,
        "name": "Capuchino",
        "price": 14
      },
      {
        "dish_id": 73,
        "name": "Torta de Zanahoria",
        "price": 14
      },
      {
        "dish_id": 75,
        "name": "Sándwich de Pollo",
        "price": 16
      }
    ],
    "specials": [
      "Alfajores",
      "Sándwich del día"
    ],
    "price": 20,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 11,
    "restaurant_id": 9,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 76,
        "name": "Ensalada Quinoa",
        "price": 22
      },
      {
        "dish_id": 77,
        "name": "Bowl de Frutas",
        "price": 18
      },
      {
        "dish_id": 78,
        "name": "Smoothie Verde",
        "price": 15
      },
      {
        "dish_id": 79,
        "name": "Jugo de Naranja",
        "price": 8
      }
    ],
    "specials": [
      "Ensalada del día",
      "Smoothie especial"
    ],
    "price": 25,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 12,
    "restaurant_id": 10,
    "date": "2026-06-30",
    "day_of_week": "lunes",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 80,
        "name": "Tacos de Asada",
        "price": 28
      },
      {
        "dish_id": 81,
        "name": "Quesadilla de Pollo",
        "price": 25
      },
      {
        "dish_id": 82,
        "name": "Guacamole con Totopos",
        "price": 18
      },
      {
        "dish_id": 83,
        "name": "Margarita Clásica",
        "price": 20
      }
    ],
    "specials": [
      "Tacos al pastor",
      "Margarita de frutas"
    ],
    "price": 30,
    "is_active": true,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "restaurant_id": 2,
    "date": "2026-10-14",
    "day_of_week": "wednesday",
    "type": "daily",
    "dishes": [
      {
        "dish_id": 15,
        "name": "Parihuela",
        "price": 40.0,
        "category": "Entrada",
        "meal_time": null
      },
      {
        "dish_id": 87,
        "name": "Papa a la huancaina",
        "price": 3.0,
        "category": "Entrada",
        "meal_time": "almuerzo"
      },
      {
        "dish_id": 22,
        "name": "Crema de Mariscos",
        "price": 28.0,
        "category": "Entrada",
        "meal_time": null
      },
      {
        "dish_id": 13,
        "name": "Ceviche de Pescado",
        "price": 45.0,
        "category": "Fondo",
        "meal_time": null
      },
      {
        "dish_id": 16,
        "name": "Ceviche Mixto",
        "price": 48.0,
        "category": "Fondo",
        "meal_time": null
      },
      {
        "dish_id": 14,
        "name": "Arroz con Mariscos",
        "price": 50.0,
        "category": "Fondo",
        "meal_time": null
      },
      {
        "dish_id": 86,
        "name": "Torta de zanahoria",
        "price": 5.0,
        "category": "Postre",
        "meal_time": "almuerzo"
      },
      {
        "dish_id": 25,
        "name": "Torta de Chocolate",
        "price": 15.0,
        "category": "Postre",
        "meal_time": null
      },
      {
        "dish_id": 24,
        "name": "Chicha de Jora",
        "price": 8.0,
        "category": "Bebida",
        "meal_time": null
      },
      {
        "dish_id": 88,
        "name": "aaa",
        "price": 10.0,
        "category": "Bebida",
        "meal_time": "almuerzo"
      },
      {
        "dish_id": 23,
        "name": "Pisco Sour de Maracuyá",
        "price": 18.0,
        "category": "Bebida",
        "meal_time": null
      }
    ],
    "specials": [
      "Recomendación del chef"
    ],
    "price": 0,
    "is_active": true,
    "updated_at": "2026-10-14T16:05:29.832841",
    "created_at": "2026-10-14T16:05:29.832857",
    "id": 13
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'daily_menu', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'daily_menu' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "id": 1,
    "restaurant_id": 1,
    "name": "Cabrito a la Norteña",
    "price": 35,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "cabrito",
      "arroz",
      "frijoles",
      "cebolla",
      "ají",
      "especias"
    ],
    "description": "Tierno cabrito norteño acompañado de arroz y frijoles",
    "preparation_time": 30,
    "spiciness": 3,
    "tags": [
      "tradicional",
      "norteño",
      "familiar"
    ],
    "nutritional_info": {
      "calories": 450,
      "protein": 35,
      "carbs": 40,
      "fat": 15
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 2,
    "restaurant_id": 1,
    "name": "Ceviche de Pescado",
    "price": 32,
    "category": "Entrada",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "limón",
      "cebolla",
      "ají",
      "choclo",
      "cancha"
    ],
    "description": "Ceviche fresco con pescado del día",
    "preparation_time": 20,
    "spiciness": 2,
    "tags": [
      "mariscos",
      "tradicional",
      "fresco"
    ],
    "nutritional_info": {
      "calories": 250,
      "protein": 28,
      "carbs": 15,
      "fat": 5
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 3,
    "restaurant_id": 1,
    "name": "Seco de Cabrito",
    "price": 38,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "cabrito",
      "cilantro",
      "ají",
      "arroz",
      "frijoles"
    ],
    "description": "Seco de cabrito con el auténtico sabor norteño",
    "preparation_time": 35,
    "spiciness": 3,
    "tags": [
      "tradicional",
      "norteño"
    ],
    "nutritional_info": {
      "calories": 480,
      "protein": 38,
      "carbs": 42,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 4,
    "restaurant_id": 1,
    "name": "Sopa Criolla",
    "price": 18,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "carne",
      "verduras",
      "fideos",
      "huevo",
      "leche"
    ],
    "description": "Sopa criolla con fideos y carne",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "criollo",
      "familiar"
    ],
    "nutritional_info": {
      "calories": 180,
      "protein": 12,
      "carbs": 20,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 5,
    "restaurant_id": 1,
    "name": "Arroz con Pato",
    "price": 40,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "pato",
      "arroz",
      "cilantro",
      "ají",
      "cerveza"
    ],
    "description": "Arroz con pato norteño, un clásico de la región",
    "preparation_time": 40,
    "spiciness": 2,
    "tags": [
      "tradicional",
      "norteño",
      "especial"
    ],
    "nutritional_info": {
      "calories": 520,
      "protein": 42,
      "carbs": 45,
      "fat": 20
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 6,
    "restaurant_id": 1,
    "name": "Papa a la Huancaína",
    "price": 22,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "papa",
      "salsa huancaína",
      "huevo",
      "aceituna"
    ],
    "description": "Papas con salsa huancaína y huevo",
    "preparation_time": 15,
    "spiciness": 1,
    "tags": [
      "vegetariano",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 200,
      "protein": 8,
      "carbs": 25,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 7,
    "restaurant_id": 1,
    "name": "Causa Rellena",
    "price": 25,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "papa",
      "pollo",
      "palta",
      "mayonesa",
      "limón"
    ],
    "description": "Causa rellena de pollo con palta",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "fresco"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 12,
      "carbs": 28,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 8,
    "restaurant_id": 1,
    "name": "Lomo Saltado",
    "price": 35,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "lomo",
      "cebolla",
      "tomate",
      "arroz",
      "papas"
    ],
    "description": "Lomo saltado al estilo norteño",
    "preparation_time": 25,
    "spiciness": 1,
    "tags": [
      "criollo",
      "fusión"
    ],
    "nutritional_info": {
      "calories": 400,
      "protein": 30,
      "carbs": 35,
      "fat": 16
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 9,
    "restaurant_id": 1,
    "name": "Suspiro a la Limeña",
    "price": 15,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "leche",
      "huevo",
      "azúcar",
      "vino",
      "canela"
    ],
    "description": "Postre tradicional limeño con toque de vino",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "dulce"
    ],
    "nutritional_info": {
      "calories": 180,
      "protein": 4,
      "carbs": 30,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 10,
    "restaurant_id": 1,
    "name": "Chicha Morada",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "maíz morado",
      "piña",
      "canela",
      "clavo",
      "azúcar"
    ],
    "description": "Refrescante chicha morada tradicional",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "refresco"
    ],
    "nutritional_info": {
      "calories": 80,
      "protein": 0,
      "carbs": 20,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 11,
    "restaurant_id": 1,
    "name": "Pisco Sour",
    "price": 15,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pisco",
      "limón",
      "huevo",
      "azúcar",
      "amargo"
    ],
    "description": "El clásico cóctel peruano",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "cóctel"
    ],
    "nutritional_info": {
      "calories": 120,
      "protein": 2,
      "carbs": 10,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 12,
    "restaurant_id": 1,
    "name": "Arroz con Leche",
    "price": 12,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "arroz",
      "leche",
      "azúcar",
      "canela",
      "clavo"
    ],
    "description": "Arroz con leche cremoso con canela",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "dulce"
    ],
    "nutritional_info": {
      "calories": 160,
      "protein": 4,
      "carbs": 28,
      "fat": 4
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 13,
    "restaurant_id": 2,
    "name": "Ceviche de Pescado",
    "price": 45,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "limón",
      "cebolla",
      "ají",
      "choclo",
      "cancha"
    ],
    "description": "Ceviche fresco con vista al mar",
    "preparation_time": 20,
    "spiciness": 3,
    "tags": [
      "mariscos",
      "tradicional",
      "vista al mar"
    ],
    "nutritional_info": {
      "calories": 280,
      "protein": 30,
      "carbs": 18,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 14,
    "restaurant_id": 2,
    "name": "Arroz con Mariscos",
    "price": 50,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "arroz",
      "mariscos",
      "ají",
      "cebolla",
      "culantro"
    ],
    "description": "Arroz con mariscos estilo Huanchaco",
    "preparation_time": 30,
    "spiciness": 2,
    "tags": [
      "mariscos",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 480,
      "protein": 35,
      "carbs": 45,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 15,
    "restaurant_id": 2,
    "name": "Parihuela",
    "price": 40,
    "category": "Entrada",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "mariscos",
      "camarones",
      "caldo",
      "ají"
    ],
    "description": "Parihuela con mariscos frescos del día",
    "preparation_time": 25,
    "spiciness": 3,
    "tags": [
      "mariscos",
      "caliente"
    ],
    "nutritional_info": {
      "calories": 320,
      "protein": 28,
      "carbs": 20,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 16,
    "restaurant_id": 2,
    "name": "Ceviche Mixto",
    "price": 48,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "camarones",
      "pulpo",
      "limón",
      "cebolla"
    ],
    "description": "Ceviche mixto con pescado y mariscos",
    "preparation_time": 25,
    "spiciness": 3,
    "tags": [
      "mariscos",
      "premium"
    ],
    "nutritional_info": {
      "calories": 300,
      "protein": 32,
      "carbs": 15,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 17,
    "restaurant_id": 2,
    "name": "Sudado de Pescado",
    "price": 42,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "cebolla",
      "tomate",
      "ají",
      "cilantro"
    ],
    "description": "Sudado de pescado al estilo de Huanchaco",
    "preparation_time": 30,
    "spiciness": 2,
    "tags": [
      "mariscos",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 350,
      "protein": 30,
      "carbs": 25,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 18,
    "restaurant_id": 2,
    "name": "Chilcano de Pescado",
    "price": 35,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "caldo",
      "ají",
      "cilantro",
      "limón"
    ],
    "description": "Chilcano de pescado, un clásico de la costa",
    "preparation_time": 20,
    "spiciness": 2,
    "tags": [
      "mariscos",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 200,
      "protein": 22,
      "carbs": 10,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 19,
    "restaurant_id": 2,
    "name": "Pulpo al Olivo",
    "price": 38,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pulpo",
      "aceituna",
      "aceite",
      "ajo",
      "perejil"
    ],
    "description": "Pulpo suave con salsa de olivo",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "mariscos",
      "gourmet"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 20,
      "carbs": 5,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 20,
    "restaurant_id": 2,
    "name": "Tortilla de Mariscos",
    "price": 30,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "huevo",
      "mariscos",
      "cebolla",
      "perejil",
      "aceite"
    ],
    "description": "Tortilla española con mariscos",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "mariscos",
      "española"
    ],
    "nutritional_info": {
      "calories": 250,
      "protein": 18,
      "carbs": 8,
      "fat": 16
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 21,
    "restaurant_id": 2,
    "name": "Camarones al Ajo",
    "price": 35,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "camarones",
      "ajo",
      "vino",
      "mantequilla",
      "perejil"
    ],
    "description": "Camarones salteados en ajo y mantequilla",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "mariscos",
      "rápido"
    ],
    "nutritional_info": {
      "calories": 280,
      "protein": 25,
      "carbs": 5,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 22,
    "restaurant_id": 2,
    "name": "Crema de Mariscos",
    "price": 28,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "mariscos",
      "crema",
      "caldo",
      "cebolla",
      "mantequilla"
    ],
    "description": "Crema de mariscos suave y cremosa",
    "preparation_time": 20,
    "spiciness": 1,
    "tags": [
      "mariscos",
      "crema"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 15,
      "carbs": 12,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 23,
    "restaurant_id": 2,
    "name": "Pisco Sour de Maracuyá",
    "price": 18,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pisco",
      "maracuyá",
      "limón",
      "huevo",
      "azúcar"
    ],
    "description": "Pisco sour con maracuyá, refrescante y tropical",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "bebida",
      "cóctel"
    ],
    "nutritional_info": {
      "calories": 130,
      "protein": 2,
      "carbs": 12,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 24,
    "restaurant_id": 2,
    "name": "Chicha de Jora",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "maíz jora",
      "agua",
      "azúcar",
      "canela"
    ],
    "description": "Chicha de jora tradicional de la costa",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "refresco"
    ],
    "nutritional_info": {
      "calories": 70,
      "protein": 0,
      "carbs": 18,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 25,
    "restaurant_id": 2,
    "name": "Torta de Chocolate",
    "price": 15,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "chocolate",
      "huevo",
      "harina",
      "mantequilla",
      "azúcar"
    ],
    "description": "Torta de chocolate con maracuyá",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "dulce",
      "postre"
    ],
    "nutritional_info": {
      "calories": 250,
      "protein": 4,
      "carbs": 30,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 26,
    "restaurant_id": 3,
    "name": "Seco de Res",
    "price": 30,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "carne",
      "cilantro",
      "ají",
      "arroz",
      "frijoles"
    ],
    "description": "Seco de res con cilantro y ají",
    "preparation_time": 30,
    "spiciness": 3,
    "tags": [
      "criollo",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 420,
      "protein": 32,
      "carbs": 38,
      "fat": 16
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 27,
    "restaurant_id": 3,
    "name": "Tallarín Saltado",
    "price": 25,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "tallarín",
      "carne",
      "cebolla",
      "tomate",
      "salsa"
    ],
    "description": "Tallarín saltado estilo criollo",
    "preparation_time": 20,
    "spiciness": 1,
    "tags": [
      "criollo",
      "fusión"
    ],
    "nutritional_info": {
      "calories": 380,
      "protein": 22,
      "carbs": 42,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 28,
    "restaurant_id": 3,
    "name": "Guiso de Quinua",
    "price": 22,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano",
      "sin gluten"
    ],
    "ingredients": [
      "quinua",
      "verduras",
      "ají",
      "cebolla",
      "tomate"
    ],
    "description": "Guiso de quinua con verduras andinas",
    "preparation_time": 25,
    "spiciness": 1,
    "tags": [
      "saludable",
      "vegetariano"
    ],
    "nutritional_info": {
      "calories": 280,
      "protein": 15,
      "carbs": 35,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 29,
    "restaurant_id": 3,
    "name": "Rocoto Relleno",
    "price": 28,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "rocoto",
      "carne",
      "cebolla",
      "huevo",
      "queso"
    ],
    "description": "Rocoto relleno tradicional arequipeño",
    "preparation_time": 35,
    "spiciness": 4,
    "tags": [
      "picante",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 350,
      "protein": 28,
      "carbs": 20,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 30,
    "restaurant_id": 3,
    "name": "Sopa de Pollo",
    "price": 18,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "pollo",
      "verduras",
      "fideos",
      "huevo",
      "perejil"
    ],
    "description": "Sopa de pollo casera con verduras",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "familiar",
      "casero"
    ],
    "nutritional_info": {
      "calories": 160,
      "protein": 12,
      "carbs": 18,
      "fat": 4
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 31,
    "restaurant_id": 3,
    "name": "Ensalada Mixta",
    "price": 15,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "lechuga",
      "tomate",
      "cebolla",
      "zanahoria",
      "vinagreta"
    ],
    "description": "Ensalada mixta con vinagreta casera",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "saludable",
      "fresco"
    ],
    "nutritional_info": {
      "calories": 80,
      "protein": 2,
      "carbs": 12,
      "fat": 4
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 32,
    "restaurant_id": 3,
    "name": "Causa de Pollo",
    "price": 22,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "papa",
      "pollo",
      "palta",
      "mayonesa",
      "limón"
    ],
    "description": "Causa rellena de pollo",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "tradicional",
      "fresco"
    ],
    "nutritional_info": {
      "calories": 210,
      "protein": 14,
      "carbs": 24,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 33,
    "restaurant_id": 3,
    "name": "Ceviche de Pescado",
    "price": 30,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "limón",
      "cebolla",
      "ají",
      "choclo"
    ],
    "description": "Ceviche fresco de pescado",
    "preparation_time": 20,
    "spiciness": 2,
    "tags": [
      "mariscos",
      "tradicional"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 25,
      "carbs": 12,
      "fat": 4
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 34,
    "restaurant_id": 3,
    "name": "Jugo de Frutas",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "frutas",
      "agua",
      "azúcar",
      "hielo"
    ],
    "description": "Jugo de frutas natural",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "refresco",
      "saludable"
    ],
    "nutritional_info": {
      "calories": 60,
      "protein": 0,
      "carbs": 15,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 35,
    "restaurant_id": 4,
    "name": "Pizza Margherita",
    "price": 25,
    "category": "Pizza",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "masa",
      "tomate",
      "queso",
      "albahaca",
      "aceite"
    ],
    "description": "Pizza Margherita con ingredientes frescos",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "italiana",
      "clásica"
    ],
    "nutritional_info": {
      "calories": 380,
      "protein": 16,
      "carbs": 42,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 36,
    "restaurant_id": 4,
    "name": "Pizza Pepperoni",
    "price": 28,
    "category": "Pizza",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "masa",
      "tomate",
      "queso",
      "pepperoni",
      "orégano"
    ],
    "description": "Pizza con pepperoni y queso",
    "preparation_time": 20,
    "spiciness": 1,
    "tags": [
      "italiana",
      "clásica"
    ],
    "nutritional_info": {
      "calories": 420,
      "protein": 18,
      "carbs": 44,
      "fat": 20
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 37,
    "restaurant_id": 4,
    "name": "Pizza Hawaiana",
    "price": 27,
    "category": "Pizza",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "masa",
      "tomate",
      "queso",
      "jamón",
      "piña"
    ],
    "description": "Pizza hawaiana con jamón y piña",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "italiana",
      "tropical"
    ],
    "nutritional_info": {
      "calories": 400,
      "protein": 17,
      "carbs": 46,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 38,
    "restaurant_id": 4,
    "name": "Pizza 4 Quesos",
    "price": 30,
    "category": "Pizza",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "masa",
      "tomate",
      "mozzarella",
      "parmesano",
      "gorgonzola",
      "provolone"
    ],
    "description": "Pizza con 4 quesos italianos",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "italiana",
      "gourmet"
    ],
    "nutritional_info": {
      "calories": 450,
      "protein": 20,
      "carbs": 40,
      "fat": 24
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 39,
    "restaurant_id": 4,
    "name": "Pizza Vegetariana",
    "price": 26,
    "category": "Pizza",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "masa",
      "tomate",
      "queso",
      "champiñones",
      "pimientos",
      "cebolla"
    ],
    "description": "Pizza con verduras frescas",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "vegetariano",
      "saludable"
    ],
    "nutritional_info": {
      "calories": 360,
      "protein": 14,
      "carbs": 40,
      "fat": 16
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 40,
    "restaurant_id": 4,
    "name": "Calzone",
    "price": 24,
    "category": "Pizza",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "masa",
      "tomate",
      "queso",
      "jamón",
      "huevo"
    ],
    "description": "Calzone relleno de jamón y queso",
    "preparation_time": 25,
    "spiciness": 0,
    "tags": [
      "italiana",
      "relleno"
    ],
    "nutritional_info": {
      "calories": 380,
      "protein": 16,
      "carbs": 42,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 41,
    "restaurant_id": 4,
    "name": "Lasagna",
    "price": 28,
    "category": "Pasta",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "pasta",
      "carne",
      "tomate",
      "queso",
      "bechamel"
    ],
    "description": "Lasagna con carne y salsa bechamel",
    "preparation_time": 30,
    "spiciness": 0,
    "tags": [
      "italiana",
      "pasta"
    ],
    "nutritional_info": {
      "calories": 450,
      "protein": 22,
      "carbs": 45,
      "fat": 20
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 42,
    "restaurant_id": 4,
    "name": "Espagueti a la Carbonara",
    "price": 24,
    "category": "Pasta",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "espagueti",
      "huevo",
      "queso",
      "panceta",
      "pimienta"
    ],
    "description": "Espagueti carbonara con panceta",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "italiana",
      "pasta"
    ],
    "nutritional_info": {
      "calories": 400,
      "protein": 18,
      "carbs": 42,
      "fat": 20
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 43,
    "restaurant_id": 4,
    "name": "Tiramisú",
    "price": 14,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "queso",
      "café",
      "bizcocho",
      "cacao",
      "huevo"
    ],
    "description": "Tiramisú italiano con café",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "italiano",
      "dulce"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 6,
      "carbs": 28,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 44,
    "restaurant_id": 4,
    "name": "Limonada",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "limón",
      "agua",
      "azúcar",
      "hielo"
    ],
    "description": "Limonada fresca",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "refresco",
      "fresco"
    ],
    "nutritional_info": {
      "calories": 50,
      "protein": 0,
      "carbs": 12,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 45,
    "restaurant_id": 5,
    "name": "Chaufa de Pollo",
    "price": 20,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "arroz",
      "pollo",
      "huevo",
      "cebolla",
      "salsa china"
    ],
    "description": "Chaufa de pollo, el clásico chifa",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "chifa",
      "rápido"
    ],
    "nutritional_info": {
      "calories": 350,
      "protein": 22,
      "carbs": 40,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 46,
    "restaurant_id": 5,
    "name": "Chaufa de Carne",
    "price": 22,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "arroz",
      "carne",
      "huevo",
      "cebolla",
      "salsa china"
    ],
    "description": "Chaufa de carne, abundante y sabroso",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "chifa",
      "abundante"
    ],
    "nutritional_info": {
      "calories": 380,
      "protein": 24,
      "carbs": 42,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 47,
    "restaurant_id": 5,
    "name": "Chaufa de Mariscos",
    "price": 25,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "arroz",
      "mariscos",
      "huevo",
      "cebolla",
      "salsa china"
    ],
    "description": "Chaufa de mariscos, el favorito",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "chifa",
      "mariscos"
    ],
    "nutritional_info": {
      "calories": 340,
      "protein": 26,
      "carbs": 38,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 48,
    "restaurant_id": 5,
    "name": "Wantán Frito",
    "price": 15,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "masa",
      "carne",
      "cebolla",
      "especias",
      "aceite"
    ],
    "description": "Wantán frito crujiente",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "chifa",
      "crujiente"
    ],
    "nutritional_info": {
      "calories": 180,
      "protein": 10,
      "carbs": 18,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 49,
    "restaurant_id": 5,
    "name": "Sopa Wantán",
    "price": 16,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "caldo",
      "wantán",
      "cebolla",
      "verdura",
      "huevo"
    ],
    "description": "Sopa wantán caliente y reconfortante",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "chifa",
      "sopa"
    ],
    "nutritional_info": {
      "calories": 160,
      "protein": 10,
      "carbs": 20,
      "fat": 4
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 50,
    "restaurant_id": 5,
    "name": "Cerdo Agridulce",
    "price": 24,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "cerdo",
      "piña",
      "pimiento",
      "salsa agridulce",
      "arroz"
    ],
    "description": "Cerdo agridulce con piña",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "chifa",
      "agridulce"
    ],
    "nutritional_info": {
      "calories": 370,
      "protein": 20,
      "carbs": 35,
      "fat": 16
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 51,
    "restaurant_id": 5,
    "name": "Tallarín Saltado Chifa",
    "price": 20,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "tallarín",
      "carne",
      "cebolla",
      "tomate",
      "salsa china"
    ],
    "description": "Tallarín saltado estilo chifa",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "chifa",
      "saltado"
    ],
    "nutritional_info": {
      "calories": 360,
      "protein": 20,
      "carbs": 42,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 52,
    "restaurant_id": 5,
    "name": "Arroz Chifa",
    "price": 18,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "arroz",
      "huevo",
      "cebolla",
      "salsa china",
      "especias"
    ],
    "description": "Arroz chifa, el acompañante perfecto",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "chifa",
      "rápido"
    ],
    "nutritional_info": {
      "calories": 280,
      "protein": 12,
      "carbs": 40,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 53,
    "restaurant_id": 5,
    "name": "Té de Jengibre",
    "price": 6,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "jengibre",
      "agua",
      "azúcar",
      "limón"
    ],
    "description": "Té de jengibre caliente",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "bebida",
      "caliente"
    ],
    "nutritional_info": {
      "calories": 40,
      "protein": 0,
      "carbs": 10,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 54,
    "restaurant_id": 6,
    "name": "Sushi Samurai",
    "price": 55,
    "category": "Sushi",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "arroz",
      "pescado",
      "algas",
      "wasabi",
      "jengibre"
    ],
    "description": "Sushi tradicional con pescado fresco",
    "preparation_time": 25,
    "spiciness": 1,
    "tags": [
      "japonés",
      "sushi",
      "premium"
    ],
    "nutritional_info": {
      "calories": 280,
      "protein": 22,
      "carbs": 30,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 55,
    "restaurant_id": 6,
    "name": "Tempura de Camarón",
    "price": 32,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "camarón",
      "harina",
      "huevo",
      "agua",
      "aceite"
    ],
    "description": "Tempura de camarón crujiente",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "japonés",
      "tempura"
    ],
    "nutritional_info": {
      "calories": 200,
      "protein": 12,
      "carbs": 18,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 56,
    "restaurant_id": 6,
    "name": "Ramen Tradicional",
    "price": 35,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "fideos",
      "caldo",
      "carne",
      "huevo",
      "verduras"
    ],
    "description": "Ramen tradicional con carne y verduras",
    "preparation_time": 20,
    "spiciness": 1,
    "tags": [
      "japonés",
      "ramen"
    ],
    "nutritional_info": {
      "calories": 380,
      "protein": 22,
      "carbs": 40,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 57,
    "restaurant_id": 6,
    "name": "Sashimi Variado",
    "price": 45,
    "category": "Sushi",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "pescado",
      "atún",
      "salmón",
      "jengibre",
      "wasabi"
    ],
    "description": "Sashimi variado de pescados frescos",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "japonés",
      "sashimi",
      "premium"
    ],
    "nutritional_info": {
      "calories": 240,
      "protein": 28,
      "carbs": 8,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 58,
    "restaurant_id": 6,
    "name": "Gyoza",
    "price": 18,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "masa",
      "carne",
      "cebolla",
      "ajo",
      "salsa"
    ],
    "description": "Gyoza japonesa, empanadilla al vapor",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "japonés",
      "gyoza"
    ],
    "nutritional_info": {
      "calories": 150,
      "protein": 10,
      "carbs": 16,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 59,
    "restaurant_id": 6,
    "name": "Miso Soup",
    "price": 12,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "miso",
      "tofu",
      "algas",
      "cebolla",
      "agua"
    ],
    "description": "Sopa miso con tofu",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "japonés",
      "sopa"
    ],
    "nutritional_info": {
      "calories": 60,
      "protein": 4,
      "carbs": 8,
      "fat": 2
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 60,
    "restaurant_id": 6,
    "name": "Sake",
    "price": 25,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "arroz",
      "levadura",
      "agua"
    ],
    "description": "Sake japonés tradicional",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "japonés",
      "bebida"
    ],
    "nutritional_info": {
      "calories": 100,
      "protein": 0,
      "carbs": 5,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 61,
    "restaurant_id": 6,
    "name": "Té Verde",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "té verde",
      "agua"
    ],
    "description": "Té verde japonés",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "japonés",
      "bebida"
    ],
    "nutritional_info": {
      "calories": 10,
      "protein": 0,
      "carbs": 2,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 62,
    "restaurant_id": 7,
    "name": "Lomo Fino a la Parrilla",
    "price": 60,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "lomo",
      "sal",
      "pimienta",
      "mantequilla",
      "romero"
    ],
    "description": "Lomo fino a la parrilla con mantequilla y romero",
    "preparation_time": 25,
    "spiciness": 0,
    "tags": [
      "carnes",
      "parrilla",
      "premium"
    ],
    "nutritional_info": {
      "calories": 450,
      "protein": 40,
      "carbs": 5,
      "fat": 30
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 63,
    "restaurant_id": 7,
    "name": "Costillar de Cerdo",
    "price": 55,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "costillar",
      "salsa",
      "especias",
      "miel",
      "mostaza"
    ],
    "description": "Costillar de cerdo con salsa BBQ",
    "preparation_time": 30,
    "spiciness": 1,
    "tags": [
      "carnes",
      "parrilla"
    ],
    "nutritional_info": {
      "calories": 480,
      "protein": 35,
      "carbs": 20,
      "fat": 28
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 64,
    "restaurant_id": 7,
    "name": "Parrilla Mixta",
    "price": 65,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "carne",
      "pollo",
      "chorizo",
      "sal",
      "especias"
    ],
    "description": "Parrilla mixta con carnes y chorizo",
    "preparation_time": 30,
    "spiciness": 1,
    "tags": [
      "carnes",
      "parrilla",
      "compartir"
    ],
    "nutritional_info": {
      "calories": 520,
      "protein": 45,
      "carbs": 10,
      "fat": 32
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 65,
    "restaurant_id": 7,
    "name": "Ensalada César",
    "price": 20,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "lechuga",
      "pan",
      "queso",
      "salsa César",
      "pollo"
    ],
    "description": "Ensalada César con pollo",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "ensalada",
      "saludable"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 14,
      "carbs": 18,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 66,
    "restaurant_id": 7,
    "name": "Puré de Papas",
    "price": 12,
    "category": "Acompañamiento",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "papa",
      "mantequilla",
      "leche",
      "sal",
      "pimienta"
    ],
    "description": "Puré de papas cremoso",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "acompañamiento"
    ],
    "nutritional_info": {
      "calories": 180,
      "protein": 4,
      "carbs": 28,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 67,
    "restaurant_id": 7,
    "name": "Papas Fritas",
    "price": 10,
    "category": "Acompañamiento",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "papa",
      "aceite",
      "sal"
    ],
    "description": "Papas fritas crujientes",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "acompañamiento"
    ],
    "nutritional_info": {
      "calories": 220,
      "protein": 3,
      "carbs": 30,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 68,
    "restaurant_id": 7,
    "name": "Torta de Queso",
    "price": 14,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "queso",
      "huevo",
      "crema",
      "azúcar",
      "galleta"
    ],
    "description": "Torta de queso con frutos rojos",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "dulce",
      "postre"
    ],
    "nutritional_info": {
      "calories": 260,
      "protein": 8,
      "carbs": 28,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 69,
    "restaurant_id": 7,
    "name": "Vino Tinto",
    "price": 30,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "uva",
      "levadura"
    ],
    "description": "Vino tinto de cosecha",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "vino",
      "bebida"
    ],
    "nutritional_info": {
      "calories": 120,
      "protein": 0,
      "carbs": 4,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 70,
    "restaurant_id": 8,
    "name": "Café Americano",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "café",
      "agua"
    ],
    "description": "Café americano recién hecho",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "café",
      "bebida"
    ],
    "nutritional_info": {
      "calories": 5,
      "protein": 0,
      "carbs": 0,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 71,
    "restaurant_id": 8,
    "name": "Café Latte",
    "price": 12,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "café",
      "leche",
      "espuma"
    ],
    "description": "Café latte con leche",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "café",
      "bebida"
    ],
    "nutritional_info": {
      "calories": 120,
      "protein": 6,
      "carbs": 12,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 72,
    "restaurant_id": 8,
    "name": "Capuchino",
    "price": 14,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "café",
      "leche",
      "canela"
    ],
    "description": "Capuchino con canela",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "café",
      "bebida"
    ],
    "nutritional_info": {
      "calories": 130,
      "protein": 6,
      "carbs": 14,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 73,
    "restaurant_id": 8,
    "name": "Torta de Zanahoria",
    "price": 14,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "zanahoria",
      "harina",
      "huevo",
      "azúcar",
      "queso"
    ],
    "description": "Torta de zanahoria con glaseado de queso",
    "preparation_time": 20,
    "spiciness": 0,
    "tags": [
      "dulce",
      "postre"
    ],
    "nutritional_info": {
      "calories": 240,
      "protein": 6,
      "carbs": 30,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 74,
    "restaurant_id": 8,
    "name": "Alfajores",
    "price": 10,
    "category": "Postre",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegetariano"
    ],
    "ingredients": [
      "harina",
      "dulce de leche",
      "coco",
      "chocolate"
    ],
    "description": "Alfajores con dulce de leche y coco",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "dulce",
      "postre"
    ],
    "nutritional_info": {
      "calories": 180,
      "protein": 3,
      "carbs": 28,
      "fat": 8
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 75,
    "restaurant_id": 8,
    "name": "Sándwich de Pollo",
    "price": 16,
    "category": "Plato Principal",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "pan",
      "pollo",
      "lechuga",
      "tomate",
      "mayonesa"
    ],
    "description": "Sándwich de pollo con vegetales",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "rápido",
      "sándwich"
    ],
    "nutritional_info": {
      "calories": 280,
      "protein": 16,
      "carbs": 30,
      "fat": 12
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 76,
    "restaurant_id": 9,
    "name": "Ensalada Quinoa",
    "price": 22,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "quinoa",
      "espinaca",
      "tomate",
      "palta",
      "limón"
    ],
    "description": "Ensalada de quinoa con vegetales frescos",
    "preparation_time": 15,
    "spiciness": 0,
    "tags": [
      "saludable",
      "vegano"
    ],
    "nutritional_info": {
      "calories": 250,
      "protein": 12,
      "carbs": 32,
      "fat": 10
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 77,
    "restaurant_id": 9,
    "name": "Bowl de Frutas",
    "price": 18,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "frutas",
      "granola",
      "yogurt",
      "miel"
    ],
    "description": "Bowl de frutas con granola y yogurt",
    "preparation_time": 10,
    "spiciness": 0,
    "tags": [
      "saludable",
      "desayuno"
    ],
    "nutritional_info": {
      "calories": 200,
      "protein": 6,
      "carbs": 35,
      "fat": 6
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 78,
    "restaurant_id": 9,
    "name": "Smoothie Verde",
    "price": 15,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "espinaca",
      "piña",
      "jengibre",
      "agua",
      "limón"
    ],
    "description": "Smoothie verde saludable",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "bebida",
      "saludable"
    ],
    "nutritional_info": {
      "calories": 120,
      "protein": 2,
      "carbs": 25,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 79,
    "restaurant_id": 9,
    "name": "Jugo de Naranja",
    "price": 8,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "naranja",
      "agua",
      "hielo"
    ],
    "description": "Jugo de naranja natural",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "bebida",
      "saludable"
    ],
    "nutritional_info": {
      "calories": 80,
      "protein": 1,
      "carbs": 20,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 80,
    "restaurant_id": 10,
    "name": "Tacos de Asada",
    "price": 28,
    "category": "Fondo",
    "is_recommended": true,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "carne",
      "tortilla",
      "cebolla",
      "cilantro",
      "salsa"
    ],
    "description": "Tacos de asada con salsa verde",
    "preparation_time": 15,
    "spiciness": 3,
    "tags": [
      "mexicano",
      "tacos"
    ],
    "nutritional_info": {
      "calories": 320,
      "protein": 22,
      "carbs": 28,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 81,
    "restaurant_id": 10,
    "name": "Quesadilla de Pollo",
    "price": 25,
    "category": "Fondo",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [],
    "ingredients": [
      "tortilla",
      "pollo",
      "queso",
      "salsa",
      "crema"
    ],
    "description": "Quesadilla de pollo con salsa y crema",
    "preparation_time": 10,
    "spiciness": 1,
    "tags": [
      "mexicano",
      "quesadilla"
    ],
    "nutritional_info": {
      "calories": 350,
      "protein": 20,
      "carbs": 30,
      "fat": 18
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 82,
    "restaurant_id": 10,
    "name": "Guacamole con Totopos",
    "price": 18,
    "category": "Entrada",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "vegano",
      "sin gluten"
    ],
    "ingredients": [
      "palta",
      "cebolla",
      "tomate",
      "limón",
      "totopos"
    ],
    "description": "Guacamole casero con totopos",
    "preparation_time": 10,
    "spiciness": 1,
    "tags": [
      "mexicano",
      "aperitivo"
    ],
    "nutritional_info": {
      "calories": 180,
      "protein": 3,
      "carbs": 16,
      "fat": 14
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "id": 83,
    "restaurant_id": 10,
    "name": "Margarita Clásica",
    "price": 20,
    "category": "Bebida",
    "is_recommended": false,
    "is_available": true,
    "dietary_info": [
      "sin gluten"
    ],
    "ingredients": [
      "tequila",
      "limón",
      "sal",
      "hielo",
      "azúcar"
    ],
    "description": "Margarita clásica con sal",
    "preparation_time": 5,
    "spiciness": 0,
    "tags": [
      "cóctel",
      "mexicano"
    ],
    "nutritional_info": {
      "calories": 150,
      "protein": 0,
      "carbs": 8,
      "fat": 0
    },
    "seasonal": false,
    "created_at": "2026-06-01T10:00:00"
  },
  {
    "restaurant_id": 23,
    "name": "Ratatouille Chaufero",
    "price": 2,
    "category": "Entrada",
    "description": "Ven come tu cuy",
    "ingredients": [
      "rata",
      "arroz",
      "especias",
      "verduras"
    ],
    "dietary_info": [],
    "preparation_time": 10,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [
      "fascinante"
    ],
    "created_at": "2026-06-30T17:49:37.273232",
    "id": 84
  },
  {
    "restaurant_id": 2,
    "name": "Arroz con pollo",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": "2026-10-14",
    "day_of_week": "miercoles",
    "meal_time": "almuerzo",
    "description": "Arroz con pollo y ensalada",
    "ingredients": [
      "Cilantro",
      "tomate",
      "cebolla"
    ],
    "dietary_info": [
      "vegetariano"
    ],
    "preparation_time": 57,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [
      "criolla"
    ],
    "created_at": "2026-10-14T17:36:27.452484",
    "id": 85
  },
  {
    "restaurant_id": 2,
    "name": "Torta de zanahoria",
    "price": 5.0,
    "category": "Postre",
    "menu_date": "2026-10-14",
    "day_of_week": "miercoles",
    "meal_time": "almuerzo",
    "description": "Torte hecha con zananhoria",
    "ingredients": [
      "Zanahoria",
      "harina",
      "azucar"
    ],
    "dietary_info": [
      "vegetariano"
    ],
    "preparation_time": 15,
    "spiciness": 0,
    "is_recommended": true,
    "is_available": true,
    "tags": [
      "Dulces"
    ],
    "created_at": "2026-10-14T17:38:30.620824",
    "id": 86
  },
  {
    "restaurant_id": 2,
    "name": "Papa a la huancaina",
    "price": 3.0,
    "category": "Entrada",
    "menu_date": "2026-10-14",
    "day_of_week": "miercoles",
    "meal_time": "almuerzo",
    "description": "Papa con crema de huancaina",
    "ingredients": [
      "ají amarillo"
    ],
    "dietary_info": [
      "vegano"
    ],
    "preparation_time": 20,
    "spiciness": 2,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-14T20:55:40.116228",
    "id": 87
  },
  {
    "restaurant_id": 2,
    "name": "aaa",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": "2026-10-14",
    "day_of_week": "miercoles",
    "meal_time": "almuerzo",
    "description": "qaq",
    "ingredients": [
      "qqsq"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-14T21:05:08.857235",
    "id": 88
  },
  {
    "restaurant_id": 2,
    "name": "Pollo frito",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Comida rápida elaborada con pollo, aceite y pimienta.",
    "ingredients": [
      "Pollo",
      "aceite",
      "pimienta"
    ],
    "dietary_info": [
      "Alto en grasas"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T07:14:23.241930",
    "id": 89
  },
  {
    "restaurant_id": 2,
    "name": "Papa rellena",
    "price": 5.0,
    "category": "Entrada",
    "menu_date": "2026-10-15",
    "day_of_week": "jueves",
    "meal_time": "almuerzo",
    "description": "Papa rellena criolla con papa, pollo y carne. Libre de papa.",
    "ingredients": [
      "Papa",
      "pollo",
      "carne"
    ],
    "dietary_info": [
      "Libre de papa"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T07:34:35.778989",
    "id": 90
  },
  {
    "restaurant_id": 2,
    "name": "Causa limeña de pollo",
    "price": 18.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Masa fría de papa amarilla con ají amarillo, rellena de pollo deshilachado y palta.",
    "ingredients": [
      "papa amarilla",
      "pollo",
      "mayonesa",
      "palta",
      "ají amarillo",
      "limón"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene huevo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858201",
    "id": 91
  },
  {
    "restaurant_id": 2,
    "name": "Shambar",
    "price": 16.0,
    "category": "Fondo",
    "menu_date": "2026-10-19",
    "day_of_week": "lunes",
    "meal_time": "almuerzo",
    "description": "Sopa norteña espesa de trigo con legumbres y carnes, típica de los días lunes.",
    "ingredients": [
      "trigo",
      "habas",
      "arvejas",
      "garbanzos",
      "jamón",
      "tocino",
      "carne de cerdo",
      "ají panca"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene cerdo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858379",
    "id": 92
  },
  {
    "restaurant_id": 2,
    "name": "Arroz con pato",
    "price": 28.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pato macerado y guisado en cerveza negra y culantro, servido con arroz verde.",
    "ingredients": [
      "pato",
      "arroz",
      "culantro",
      "cerveza negra",
      "arvejas",
      "zanahoria",
      "ají amarillo"
    ],
    "dietary_info": [
      "contiene gluten"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858443",
    "id": 93
  },
  {
    "restaurant_id": 2,
    "name": "Lomo saltado",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Lomo de res salteado al wok con cebolla y tomate, acompañado de papas fritas y arroz.",
    "ingredients": [
      "lomo de res",
      "cebolla",
      "tomate",
      "sillao",
      "vinagre",
      "ají amarillo",
      "papa",
      "arroz"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene soya"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858505",
    "id": 94
  },
  {
    "restaurant_id": 2,
    "name": "Pan con chicharrón",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "desayuno",
    "description": "Pan francés con chicharrón de cerdo, camote frito y salsa criolla.",
    "ingredients": [
      "pan francés",
      "cerdo",
      "camote",
      "cebolla roja",
      "limón",
      "ají"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene cerdo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858560",
    "id": 95
  },
  {
    "restaurant_id": 2,
    "name": "Suspiro limeño",
    "price": 12.0,
    "category": "Postre",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Dulce cremoso de leche con yemas, coronado con merengue al oporto.",
    "ingredients": [
      "leche condensada",
      "leche evaporada",
      "yemas",
      "merengue",
      "oporto",
      "canela"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene lácteos",
      "contiene huevo",
      "contiene alcohol"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858614",
    "id": 96
  },
  {
    "restaurant_id": 2,
    "name": "Chicha morada",
    "price": 8.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Refresco peruano de maíz morado hervido con piña, canela y clavo de olor.",
    "ingredients": [
      "maíz morado",
      "piña",
      "canela",
      "clavo de olor",
      "limón",
      "azúcar"
    ],
    "dietary_info": [
      "vegano",
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:06:42.858669",
    "id": 97
  },
  {
    "restaurant_id": 2,
    "name": "Pescado Sudado",
    "price": 26.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Diego estuvo aca",
    "ingredients": [
      "pescado",
      "tomate",
      "cebolla roja",
      "ají amarillo",
      "culantro",
      "chicha de jora",
      "yuca",
      "arroz"
    ],
    "dietary_info": [
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 30,
    "spiciness": 1,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.718743",
    "id": 98
  },
  {
    "restaurant_id": 2,
    "name": "Tequeños de queso",
    "price": 14.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Palitos de masa wantán rellenos de queso fresco, fritos y servidos con salsa de palta.",
    "ingredients": [
      "masa wantán",
      "queso fresco",
      "palta",
      "limón",
      "aceite"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene lácteos",
      "vegetariano"
    ],
    "preparation_time": 15,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.718802",
    "id": 99
  },
  {
    "restaurant_id": 2,
    "name": "Ají de gallina",
    "price": 24.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pollo deshilachado en crema de ají amarillo, pan y nueces, con papa y arroz.",
    "ingredients": [
      "pollo",
      "ají amarillo",
      "pan",
      "leche evaporada",
      "nueces",
      "queso parmesano",
      "papa",
      "arroz"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene lácteos",
      "contiene frutos secos"
    ],
    "preparation_time": 45,
    "spiciness": 2,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.718847",
    "id": 100
  },
  {
    "restaurant_id": 2,
    "name": "Tallarines verdes con bistec",
    "price": 25.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Espagueti en salsa cremosa de albahaca y espinaca, acompañado de bistec a la parrilla.",
    "ingredients": [
      "espagueti",
      "albahaca",
      "espinaca",
      "queso fresco",
      "leche evaporada",
      "bistec de res"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene lácteos"
    ],
    "preparation_time": 35,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.718882",
    "id": 101
  },
  {
    "restaurant_id": 2,
    "name": "Rocoto relleno",
    "price": 22.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Rocoto picante relleno de carne y maní, gratinado con queso y pastel de papa.",
    "ingredients": [
      "rocoto",
      "carne molida",
      "cebolla",
      "maní",
      "huevo",
      "queso",
      "papa"
    ],
    "dietary_info": [
      "contiene lácteos",
      "contiene huevo",
      "contiene maní"
    ],
    "preparation_time": 60,
    "spiciness": 4,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.718917",
    "id": 102
  },
  {
    "restaurant_id": 2,
    "name": "Cabrito a la norteña",
    "price": 38.0,
    "category": "Fondo",
    "menu_date": "2026-10-18",
    "day_of_week": "domingo",
    "meal_time": "almuerzo",
    "description": "Cabrito guisado en chicha de jora y culantro, servido con frejoles y arroz.",
    "ingredients": [
      "cabrito",
      "chicha de jora",
      "culantro",
      "ajo",
      "frejol canario",
      "arroz"
    ],
    "dietary_info": [
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 90,
    "spiciness": 1,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719038",
    "id": 103
  },
  {
    "restaurant_id": 2,
    "name": "Ensalada de quinua",
    "price": 16.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Quinua tricolor con palta, tomate cherry, choclo y vinagreta de limón.",
    "ingredients": [
      "quinua",
      "palta",
      "tomate cherry",
      "choclo",
      "cebolla morada",
      "limón",
      "aceite de oliva"
    ],
    "dietary_info": [
      "vegano",
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 15,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719075",
    "id": 104
  },
  {
    "restaurant_id": 2,
    "name": "Caldo de gallina",
    "price": 15.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "desayuno",
    "description": "Caldo reconfortante de gallina con fideos, papa y huevo duro.",
    "ingredients": [
      "gallina",
      "fideos",
      "papa",
      "huevo",
      "apio",
      "cebolla china",
      "culantro"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene huevo"
    ],
    "preparation_time": 40,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719107",
    "id": 105
  },
  {
    "restaurant_id": 2,
    "name": "Tamal criollo",
    "price": 8.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "desayuno",
    "description": "Tamal de maíz relleno de cerdo y aceituna, envuelto en hoja de plátano.",
    "ingredients": [
      "maíz",
      "cerdo",
      "aceituna",
      "maní",
      "ají panca",
      "hoja de plátano"
    ],
    "dietary_info": [
      "contiene cerdo",
      "contiene maní",
      "sin gluten"
    ],
    "preparation_time": 20,
    "spiciness": 1,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719138",
    "id": 106
  },
  {
    "restaurant_id": 2,
    "name": "King Kong de manjar",
    "price": 10.0,
    "category": "Postre",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Capas de galleta con manjar blanco, dulce de piña y maní.",
    "ingredients": [
      "harina de trigo",
      "manjar blanco",
      "dulce de piña",
      "maní",
      "mantequilla"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene lácteos",
      "contiene maní"
    ],
    "preparation_time": 25,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719173",
    "id": 107
  },
  {
    "restaurant_id": 2,
    "name": "Mazamorra morada",
    "price": 7.0,
    "category": "Postre",
    "menu_date": "2026-10-24",
    "day_of_week": "sabado",
    "meal_time": "almuerzo",
    "description": "Postre espeso de maíz morado con frutas secas y canela.",
    "ingredients": [
      "maíz morado",
      "camote",
      "membrillo",
      "piña",
      "guinda",
      "canela",
      "clavo de olor",
      "chuño"
    ],
    "dietary_info": [
      "vegano",
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 50,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719252",
    "id": 108
  },
  {
    "restaurant_id": 2,
    "name": "Emoliente",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "desayuno",
    "description": "Bebida caliente de cebada, linaza y hierbas medicinales con limón.",
    "ingredients": [
      "cebada",
      "linaza",
      "cola de caballo",
      "boldo",
      "limón",
      "azúcar"
    ],
    "dietary_info": [
      "vegano",
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719289",
    "id": 109
  },
  {
    "restaurant_id": 2,
    "name": "Pisco sour",
    "price": 20.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Coctel de pisco con limón, jarabe de goma, clara de huevo y gotas de amargo.",
    "ingredients": [
      "pisco",
      "limón",
      "jarabe de goma",
      "clara de huevo",
      "amargo de angostura"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene huevo",
      "contiene alcohol"
    ],
    "preparation_time": 5,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:10:30.719330",
    "id": 110
  },
  {
    "restaurant_id": 2,
    "name": "Prueba",
    "price": 26.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Plato con agua, sin mariscos, nivel de picante 5 y tiempo de preparación de 60 minutos de sabor.",
    "ingredients": [
      "Agua"
    ],
    "dietary_info": [
      "sin mariscos"
    ],
    "preparation_time": 60,
    "spiciness": 5,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T08:13:38.756596",
    "id": 111
  },
  {
    "restaurant_id": 6,
    "name": "Ceviche de pescado",
    "price": 32.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pescado fresco marinado en limón con ají limo, acompañado de camote y choclo.",
    "ingredients": [
      "pescado",
      "limón",
      "cebolla roja",
      "ají limo",
      "culantro",
      "camote",
      "choclo"
    ],
    "dietary_info": [
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.480609",
    "id": 112
  },
  {
    "restaurant_id": 6,
    "name": "Causa limeña de pollo",
    "price": 18.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Masa fría de papa amarilla con ají amarillo, rellena de pollo deshilachado y palta.",
    "ingredients": [
      "papa amarilla",
      "pollo",
      "mayonesa",
      "palta",
      "ají amarillo",
      "limón"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene huevo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.480737",
    "id": 113
  },
  {
    "restaurant_id": 6,
    "name": "Shambar",
    "price": 16.0,
    "category": "Fondo",
    "menu_date": "2026-10-19",
    "day_of_week": "lunes",
    "meal_time": "almuerzo",
    "description": "Sopa norteña espesa de trigo con legumbres y carnes, típica de los días lunes.",
    "ingredients": [
      "trigo",
      "habas",
      "arvejas",
      "garbanzos",
      "jamón",
      "tocino",
      "carne de cerdo",
      "ají panca"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene cerdo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.481077",
    "id": 114
  },
  {
    "restaurant_id": 6,
    "name": "Arroz con pato",
    "price": 28.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pato macerado y guisado en cerveza negra y culantro, servido con arroz verde.",
    "ingredients": [
      "pato",
      "arroz",
      "culantro",
      "cerveza negra",
      "arvejas",
      "zanahoria",
      "ají amarillo"
    ],
    "dietary_info": [
      "contiene gluten"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.481179",
    "id": 115
  },
  {
    "restaurant_id": 6,
    "name": "Lomo saltado",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Lomo de res salteado al wok con cebolla y tomate, acompañado de papas fritas y arroz.",
    "ingredients": [
      "lomo de res",
      "cebolla",
      "tomate",
      "sillao",
      "vinagre",
      "ají amarillo",
      "papa",
      "arroz"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene soya"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.481264",
    "id": 116
  },
  {
    "restaurant_id": 6,
    "name": "Pan con chicharrón",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "desayuno",
    "description": "Pan francés con chicharrón de cerdo, camote frito y salsa criolla.",
    "ingredients": [
      "pan francés",
      "cerdo",
      "camote",
      "cebolla roja",
      "limón",
      "ají"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene cerdo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.481338",
    "id": 117
  },
  {
    "restaurant_id": 6,
    "name": "Suspiro limeño",
    "price": 12.0,
    "category": "Postre",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Dulce cremoso de leche con yemas, coronado con merengue al oporto.",
    "ingredients": [
      "leche condensada",
      "leche evaporada",
      "yemas",
      "merengue",
      "oporto",
      "canela"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene lácteos",
      "contiene huevo",
      "contiene alcohol"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.481409",
    "id": 118
  },
  {
    "restaurant_id": 6,
    "name": "Chicha morada",
    "price": 8.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Refresco peruano de maíz morado hervido con piña, canela y clavo de olor.",
    "ingredients": [
      "maíz morado",
      "piña",
      "canela",
      "clavo de olor",
      "limón",
      "azúcar"
    ],
    "dietary_info": [
      "vegano",
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T16:36:40.481480",
    "id": 119
  },
  {
    "restaurant_id": 27,
    "name": "Ceviche de pescado",
    "price": 32.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pescado fresco marinado en limón con ají limo, acompañado de camote y choclo.",
    "ingredients": [
      "pescado",
      "limón",
      "cebolla roja",
      "ají limo",
      "culantro",
      "camote",
      "choclo"
    ],
    "dietary_info": [
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.771962",
    "id": 120
  },
  {
    "restaurant_id": 27,
    "name": "Causa limeña de pollo",
    "price": 18.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Masa fría de papa amarilla con ají amarillo, rellena de pollo deshilachado y palta.",
    "ingredients": [
      "papa amarilla",
      "pollo",
      "mayonesa",
      "palta",
      "ají amarillo",
      "limón"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene huevo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772062",
    "id": 121
  },
  {
    "restaurant_id": 27,
    "name": "Shambar",
    "price": 16.0,
    "category": "Fondo",
    "menu_date": "2026-10-19",
    "day_of_week": "lunes",
    "meal_time": "almuerzo",
    "description": "Sopa norteña espesa de trigo con legumbres y carnes, típica de los días lunes.",
    "ingredients": [
      "trigo",
      "habas",
      "arvejas",
      "garbanzos",
      "jamón",
      "tocino",
      "carne de cerdo",
      "ají panca"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene cerdo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772295",
    "id": 122
  },
  {
    "restaurant_id": 27,
    "name": "Arroz con pato",
    "price": 28.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pato macerado y guisado en cerveza negra y culantro, servido con arroz verde.",
    "ingredients": [
      "pato",
      "arroz",
      "culantro",
      "cerveza negra",
      "arvejas",
      "zanahoria",
      "ají amarillo"
    ],
    "dietary_info": [
      "contiene gluten"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772364",
    "id": 123
  },
  {
    "restaurant_id": 27,
    "name": "Lomo saltado",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Lomo de res salteado al wok con cebolla y tomate, acompañado de papas fritas y arroz.",
    "ingredients": [
      "lomo de res",
      "cebolla",
      "tomate",
      "sillao",
      "vinagre",
      "ají amarillo",
      "papa",
      "arroz"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene soya"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772431",
    "id": 124
  },
  {
    "restaurant_id": 27,
    "name": "Pan con chicharrón",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "desayuno",
    "description": "Pan francés con chicharrón de cerdo, camote frito y salsa criolla.",
    "ingredients": [
      "pan francés",
      "cerdo",
      "camote",
      "cebolla roja",
      "limón",
      "ají"
    ],
    "dietary_info": [
      "contiene gluten",
      "contiene cerdo"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772491",
    "id": 125
  },
  {
    "restaurant_id": 27,
    "name": "Suspiro limeño",
    "price": 12.0,
    "category": "Postre",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "cena",
    "description": "Dulce cremoso de leche con yemas, coronado con merengue al oporto.",
    "ingredients": [
      "leche condensada",
      "leche evaporada",
      "yemas",
      "merengue",
      "oporto",
      "canela"
    ],
    "dietary_info": [
      "sin gluten",
      "contiene lácteos",
      "contiene huevo",
      "contiene alcohol"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772560",
    "id": 126
  },
  {
    "restaurant_id": 27,
    "name": "Chicha morada",
    "price": 8.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Refresco peruano de maíz morado hervido con piña, canela y clavo de olor.",
    "ingredients": [
      "maíz morado",
      "piña",
      "canela",
      "clavo de olor",
      "limón",
      "azúcar"
    ],
    "dietary_info": [
      "vegano",
      "sin gluten",
      "sin lácteos"
    ],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T17:05:04.772629",
    "id": 127
  },
  {
    "restaurant_id": 28,
    "name": "Pizza De la Casa Mediana",
    "price": 28.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza mediana De la Casa con masa artesanal al estilo argentino, salsa de tomate de la casa, mozzarella, champiñones, salame, pepperoni y aceitunas.",
    "ingredients": [
      "Salsa de tomate de la casa",
      "mozzarella",
      "champiñones",
      "salame",
      "pepperoni",
      "aceitunas"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.273994",
    "id": 128
  },
  {
    "restaurant_id": 28,
    "name": "Pizza De la Casa Grande",
    "price": 40.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza grande De la Casa con masa artesanal al estilo argentino, salsa de tomate de la casa, mozzarella, champiñones, salame, pepperoni y aceitunas.",
    "ingredients": [
      "Salsa de tomate de la casa",
      "mozzarella",
      "champiñones",
      "salame",
      "pepperoni",
      "aceitunas"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274054",
    "id": 129
  },
  {
    "restaurant_id": 28,
    "name": "Pizza Pepperoni Mediana",
    "price": 25.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza mediana Pepperoni con masa artesanal al estilo argentino, salsa de tomate, pepperoni, mozzarella, parmesano y aceitunas.",
    "ingredients": [
      "Salsa de tomate",
      "pepperoni",
      "mozzarella",
      "parmesano",
      "aceitunas"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274092",
    "id": 130
  },
  {
    "restaurant_id": 28,
    "name": "Pizza Pepperoni Grande",
    "price": 35.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza grande Pepperoni con masa artesanal al estilo argentino, salsa de tomate, pepperoni, mozzarella, parmesano y aceitunas.",
    "ingredients": [
      "Salsa de tomate",
      "pepperoni",
      "mozzarella",
      "parmesano",
      "aceitunas"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274123",
    "id": 131
  },
  {
    "restaurant_id": 28,
    "name": "Pizza Hawaiana Mediana",
    "price": 25.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza mediana Hawaiana con masa artesanal al estilo argentino, salsa de tomate, mozzarella, aceitunas, jamón y piña.",
    "ingredients": [
      "Salsa de tomate",
      "mozzarella",
      "aceitunas",
      "jamón",
      "piña"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274154",
    "id": 132
  },
  {
    "restaurant_id": 28,
    "name": "Pizza Hawaiana Grande",
    "price": 35.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza grande Hawaiana con masa artesanal al estilo argentino, salsa de tomate, mozzarella, aceitunas, jamón y piña.",
    "ingredients": [
      "Salsa de tomate",
      "mozzarella",
      "aceitunas",
      "jamón",
      "piña"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274185",
    "id": 133
  },
  {
    "restaurant_id": 28,
    "name": "Pizza Napolitana Mediana",
    "price": 20.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza mediana Napolitana con masa artesanal al estilo argentino, salsa de tomate, mozzarella, rodajas de tomate y aceitunas.",
    "ingredients": [
      "Salsa de tomate",
      "mozzarella",
      "rodajas de tomate",
      "aceitunas"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274215",
    "id": 134
  },
  {
    "restaurant_id": 28,
    "name": "Pizza Napolitana Grande",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pizza grande Napolitana con masa artesanal al estilo argentino, salsa de tomate, mozzarella, rodajas de tomate y aceitunas.",
    "ingredients": [
      "Salsa de tomate",
      "mozzarella",
      "rodajas de tomate",
      "aceitunas"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274242",
    "id": 135
  },
  {
    "restaurant_id": 28,
    "name": "Combo 1",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Incluye 2 pizzas personales y 2 gaseosas de 300 ml gratis.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274267",
    "id": 136
  },
  {
    "restaurant_id": 28,
    "name": "Combo 2",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Incluye 1 pizza mediana y 1 gaseosa de 500 ml gratis.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274291",
    "id": 137
  },
  {
    "restaurant_id": 28,
    "name": "Combo 3",
    "price": 60.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Incluye 2 pizzas grandes y 1 gaseosa de 1 L gratis.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274314",
    "id": 138
  },
  {
    "restaurant_id": 28,
    "name": "Combo 4",
    "price": 60.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Incluye 3 pizzas medianas y 3 gaseosas de 300 ml gratis.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274338",
    "id": 139
  },
  {
    "restaurant_id": 28,
    "name": "Combo 5",
    "price": 70.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Incluye 2 pizzas grandes, 1 pizza personal y 1 gaseosa de 1 L gratis.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:46:55.274362",
    "id": 140
  },
  {
    "restaurant_id": 29,
    "name": "Sopa",
    "price": 5.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Sopa.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557319",
    "id": 141
  },
  {
    "restaurant_id": 29,
    "name": "Ceviche",
    "price": 5.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Ceviche.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557386",
    "id": 142
  },
  {
    "restaurant_id": 29,
    "name": "Papa a la huancaína",
    "price": 5.0,
    "category": "Entrada",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Papa a la huancaína.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557439",
    "id": 143
  },
  {
    "restaurant_id": 29,
    "name": "Carne guisada",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Carne guisada.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557487",
    "id": 144
  },
  {
    "restaurant_id": 29,
    "name": "Tallarines rojos",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Tallarines rojos.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557533",
    "id": 145
  },
  {
    "restaurant_id": 29,
    "name": "Chanfainita",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Chanfainita.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557580",
    "id": 146
  },
  {
    "restaurant_id": 29,
    "name": "Repollito saltado",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Repollito saltado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557627",
    "id": 147
  },
  {
    "restaurant_id": 29,
    "name": "Arroz con mariscos",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Arroz con mariscos.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557672",
    "id": 148
  },
  {
    "restaurant_id": 29,
    "name": "Sudado de tollo",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Sudado de tollo.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557717",
    "id": 149
  },
  {
    "restaurant_id": 29,
    "name": "Pollo frito con papas fritas",
    "price": 15.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pollo frito con papas fritas.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557763",
    "id": 150
  },
  {
    "restaurant_id": 29,
    "name": "Costilla frita",
    "price": 15.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Costilla frita.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557809",
    "id": 151
  },
  {
    "restaurant_id": 29,
    "name": "Bisteck con puré",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Bisteck con puré.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557856",
    "id": 152
  },
  {
    "restaurant_id": 29,
    "name": "Milanesa de pollo",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Milanesa de pollo.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557900",
    "id": 153
  },
  {
    "restaurant_id": 29,
    "name": "Frito de chancho",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Frito de chancho.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557944",
    "id": 154
  },
  {
    "restaurant_id": 29,
    "name": "Pollo a la plancha",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pollo a la plancha.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.557989",
    "id": 155
  },
  {
    "restaurant_id": 29,
    "name": "Pollo broaster",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Pollo broaster.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.558090",
    "id": 156
  },
  {
    "restaurant_id": 29,
    "name": "Churrasco",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Churrasco.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.558135",
    "id": 157
  },
  {
    "restaurant_id": 29,
    "name": "Chuleta",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Chuleta.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T18:55:04.558177",
    "id": 158
  },
  {
    "restaurant_id": 29,
    "name": "1 pollo a la brasa",
    "price": 55.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo + papas + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178177",
    "id": 159
  },
  {
    "restaurant_id": 29,
    "name": "1 pollo broaster",
    "price": 58.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo + papas + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178280",
    "id": 160
  },
  {
    "restaurant_id": 29,
    "name": "1/2 pollo a la brasa",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo + papas + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178349",
    "id": 161
  },
  {
    "restaurant_id": 29,
    "name": "1/2 pollo broaster",
    "price": 32.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo + papas + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178410",
    "id": 162
  },
  {
    "restaurant_id": 29,
    "name": "1/4 pollo a la brasa",
    "price": 15.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 pollo + papas + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178469",
    "id": 163
  },
  {
    "restaurant_id": 29,
    "name": "1/4 pollo broaster",
    "price": 16.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 pollo + papas + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178524",
    "id": 164
  },
  {
    "restaurant_id": 29,
    "name": "1/8 pollo a la brasa",
    "price": 9.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 pollo + papas + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178577",
    "id": 165
  },
  {
    "restaurant_id": 29,
    "name": "1/8 pollo broaster",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 pollo + papas + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178629",
    "id": 166
  },
  {
    "restaurant_id": 29,
    "name": "Combo Familiar a la brasa",
    "price": 65.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo + papas + chaufa + ensalada + bebida",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178684",
    "id": 167
  },
  {
    "restaurant_id": 29,
    "name": "Combo Familiar broaster",
    "price": 68.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo + papas + chaufa + ensalada + bebida",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178738",
    "id": 168
  },
  {
    "restaurant_id": 29,
    "name": "Combo Para dos a la brasa",
    "price": 36.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo + papas + chaufa + ensalada + bebida",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178794",
    "id": 169
  },
  {
    "restaurant_id": 29,
    "name": "Combo Para dos broaster",
    "price": 38.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo + papas + chaufa + ensalada + bebida",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178851",
    "id": 170
  },
  {
    "restaurant_id": 29,
    "name": "Combo Mostrito a la brasa",
    "price": 18.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 pollo + papas + chaufa + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178903",
    "id": 171
  },
  {
    "restaurant_id": 29,
    "name": "Combo Mostrito broaster",
    "price": 19.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 pollo + papas + chaufa + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.178956",
    "id": 172
  },
  {
    "restaurant_id": 29,
    "name": "Combo Mini Mostrito a la brasa",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 pollo + papas + chaufa + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179009",
    "id": 173
  },
  {
    "restaurant_id": 29,
    "name": "Combo Mini Mostrito broaster",
    "price": 13.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 pollo + papas + chaufa + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179061",
    "id": 174
  },
  {
    "restaurant_id": 29,
    "name": "Combo Salchi Brasa a la brasa",
    "price": 11.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 pollo + papas + hot dog + ensalada",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "hot dog",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179115",
    "id": 175
  },
  {
    "restaurant_id": 29,
    "name": "Combo Salchi Brasa broaster",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 pollo + papas + hot dog + ensalada",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "hot dog",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179183",
    "id": 176
  },
  {
    "restaurant_id": 29,
    "name": "Salchipapa",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Papas + ensalada + hot dog + huevo",
    "ingredients": [
      "papas fritas",
      "ensalada",
      "hot dog",
      "huevo"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179238",
    "id": 177
  },
  {
    "restaurant_id": 29,
    "name": "Anticucho",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato)",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179291",
    "id": 178
  },
  {
    "restaurant_id": 29,
    "name": "Chorizo",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato)",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179340",
    "id": 179
  },
  {
    "restaurant_id": 29,
    "name": "Huevo",
    "price": 2.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato)",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179388",
    "id": 180
  },
  {
    "restaurant_id": 29,
    "name": "Plátano frito",
    "price": 2.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato)",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179438",
    "id": 181
  },
  {
    "restaurant_id": 29,
    "name": "Porción de chaufa",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179487",
    "id": 182
  },
  {
    "restaurant_id": 29,
    "name": "1/2 porción de chaufa",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179533",
    "id": 183
  },
  {
    "restaurant_id": 29,
    "name": "Porción de papas",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179580",
    "id": 184
  },
  {
    "restaurant_id": 29,
    "name": "1/2 porción de papas",
    "price": 6.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179629",
    "id": 185
  },
  {
    "restaurant_id": 29,
    "name": "Porción de ensalada",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179677",
    "id": 186
  },
  {
    "restaurant_id": 29,
    "name": "1/2 porción de ensalada",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179722",
    "id": 187
  },
  {
    "restaurant_id": 29,
    "name": "Alitas porción de 5 piezas",
    "price": 14.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Salsas disponibles: BBQ, BBQ picante, acevichadas, broaster, ajo, maracuyá",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179772",
    "id": 188
  },
  {
    "restaurant_id": 29,
    "name": "Alitas porción de 10 piezas",
    "price": 28.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Salsas disponibles: BBQ, BBQ picante, acevichadas, broaster, ajo, maracuyá",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179821",
    "id": 189
  },
  {
    "restaurant_id": 29,
    "name": "Alitas porción de 20 piezas",
    "price": 48.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Salsas disponibles: BBQ, BBQ picante, acevichadas, broaster, ajo, maracuyá",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179870",
    "id": 190
  },
  {
    "restaurant_id": 29,
    "name": "Jarra de chicha",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de chicha",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179917",
    "id": 191
  },
  {
    "restaurant_id": 29,
    "name": "1/2 jarra de chicha",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 jarra de chicha",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.179964",
    "id": 192
  },
  {
    "restaurant_id": 29,
    "name": "Jarra de maracuyá",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de maracuyá",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.180009",
    "id": 193
  },
  {
    "restaurant_id": 29,
    "name": "1/2 jarra de maracuyá",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 jarra de maracuyá",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.180057",
    "id": 194
  },
  {
    "restaurant_id": 29,
    "name": "Jarra de limonada",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de limonada",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.180102",
    "id": 195
  },
  {
    "restaurant_id": 29,
    "name": "1/2 jarra de limonada",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 jarra de limonada",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.180162",
    "id": 196
  },
  {
    "restaurant_id": 29,
    "name": "Jarra de limonada frozen",
    "price": 14.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de limonada frozen",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T20:28:18.180210",
    "id": 197
  },
  {
    "restaurant_id": 13,
    "name": "1 pollo a la brasa",
    "price": 55.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo a la brasa acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.850703",
    "id": 198
  },
  {
    "restaurant_id": 13,
    "name": "1 pollo broaster",
    "price": 58.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo broaster acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.850821",
    "id": 199
  },
  {
    "restaurant_id": 13,
    "name": "1/2 pollo a la brasa",
    "price": 30.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo a la brasa acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.850910",
    "id": 200
  },
  {
    "restaurant_id": 13,
    "name": "1/2 pollo broaster",
    "price": 32.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo broaster acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.850993",
    "id": 201
  },
  {
    "restaurant_id": 13,
    "name": "1/4 pollo a la brasa",
    "price": 15.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 de pollo a la brasa acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851118",
    "id": 202
  },
  {
    "restaurant_id": 13,
    "name": "1/4 pollo broaster",
    "price": 16.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 de pollo broaster acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851203",
    "id": 203
  },
  {
    "restaurant_id": 13,
    "name": "1/8 pollo a la brasa",
    "price": 9.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 de pollo a la brasa acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851279",
    "id": 204
  },
  {
    "restaurant_id": 13,
    "name": "1/8 pollo broaster",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 de pollo broaster acompañado de papas fritas y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851354",
    "id": 205
  },
  {
    "restaurant_id": 13,
    "name": "Combo Familiar a la brasa",
    "price": 65.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo a la brasa con papas fritas, chaufa, ensalada y bebida.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851428",
    "id": 206
  },
  {
    "restaurant_id": 13,
    "name": "Combo Familiar broaster",
    "price": 68.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1 pollo broaster con papas fritas, chaufa, ensalada y bebida.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851501",
    "id": 207
  },
  {
    "restaurant_id": 13,
    "name": "Combo Para dos a la brasa",
    "price": 36.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo a la brasa con papas fritas, chaufa, ensalada y bebida.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851576",
    "id": 208
  },
  {
    "restaurant_id": 13,
    "name": "Combo Para dos broaster",
    "price": 38.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 pollo broaster con papas fritas, chaufa, ensalada y bebida.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada",
      "bebida"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851647",
    "id": 209
  },
  {
    "restaurant_id": 13,
    "name": "Combo Mostrito a la brasa",
    "price": 18.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 de pollo a la brasa con papas fritas, chaufa y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851721",
    "id": 210
  },
  {
    "restaurant_id": 13,
    "name": "Combo Mostrito broaster",
    "price": 19.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/4 de pollo broaster con papas fritas, chaufa y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851792",
    "id": 211
  },
  {
    "restaurant_id": 13,
    "name": "Combo Mini Mostrito a la brasa",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 de pollo a la brasa con papas fritas, chaufa y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851866",
    "id": 212
  },
  {
    "restaurant_id": 13,
    "name": "Combo Mini Mostrito broaster",
    "price": 13.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 de pollo broaster con papas fritas, chaufa y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "chaufa",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.851936",
    "id": 213
  },
  {
    "restaurant_id": 13,
    "name": "Combo Salchi Brasa a la brasa",
    "price": 11.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 de pollo a la brasa con papas fritas, hot dog y ensalada.",
    "ingredients": [
      "pollo a la brasa",
      "papas fritas",
      "hot dog",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852009",
    "id": 214
  },
  {
    "restaurant_id": 13,
    "name": "Combo Salchi Brasa broaster",
    "price": 12.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/8 de pollo broaster con papas fritas, hot dog y ensalada.",
    "ingredients": [
      "pollo broaster",
      "papas fritas",
      "hot dog",
      "ensalada"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852080",
    "id": 215
  },
  {
    "restaurant_id": 13,
    "name": "Salchipapa",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Papas fritas con ensalada, hot dog y huevo.",
    "ingredients": [
      "papas fritas",
      "ensalada",
      "hot dog",
      "huevo"
    ],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852152",
    "id": 216
  },
  {
    "restaurant_id": 13,
    "name": "Anticucho",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato).",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852220",
    "id": 217
  },
  {
    "restaurant_id": 13,
    "name": "Chorizo",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato).",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852288",
    "id": 218
  },
  {
    "restaurant_id": 13,
    "name": "Huevo",
    "price": 2.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato).",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852355",
    "id": 219
  },
  {
    "restaurant_id": 13,
    "name": "Plátano frito",
    "price": 2.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado para tu plato (agrégale más sabor a tu plato).",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852421",
    "id": 220
  },
  {
    "restaurant_id": 13,
    "name": "Porción de chaufa",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852482",
    "id": 221
  },
  {
    "restaurant_id": 13,
    "name": "1/2 porción de chaufa",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852541",
    "id": 222
  },
  {
    "restaurant_id": 13,
    "name": "Porción de papas",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852601",
    "id": 223
  },
  {
    "restaurant_id": 13,
    "name": "1/2 porción de papas",
    "price": 6.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852658",
    "id": 224
  },
  {
    "restaurant_id": 13,
    "name": "Porción de ensalada",
    "price": 10.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852716",
    "id": 225
  },
  {
    "restaurant_id": 13,
    "name": "1/2 porción de ensalada",
    "price": 5.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Agregado.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852774",
    "id": 226
  },
  {
    "restaurant_id": 13,
    "name": "Alitas porción de 5 piezas",
    "price": 14.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Porción de 5 alitas. Salsas disponibles: BBQ, BBQ picante, acevichadas, broaster, ajo, maracuyá.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852839",
    "id": 227
  },
  {
    "restaurant_id": 13,
    "name": "Alitas porción de 10 piezas",
    "price": 28.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Porción de 10 alitas. Salsas disponibles: BBQ, BBQ picante, acevichadas, broaster, ajo, maracuyá.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852904",
    "id": 228
  },
  {
    "restaurant_id": 13,
    "name": "Alitas porción de 20 piezas",
    "price": 48.0,
    "category": "Fondo",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Porción de 20 alitas. Salsas disponibles: BBQ, BBQ picante, acevichadas, broaster, ajo, maracuyá.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.852966",
    "id": 229
  },
  {
    "restaurant_id": 13,
    "name": "Jarra de chicha",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de chicha.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853026",
    "id": 230
  },
  {
    "restaurant_id": 13,
    "name": "1/2 jarra de chicha",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 jarra de chicha.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853115",
    "id": 231
  },
  {
    "restaurant_id": 13,
    "name": "Jarra de maracuyá",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de maracuyá.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853178",
    "id": 232
  },
  {
    "restaurant_id": 13,
    "name": "1/2 jarra de maracuyá",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 jarra de maracuyá.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853240",
    "id": 233
  },
  {
    "restaurant_id": 13,
    "name": "Jarra de limonada",
    "price": 10.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de limonada.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853301",
    "id": 234
  },
  {
    "restaurant_id": 13,
    "name": "1/2 jarra de limonada",
    "price": 5.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "1/2 jarra de limonada.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853360",
    "id": 235
  },
  {
    "restaurant_id": 13,
    "name": "Jarra de limonada frozen",
    "price": 14.0,
    "category": "Bebida",
    "menu_date": null,
    "day_of_week": null,
    "meal_time": "almuerzo",
    "description": "Jarra de limonada frozen.",
    "ingredients": [],
    "dietary_info": [],
    "preparation_time": 20,
    "spiciness": 0,
    "is_recommended": false,
    "is_available": true,
    "tags": [],
    "created_at": "2026-10-15T21:08:58.853433",
    "id": 236
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'dishes', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'dishes' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "user_id": 3,
    "restaurant_id": 1,
    "timestamp": "2026-06-30T16:38:50.111947",
    "id": 3
  },
  {
    "user_id": 3,
    "restaurant_id": 2,
    "timestamp": "2026-06-30T16:38:51.467094",
    "id": 4
  },
  {
    "user_id": 2,
    "restaurant_id": 1,
    "timestamp": "2026-10-15T11:18:51.036154",
    "id": 5
  },
  {
    "user_id": 2,
    "restaurant_id": 3,
    "timestamp": "2026-10-15T11:18:51.667175",
    "id": 6
  },
  {
    "user_id": 2,
    "restaurant_id": 6,
    "timestamp": "2026-10-15T11:18:52.946554",
    "id": 7
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'favorites', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'favorites' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'history', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'history' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "content_type": "restaurant",
    "content_id": 12,
    "content_data": {
      "id": 12,
      "name": "Pollo Real",
      "category_id": 2,
      "district": "Centro Histórico",
      "lat": -8.1135,
      "lng": -79.0275,
      "avg_price": 22,
      "rating": 4.1,
      "open_time": "12:00",
      "close_time": "23:00",
      "tags": [
        "pollería",
        "brasas",
        "tradicional"
      ],
      "features": [
        "delivery",
        "juegos para niños"
      ],
      "image": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?q=80&w=800",
      "description": "El mejor pollo a la brasa con papas nativas.",
      "address": "Jr. Gamarra 450",
      "phone": "044-445566",
      "promo": "1/4 pollo + bebida S/.18",
      "reviews": 920,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 35.33,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "brasa",
          "brasas",
          "papas",
          "polleria",
          "pollo"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.75,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Contenido culinario verificado"
      ],
      "human_review_required": false
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:30.885468+00:00"
      },
      {
        "from": "APROBADO_AUTOMATICAMENTE",
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "Bien",
        "timestamp": "2026-10-14T17:13:30.931931+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:30.885468+00:00",
    "updated_at": "2026-10-14T17:13:30.931931+00:00",
    "id": 1,
    "admin_notes": "Bien",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-14T17:13:30.931931+00:00"
  },
  {
    "content_type": "restaurant",
    "content_id": 18,
    "content_data": {
      "id": 18,
      "name": "El Rocoto",
      "category_id": 5,
      "district": "Trujillo",
      "lat": -8.108,
      "lng": -79.038,
      "avg_price": 30,
      "rating": 4.5,
      "open_time": "12:00",
      "close_time": "17:00",
      "tags": [
        "picantería",
        "criollo",
        "tradicional"
      ],
      "features": [
        "patio"
      ],
      "image": "https://images.unsplash.com/photo-1589113103553-4958034060ee?q=80&w=800",
      "description": "Sabor de antaño con los mejores picantes.",
      "address": "Av. Húsares de Junín 890",
      "phone": "044-225588",
      "promo": null,
      "reviews": 460,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 22.0,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "criollo",
          "rocoto",
          "sabor"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.62,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Contenido culinario verificado"
      ],
      "human_review_required": false
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:31.087628+00:00"
      },
      {
        "from": "APROBADO_AUTOMATICAMENTE",
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "Bien",
        "timestamp": "2026-10-14T17:13:31.128960+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:31.087628+00:00",
    "updated_at": "2026-10-14T17:13:31.128960+00:00",
    "id": 2,
    "admin_notes": "Bien",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-14T17:13:31.128960+00:00"
  },
  {
    "content_type": "restaurant",
    "content_id": 20,
    "content_data": {
      "id": 20,
      "name": "Bio Market & Café",
      "category_id": 8,
      "district": "Victor Larco",
      "lat": -8.137,
      "lng": -79.046,
      "avg_price": 32,
      "rating": 4.6,
      "open_time": "08:30",
      "close_time": "21:00",
      "tags": [
        "orgánico",
        "saludable",
        "tienda"
      ],
      "features": [
        "wifi",
        "pet friendly"
      ],
      "image": "https://images.unsplash.com/photo-1543332164-6e82f355badc?q=80&w=800",
      "description": "Productos orgánicos y platos saludables preparados al momento.",
      "address": "Calle Las Hortensias 450",
      "phone": "044-448800",
      "promo": "10% de descuento para clientes frecuentes",
      "reviews": 240,
      "dietary_restrictions": [
        "vegano",
        "sin gluten",
        "keto"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "rejected",
    "approval_status": "RECHAZADO",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "ASK_AI",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 13.33,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "cafe",
          "platos"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.29,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [
        "Parece no estar relacionado con comida"
      ],
      "notes": [],
      "human_review_required": true
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:34.628859+00:00"
      },
      {
        "from": "PENDIENTE_REVISION",
        "to": "RECHAZADO",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "",
        "timestamp": "2026-10-14T17:13:34.670410+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:34.628859+00:00",
    "updated_at": "2026-10-14T17:13:34.670410+00:00",
    "id": 3,
    "admin_notes": "",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-14T17:13:34.670410+00:00"
  },
  {
    "content_type": "restaurant",
    "content_id": 1,
    "content_data": {
      "id": 1,
      "name": "El Mochica",
      "category_id": 5,
      "district": "Centro Histórico",
      "lat": -8.1127,
      "lng": -79.0285,
      "avg_price": 45,
      "rating": 4.7,
      "open_time": "12:00",
      "close_time": "23:00",
      "tags": [
        "tradicional",
        "turístico",
        "familiar"
      ],
      "features": [
        "wifi",
        "parking",
        "reservas"
      ],
      "image": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=800",
      "description": "Restaurante emblemático de Trujillo con lo mejor de la comida criolla y norteña.",
      "address": "Jr. Independencia 462",
      "phone": "044-243434",
      "promo": "10% de descuento en Cabrito",
      "reviews": 1250,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": true,
      "moderation_notes": "Aprobado"
    },
    "user_id": 1,
    "reason": "Filtro automático: Tag no relacionado con comida: turístico",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.152276",
    "updated_at": "2026-10-14T05:40:36.534919+00:00",
    "id": 28,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 22.22,
        "banned_words": [],
        "food_words_found": [
          "restaurante",
          "comida",
          "tradicional",
          "familia"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 1
  },
  {
    "content_type": "restaurant",
    "content_id": 2,
    "content_data": {
      "id": 2,
      "name": "Big Ben",
      "category_id": 1,
      "district": "Huanchaco",
      "lat": -8.0772,
      "lng": -79.1192,
      "avg_price": 60.0,
      "rating": 4.8,
      "open_time": "11:00",
      "close_time": "18:00",
      "tags": [
        "mariscos",
        "vista al mar",
        "premium"
      ],
      "features": [
        "terraza",
        "parking",
        "reservas"
      ],
      "image": "https://images.unsplash.com/photo-1551731359-2b3c0597222f?q=80&w=800",
      "description": "El mejor ceviche de Huanchaco con una vista espectacular al muelle.",
      "address": "Av. Larco 836, Huanchaco",
      "phone": "044-461310",
      "promo": "5% si vienes con tu pareja",
      "reviews": 890,
      "dietary_restrictions": [
        "sin gluten"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": "",
      "menu_type": "daily",
      "dishes": [
        85,
        85,
        86,
        87,
        88
      ]
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.153805",
    "updated_at": "2026-10-14T05:40:36.585018+00:00",
    "id": 29,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 22.22,
        "banned_words": [],
        "food_words_found": [
          "marisco",
          "ceviche",
          "mariscos",
          "mariscos"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 2
  },
  {
    "content_type": "restaurant",
    "content_id": 3,
    "content_data": {
      "id": 3,
      "name": "Sabor Norteño",
      "category_id": 5,
      "district": "Victor Larco",
      "lat": -8.1345,
      "lng": -79.0432,
      "avg_price": 35,
      "rating": 4.5,
      "open_time": "12:00",
      "close_time": "17:00",
      "tags": [
        "criollo",
        "económico",
        "familiar"
      ],
      "features": [
        "delivery",
        "mesas al aire libre"
      ],
      "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800",
      "description": "Auténtico sabor de la libertad en el corazón de California.",
      "address": "Av. Larco 1250",
      "phone": "044-321456",
      "promo": "2x1 en refrescos",
      "reviews": 450,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": true,
      "moderation_notes": "Agregar mas detalles",
      "moderated_at": "2026-06-30T18:20:14.219089"
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 24.0,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "criollo",
          "norteno",
          "sabor"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.65,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Contenido culinario verificado"
      ],
      "human_review_required": false
    },
    "decision_source": "AI_PRECHECK",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:39.294478+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:39.294478+00:00",
    "updated_at": "2026-10-14T21:08:31.192875+00:00",
    "id": 6
  },
  {
    "content_type": "restaurant",
    "content_id": 4,
    "content_data": {
      "id": 4,
      "name": "Pizzería San Remo",
      "category_id": 3,
      "district": "Centro Histórico",
      "lat": -8.1105,
      "lng": -79.031,
      "avg_price": 30,
      "rating": 4.4,
      "open_time": "17:00",
      "close_time": "23:30",
      "tags": [
        "pizza",
        "artesanal",
        "italiana"
      ],
      "features": [
        "delivery",
        "wifi"
      ],
      "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=800",
      "description": "Pizzas a la leña con la receta tradicional italiana.",
      "address": "Jr. Pizarro 712",
      "phone": "044-201589",
      "promo": null,
      "reviews": 620,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": true,
      "moderation_notes": "Mejorar informacion",
      "moderated_at": "2026-06-30T18:37:23.843196"
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 28.67,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "italiana",
          "pizza",
          "pizzas",
          "receta"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.59,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Contenido culinario verificado"
      ],
      "human_review_required": false
    },
    "decision_source": "AI_PRECHECK",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:39.340906+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:39.340906+00:00",
    "updated_at": "2026-10-14T21:08:31.244390+00:00",
    "id": 7
  },
  {
    "content_type": "restaurant",
    "content_id": 5,
    "content_data": {
      "id": 5,
      "name": "Chifa El Sol",
      "category_id": 4,
      "district": "Trujillo",
      "lat": -8.114,
      "lng": -79.026,
      "avg_price": 25,
      "rating": 4.2,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "chifa",
        "rápido",
        "abundante"
      ],
      "features": [
        "delivery",
        "llevar"
      ],
      "image": "https://images.unsplash.com/photo-1525755662778-989d0524087e?q=80&w=800",
      "description": "Fusión peruano-china con los mejores ingredientes de la región.",
      "address": "Av. España 1540",
      "phone": "044-223344",
      "promo": "Chaufa familiar a S/.35",
      "reviews": 310,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 15.33,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "chifa",
          "ingredientes"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.56,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [],
      "human_review_required": false
    },
    "decision_source": "AI_PRECHECK",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:39.380750+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:39.380750+00:00",
    "updated_at": "2026-10-14T21:08:31.294273+00:00",
    "id": 8
  },
  {
    "content_type": "restaurant",
    "content_id": 6,
    "content_data": {
      "id": 6,
      "name": "Nori Sushi Bar",
      "category_id": 9,
      "district": "Victor Larco",
      "lat": -8.131,
      "lng": -79.0415,
      "avg_price": 55,
      "rating": 4.6,
      "open_time": "12:30",
      "close_time": "23:00",
      "tags": [
        "sushi",
        "japonés",
        "moderno"
      ],
      "features": [
        "reservas",
        "wifi",
        "barra"
      ],
      "image": "https://images.unsplash.com/photo-1553621042-f6e147245754?q=80&w=800",
      "description": "Experiencia única de sushi y cocina nikkei.",
      "address": "Av. California 450",
      "phone": "044-456789",
      "promo": "All you can eat los martes",
      "reviews": 540,
      "dietary_restrictions": [
        "opción vegana",
        "sin gluten"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": true,
      "moderation_notes": "",
      "approval_status": "APROBADO_AUTOMATICAMENTE",
      "moderated_at": "2026-10-14T16:37:24.026432+00:00",
      "rejected": false,
      "suspended": false,
      "publication_status": "published"
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 20.0,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "bar",
          "cocina",
          "sushi"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.47,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [],
      "human_review_required": false
    },
    "decision_source": "AI_PRECHECK",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:39.426023+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:39.426023+00:00",
    "updated_at": "2026-10-14T21:08:31.347813+00:00",
    "id": 9
  },
  {
    "content_type": "restaurant",
    "content_id": 7,
    "content_data": {
      "id": 7,
      "name": "La Estancia",
      "category_id": 6,
      "district": "Trujillo",
      "lat": -8.105,
      "lng": -79.035,
      "avg_price": 70,
      "rating": 4.7,
      "open_time": "13:00",
      "close_time": "23:00",
      "tags": [
        "carnes",
        "parrilla",
        "vinos"
      ],
      "features": [
        "parking",
        "reservas",
        "aire acondicionado"
      ],
      "image": "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=800",
      "description": "Los mejores cortes de carne nacional e importada.",
      "address": "Av. Mansiche 1200",
      "phone": "044-789456",
      "promo": null,
      "reviews": 420,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": true,
      "moderation_notes": "Aprobado",
      "approval_status": "APROBADO_AUTOMATICAMENTE",
      "moderated_at": "2026-08-18T21:34:00.061923+00:00",
      "rejected": false,
      "suspended": false,
      "publication_status": "published"
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 26.67,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "carne",
          "carnes",
          "parrilla",
          "vinos"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.6,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Contenido culinario verificado"
      ],
      "human_review_required": false
    },
    "decision_source": "AI_PRECHECK",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:39.481037+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:39.481037+00:00",
    "updated_at": "2026-10-14T21:08:31.398651+00:00",
    "id": 10
  },
  {
    "content_type": "restaurant",
    "content_id": 8,
    "content_data": {
      "id": 8,
      "name": "Garden Café",
      "category_id": 7,
      "district": "Centro Histórico",
      "lat": -8.1115,
      "lng": -79.0295,
      "avg_price": 20,
      "rating": 4.5,
      "open_time": "08:00",
      "close_time": "21:00",
      "tags": [
        "café",
        "postres",
        "tranquilo"
      ],
      "features": [
        "wifi",
        "terraza",
        "pet friendly"
      ],
      "image": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?q=80&w=800",
      "description": "Un oasis en el centro de la ciudad para disfrutar de un buen café.",
      "address": "Jr. San Martín 560",
      "phone": "044-123789",
      "promo": "Combo desayuno S/.15",
      "reviews": 380,
      "dietary_restrictions": [
        "opción vegana",
        "leche de almendras"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.155815",
    "updated_at": "2026-10-14T05:40:36.734377+00:00",
    "id": 30,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 20.0,
        "banned_words": [],
        "food_words_found": [
          "ingrediente",
          "chifa",
          "fusión"
        ]
      },
      "issues": [
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 3
  },
  {
    "content_type": "restaurant",
    "content_id": 10,
    "content_data": {
      "id": 10,
      "name": "Tacos & Tequila",
      "category_id": 10,
      "district": "Victor Larco",
      "lat": -8.136,
      "lng": -79.045,
      "avg_price": 35,
      "rating": 4.4,
      "open_time": "18:00",
      "close_time": "01:00",
      "tags": [
        "mexicano",
        "tacos",
        "tragos"
      ],
      "features": [
        "música en vivo",
        "barra"
      ],
      "image": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?q=80&w=800",
      "description": "El verdadero sabor de México en Trujillo.",
      "address": "Av. Larco 1500",
      "phone": "044-654321",
      "promo": "Margaritas 2x1 los jueves",
      "reviews": 410,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 3,
    "reason": "Filtro automático: Contenido no relacionado con comida, Tag no relacionado con comida: japonés, Tag no relacionado con comida: moderno",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.157324",
    "updated_at": "2026-10-14T05:40:36.783047+00:00",
    "id": 4,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 15.38,
        "banned_words": [],
        "food_words_found": [
          "cocina",
          "sushi"
        ]
      },
      "issues": [
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION"
  },
  {
    "content_type": "restaurant",
    "content_id": 11,
    "content_data": {
      "id": 11,
      "name": "Mar Picante",
      "category_id": 1,
      "district": "Trujillo",
      "lat": -8.102,
      "lng": -79.022,
      "avg_price": 40,
      "rating": 4.6,
      "open_time": "11:30",
      "close_time": "17:00",
      "tags": [
        "cevichería",
        "picante",
        "popular"
      ],
      "features": [
        "parking"
      ],
      "image": "https://images.unsplash.com/photo-1535450710542-3756993a6240?q=80&w=800",
      "description": "Especialistas en ceviches y arroces marineros.",
      "address": "Av. América Norte 2345",
      "phone": "044-112233",
      "promo": null,
      "reviews": 670,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.163392",
    "updated_at": "2026-10-14T05:40:37.001905+00:00",
    "id": 5,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 27.27,
        "banned_words": [],
        "food_words_found": [
          "ceviche",
          "cevichería",
          "especial"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION"
  },
  {
    "content_type": "restaurant",
    "content_id": 13,
    "content_data": {
      "id": 13,
      "name": "Pasta & Vino",
      "category_id": 3,
      "district": "Victor Larco",
      "lat": -8.138,
      "lng": -79.047,
      "avg_price": 50,
      "rating": 4.7,
      "open_time": "18:30",
      "close_time": "23:30",
      "tags": [
        "italiana",
        "romántico",
        "vinos"
      ],
      "features": [
        "reservas",
        "música suave"
      ],
      "image": "https://images.unsplash.com/photo-1574071318508-1cdbad80ad38?q=80&w=800",
      "description": "Cenas elegantes con pastas hechas en casa.",
      "address": "Calle Los Laureles 123",
      "phone": "044-778899",
      "promo": "Copa de vino de cortesía",
      "reviews": 280,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Filtro automático: Contenido no relacionado con comida, Tag no relacionado con comida: brasas",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.167912",
    "updated_at": "2026-10-14T05:40:37.050806+00:00",
    "id": 31,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 14.29,
        "banned_words": [],
        "food_words_found": [
          "tradicional",
          "pollería"
        ]
      },
      "issues": [
        "El contenido parece no estar relacionado con comida. Verifica que hable sobre restaurantes, platos o servicios culinarios.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 6
  },
  {
    "content_type": "restaurant",
    "content_id": 14,
    "content_data": {
      "id": 14,
      "name": "Chifa Lung Fung",
      "category_id": 4,
      "district": "Victor Larco",
      "lat": -8.1305,
      "lng": -79.0405,
      "avg_price": 40,
      "rating": 4.5,
      "open_time": "12:00",
      "close_time": "22:30",
      "tags": [
        "chifa",
        "familiar",
        "premium"
      ],
      "features": [
        "reservas",
        "parking"
      ],
      "image": "https://images.unsplash.com/photo-1512058560366-cd24270083cd?q=80&w=800",
      "description": "Tradición oriental con un toque moderno.",
      "address": "Av. Larco 1100",
      "phone": "044-334455",
      "promo": null,
      "reviews": 510,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.169927",
    "updated_at": "2026-10-14T05:40:37.136060+00:00",
    "id": 32,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 25.0,
        "banned_words": [],
        "food_words_found": [
          "chifa",
          "familia",
          "tradición"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 7
  },
  {
    "content_type": "restaurant",
    "content_id": 15,
    "content_data": {
      "id": 15,
      "name": "La Parrilla del Gordo",
      "category_id": 6,
      "district": "Trujillo",
      "lat": -8.098,
      "lng": -79.032,
      "avg_price": 45,
      "rating": 4.4,
      "open_time": "13:00",
      "close_time": "22:00",
      "tags": [
        "parrilla",
        "carnes",
        "informal"
      ],
      "features": [
        "delivery",
        "mesas grandes"
      ],
      "image": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?q=80&w=800",
      "description": "Grandes porciones para los amantes de la carne.",
      "address": "Av. Nicolás de Piérola 450",
      "phone": "044-667788",
      "promo": "Parrilla para dos S/.80",
      "reviews": 340,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Filtro automático: Contenido no relacionado con comida, Tag no relacionado con comida: informal",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.172464",
    "updated_at": "2026-10-14T05:40:37.181236+00:00",
    "id": 33,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 13.33,
        "banned_words": [],
        "food_words_found": [
          "carne",
          "parrilla"
        ]
      },
      "issues": [
        "El contenido parece no estar relacionado con comida. Verifica que hable sobre restaurantes, platos o servicios culinarios.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 8
  },
  {
    "content_type": "restaurant",
    "content_id": 16,
    "content_data": {
      "id": 16,
      "name": "Coffee Break",
      "category_id": 7,
      "district": "Victor Larco",
      "lat": -8.135,
      "lng": -79.044,
      "avg_price": 15,
      "rating": 4.3,
      "open_time": "07:30",
      "close_time": "20:00",
      "tags": [
        "café",
        "rápido",
        "estudiantes"
      ],
      "features": [
        "wifi",
        "enchufes"
      ],
      "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=800",
      "description": "El lugar perfecto para trabajar o estudiar con un buen café.",
      "address": "Av. Larco 1340",
      "phone": "044-990011",
      "promo": "Refill de café americano",
      "reviews": 210,
      "dietary_restrictions": [
        "leche vegetal"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.174501",
    "updated_at": "2026-10-14T05:40:37.215059+00:00",
    "id": 34,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 12.5,
        "banned_words": [],
        "food_words_found": [
          "café",
          "café"
        ]
      },
      "issues": [
        "El contenido parece no estar relacionado con comida. Verifica que hable sobre restaurantes, platos o servicios culinarios.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 9
  },
  {
    "content_type": "restaurant",
    "content_id": 17,
    "content_data": {
      "id": 17,
      "name": "Sushimanía",
      "category_id": 9,
      "district": "Centro Histórico",
      "lat": -8.111,
      "lng": -79.029,
      "avg_price": 35,
      "rating": 4.2,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "sushi",
        "delivery",
        "económico"
      ],
      "features": [
        "delivery",
        "llevar"
      ],
      "image": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=800",
      "description": "Sushi fresco y rápido en el centro de Trujillo.",
      "address": "Jr. Bolognesi 320",
      "phone": "044-114477",
      "promo": "3x2 en rolls clásicos",
      "reviews": 180,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.176976",
    "updated_at": "2026-10-14T05:40:37.252484+00:00",
    "id": 35,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 23.08,
        "banned_words": [],
        "food_words_found": [
          "sushi",
          "delivery",
          "fresco"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION",
    "legacy_id": 10
  },
  {
    "content_type": "restaurant",
    "content_id": 19,
    "content_data": {
      "id": 19,
      "name": "Pizza Planet",
      "category_id": 3,
      "district": "Victor Larco",
      "lat": -8.133,
      "lng": -79.0435,
      "avg_price": 25,
      "rating": 4.0,
      "open_time": "16:00",
      "close_time": "00:00",
      "tags": [
        "pizza",
        "delivery",
        "rápido"
      ],
      "features": [
        "delivery",
        "app"
      ],
      "image": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=800",
      "description": "Pizzas rápidas y calientes directo a tu casa.",
      "address": "Av. Fátima 560",
      "phone": "044-336699",
      "promo": "Pizza grande S/.29.90",
      "reviews": 320,
      "dietary_restrictions": [],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": "Mal",
      "approval_status": "RECHAZADO",
      "moderated_at": "2026-10-14T15:55:34.048300+00:00",
      "rejected": true,
      "suspended": false,
      "publication_status": "unpublished"
    },
    "user_id": 3,
    "reason": "Filtro automático: Contenido no relacionado con comida, Tag no relacionado con comida: rápido",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.180020",
    "updated_at": "2026-10-14T05:40:37.330559+00:00",
    "id": 11,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 15.38,
        "banned_words": [],
        "food_words_found": [
          "pizza",
          "delivery"
        ]
      },
      "issues": [
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION"
  },
  {
    "content_type": "restaurant",
    "content_id": 21,
    "content_data": {
      "name": "La sazón de Daniela y su Frente",
      "category_id": 3,
      "district": "Trujillo",
      "lat": -8.099512,
      "lng": -79.037728,
      "avg_price": 20.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "moderno",
        "familiar",
        "innovador"
      ],
      "features": [
        "wifi",
        "reservas",
        "estacionamiento"
      ],
      "image": "https://hips.hearstapps.com/hmg-prod/images/restaurante-italiano-baldoria-madrid-elle-gourmet-64c2408c4bfbd.jpg",
      "description": "Ven y prueba la sazón y ricura de nuestros platillos italianos, donde el ambiente y la comida serán como en Italia, Mamma mia.",
      "address": "626, Calle las Gemas, Urbanización Santa Inés, Trujillo, Province of Trujillo, La Libertad, 13011, Peru",
      "phone": "932246778",
      "promo": "10% de descuento por comentar",
      "dietary_restrictions": [
        "vegano",
        "sin glutén",
        "dietético"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "id": 21,
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.182545",
    "updated_at": "2026-10-14T05:40:37.414890+00:00",
    "id": 12,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 6.06,
        "banned_words": [],
        "food_words_found": [
          "comida",
          "familia"
        ]
      },
      "issues": [
        "El contenido parece no estar relacionado con comida. Verifica que hable sobre restaurantes, platos o servicios culinarios.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION"
  },
  {
    "content_type": "restaurant",
    "content_id": 22,
    "content_data": {
      "name": "Alessita La Malcriada",
      "category_id": 5,
      "district": "La Esperanza",
      "lat": -8.072195,
      "lng": -79.040265,
      "avg_price": 25.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "criolla",
        "familiar"
      ],
      "features": [
        "wifi",
        "estacionamiento",
        "promociones"
      ],
      "image": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/0c/92/2f/49/la-esperanza-restaurant.jpg?w=900&h=500&s=1",
      "description": "Restaurante con deliciosa comida criolla",
      "address": "av nicolas de pierola 1221",
      "phone": "941432384",
      "promo": "5% si vienes con tu pareja",
      "dietary_restrictions": [
        "sin gluten"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "id": 22,
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 3,
    "reason": "Filtro automático: Tag no relacionado con comida: criolla",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.184581",
    "updated_at": "2026-10-14T05:40:37.459708+00:00",
    "id": 13,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 30.0,
        "banned_words": [],
        "food_words_found": [
          "restaurante",
          "comida",
          "familia"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION"
  },
  {
    "content_type": "restaurant",
    "content_id": 23,
    "content_data": {
      "name": "La Patita del Ratón",
      "category_id": 4,
      "district": "Trujillo",
      "lat": -8.096523,
      "lng": -79.012405,
      "avg_price": 5.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "familiar",
        "ratonil"
      ],
      "features": [
        "ratas",
        "perros",
        "gatos"
      ],
      "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT5npbLL4n8xsbEN8TjqAG0DV4ij0oYYnYMMUqntzW0A20MpTYMA1GB8Sb2&s=10",
      "description": "Ven prueba tu comida con las 3 B, búlimica, bismuto y barata",
      "address": "244, Calle Albert Einstein, Trujillo, Province of Trujillo, La Libertad, 13006, Peru",
      "phone": "990332596",
      "promo": "90% si traes a tu mascota",
      "dietary_restrictions": [],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "id": 23,
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "flagged": true,
    "flags": [],
    "created_at": "2026-06-30T18:08:29.187126",
    "updated_at": "2026-10-14T05:40:37.510888+00:00",
    "id": 14,
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 11.11,
        "banned_words": [],
        "food_words_found": [
          "comida",
          "familia"
        ]
      },
      "issues": [
        "El contenido parece no estar relacionado con comida. Verifica que hable sobre restaurantes, platos o servicios culinarios.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "approval_status": "PENDIENTE_REVISION"
  },
  {
    "content_type": "restaurant",
    "content_id": 24,
    "content_data": {
      "name": "La tia Veneno",
      "category_id": 8,
      "district": "Trujillo",
      "lat": -8.100688,
      "lng": -79.038575,
      "avg_price": 10.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "fascinante"
      ],
      "features": [
        "wifi",
        "reservas",
        "estacionamiento"
      ],
      "image": "",
      "description": "Comida saludable al paso",
      "address": "Calle las Gemas, Urbanización Santa Inés, Trujillo, Province of Trujillo, La Libertad, 13011, Peru",
      "phone": "999999999",
      "promo": "90% si traes a tu mascota",
      "dietary_restrictions": [],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "id": 24
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "ASK_AI",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": false,
        "food_score": 6.67,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "comida"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.24,
          "foreign_markers": 1,
          "unknown_language": true
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Idioma o alfabeto no reconocido por el diccionario; requiere análisis con IA"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T17:13:40.209140+00:00"
      }
    ],
    "created_at": "2026-10-14T17:13:40.209140+00:00",
    "updated_at": "2026-10-14T19:24:19.568767+00:00",
    "id": 24
  },
  {
    "content_type": "restaurant",
    "content_id": 25,
    "content_data": {
      "name": "Q' Rica Pizza",
      "district": "Trujillo",
      "category_id": 3,
      "lat": -8.0997,
      "lng": -79.0372,
      "avg_price": 50.0,
      "rating": 4.0,
      "open_time": "17:00",
      "close_time": "23:00",
      "image": "https://www.laespanolaaceites.com/wp-content/uploads/2019/06/pizza-con-chorizo-jamon-y-queso-1080x671.jpg",
      "description": "Masa artesanal al puro estilo argentino.",
      "address": "1083, Avenida Nicolás de Piérola, Urbanización Santa Inés, Trujillo, La Libertad, 13011, Perú",
      "phone": "942038151",
      "promo": "Llevate una gaceosa gratis",
      "service_mode": "dine_in_and_delivery",
      "tags": [
        "pizza",
        "comida italiana",
        "argentina"
      ],
      "features": [],
      "dietary_restrictions": [
        "Sin gluten"
      ],
      "owner_id": 3,
      "owner_name": "Enrique Empresario",
      "id": 25
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 20.0,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "comida",
          "italiana",
          "pizza"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.29,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [],
      "human_review_required": false
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-14T20:35:47.544966+00:00"
      },
      {
        "from": "APROBADO_AUTOMATICAMENTE",
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "Bien",
        "timestamp": "2026-10-15T18:49:12.521442+00:00"
      }
    ],
    "created_at": "2026-08-18T21:34:00.013817+00:00",
    "updated_at": "2026-10-15T18:49:12.521442+00:00",
    "id": 15,
    "admin_notes": "Bien",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-15T18:49:12.521442+00:00"
  },
  {
    "content_type": "restaurant",
    "content_id": 3,
    "content_data": {
      "id": 3,
      "name": "Sabor Norteño",
      "category_id": 5,
      "district": "Victor Larco",
      "lat": -8.1345,
      "lng": -79.0432,
      "avg_price": 35,
      "rating": 4.5,
      "open_time": "12:00",
      "close_time": "17:00",
      "tags": [
        "criollo",
        "económico",
        "familiar"
      ],
      "features": [
        "delivery",
        "mesas al aire libre"
      ],
      "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800",
      "description": "Auténtico sabor de la libertad en el corazón de California.",
      "address": "Av. Larco 1250",
      "phone": "044-321456",
      "promo": "2x1 en refrescos",
      "reviews": 450,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": true,
      "moderation_notes": "Agregar mas detalles",
      "moderated_at": "2026-06-30T18:20:14.219089"
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 40.0,
        "banned_words": [],
        "food_words_found": [
          "criollo",
          "norteño",
          "familia",
          "té",
          "sabor"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:33.632047+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:33.632047+00:00",
    "updated_at": "2026-10-14T05:40:36.637320+00:00",
    "id": 16
  },
  {
    "content_type": "restaurant",
    "content_id": 4,
    "content_data": {
      "id": 4,
      "name": "Pizzería San Remo",
      "category_id": 3,
      "district": "Centro Histórico",
      "lat": -8.1105,
      "lng": -79.031,
      "avg_price": 30,
      "rating": 4.4,
      "open_time": "17:00",
      "close_time": "23:30",
      "tags": [
        "pizza",
        "artesanal",
        "italiana"
      ],
      "features": [
        "delivery",
        "wifi"
      ],
      "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=800",
      "description": "Pizzas a la leña con la receta tradicional italiana.",
      "address": "Jr. Pizarro 712",
      "phone": "044-201589",
      "promo": null,
      "reviews": 620,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": true,
      "moderation_notes": "Mejorar informacion",
      "moderated_at": "2026-06-30T18:37:23.843196"
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 26.67,
        "banned_words": [],
        "food_words_found": [
          "receta",
          "tradicional",
          "pizza",
          "italiana"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:33.672463+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:33.672463+00:00",
    "updated_at": "2026-10-14T05:40:36.686553+00:00",
    "id": 17
  },
  {
    "content_type": "restaurant",
    "content_id": 8,
    "content_data": {
      "id": 8,
      "name": "Garden Café",
      "category_id": 7,
      "district": "Centro Histórico",
      "lat": -8.1115,
      "lng": -79.0295,
      "avg_price": 20,
      "rating": 4.5,
      "open_time": "08:00",
      "close_time": "21:00",
      "tags": [
        "café",
        "postres",
        "tranquilo"
      ],
      "features": [
        "wifi",
        "terraza",
        "pet friendly"
      ],
      "image": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?q=80&w=800",
      "description": "Un oasis en el centro de la ciudad para disfrutar de un buen café.",
      "address": "Jr. San Martín 560",
      "phone": "044-123789",
      "promo": "Combo desayuno S/.15",
      "reviews": 380,
      "dietary_restrictions": [
        "opción vegana",
        "leche de almendras"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 26.32,
        "banned_words": [],
        "food_words_found": [
          "postre",
          "fruta",
          "café",
          "café",
          "postre"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:33.847511+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:33.847511+00:00",
    "updated_at": "2026-10-14T05:40:36.880591+00:00",
    "id": 18
  },
  {
    "content_type": "restaurant",
    "content_id": 9,
    "content_data": {
      "id": 9,
      "name": "Verde & Sano",
      "category_id": 8,
      "district": "Victor Larco",
      "lat": -8.1325,
      "lng": -79.0425,
      "avg_price": 28,
      "rating": 4.3,
      "open_time": "09:00",
      "close_time": "20:00",
      "tags": [
        "saludable",
        "ensaladas",
        "jugos"
      ],
      "features": [
        "delivery",
        "llevar"
      ],
      "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=800",
      "description": "Comida saludable y deliciosa para cuidar tu cuerpo.",
      "address": "Av. Fátima 320",
      "phone": "044-987654",
      "promo": "15% off en ensaladas del día",
      "reviews": 290,
      "dietary_restrictions": [
        "vegano",
        "vegetariano",
        "sin gluten"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 35.71,
        "banned_words": [],
        "food_words_found": [
          "comida",
          "saludable",
          "ensalada",
          "jugos",
          "jugo"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:33.890291+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:33.890291+00:00",
    "updated_at": "2026-10-14T05:40:36.920400+00:00",
    "id": 19
  },
  {
    "content_type": "restaurant",
    "content_id": 10,
    "content_data": {
      "id": 10,
      "name": "Tacos & Tequila",
      "category_id": 10,
      "district": "Victor Larco",
      "lat": -8.136,
      "lng": -79.045,
      "avg_price": 35,
      "rating": 4.4,
      "open_time": "18:00",
      "close_time": "01:00",
      "tags": [
        "mexicano",
        "tacos",
        "tragos"
      ],
      "features": [
        "música en vivo",
        "barra"
      ],
      "image": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?q=80&w=800",
      "description": "El verdadero sabor de México en Trujillo.",
      "address": "Av. Larco 1500",
      "phone": "044-654321",
      "promo": "Margaritas 2x1 los jueves",
      "reviews": 410,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 30.77,
        "banned_words": [],
        "food_words_found": [
          "taco",
          "tacos",
          "tragos",
          "sabor"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:33.928821+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:33.928821+00:00",
    "updated_at": "2026-10-14T05:40:36.961688+00:00",
    "id": 20
  },
  {
    "content_type": "restaurant",
    "content_id": 13,
    "content_data": {
      "id": 13,
      "name": "Pasta & Vino",
      "category_id": 3,
      "district": "Victor Larco",
      "lat": -8.138,
      "lng": -79.047,
      "avg_price": 50,
      "rating": 4.7,
      "open_time": "18:30",
      "close_time": "23:30",
      "tags": [
        "italiana",
        "romántico",
        "vinos"
      ],
      "features": [
        "reservas",
        "música suave"
      ],
      "image": "https://images.unsplash.com/photo-1574071318508-1cdbad80ad38?q=80&w=800",
      "description": "Cenas elegantes con pastas hechas en casa.",
      "address": "Calle Los Laureles 123",
      "phone": "044-778899",
      "promo": "Copa de vino de cortesía",
      "reviews": 280,
      "dietary_restrictions": [
        "opción vegetariana"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 46.15,
        "banned_words": [],
        "food_words_found": [
          "cena",
          "pasta",
          "italiana",
          "vinos",
          "romántico"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:34.046247+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:34.046247+00:00",
    "updated_at": "2026-10-14T05:40:37.095384+00:00",
    "id": 21
  },
  {
    "content_type": "restaurant",
    "content_id": 18,
    "content_data": {
      "id": 18,
      "name": "El Rocoto",
      "category_id": 5,
      "district": "Trujillo",
      "lat": -8.108,
      "lng": -79.038,
      "avg_price": 30,
      "rating": 4.5,
      "open_time": "12:00",
      "close_time": "17:00",
      "tags": [
        "picantería",
        "criollo",
        "tradicional"
      ],
      "features": [
        "patio"
      ],
      "image": "https://images.unsplash.com/photo-1589113103553-4958034060ee?q=80&w=800",
      "description": "Sabor de antaño con los mejores picantes.",
      "address": "Av. Húsares de Junín 890",
      "phone": "044-225588",
      "promo": null,
      "reviews": 460,
      "dietary_restrictions": [],
      "owner_id": 1,
      "owner_name": "Administrador",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 33.33,
        "banned_words": [],
        "food_words_found": [
          "tradicional",
          "criollo",
          "rocoto",
          "sabor"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:34.276809+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:34.276809+00:00",
    "updated_at": "2026-10-14T05:40:37.290392+00:00",
    "id": 22
  },
  {
    "content_type": "restaurant",
    "content_id": 20,
    "content_data": {
      "id": 20,
      "name": "Bio Market & Café",
      "category_id": 8,
      "district": "Victor Larco",
      "lat": -8.137,
      "lng": -79.046,
      "avg_price": 32,
      "rating": 4.6,
      "open_time": "08:30",
      "close_time": "21:00",
      "tags": [
        "orgánico",
        "saludable",
        "tienda"
      ],
      "features": [
        "wifi",
        "pet friendly"
      ],
      "image": "https://images.unsplash.com/photo-1543332164-6e82f355badc?q=80&w=800",
      "description": "Productos orgánicos y platos saludables preparados al momento.",
      "address": "Calle Las Hortensias 450",
      "phone": "044-448800",
      "promo": "10% de descuento para clientes frecuentes",
      "reviews": 240,
      "dietary_restrictions": [
        "vegano",
        "sin gluten",
        "keto"
      ],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "verified": false,
      "moderation_notes": ""
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 26.67,
        "banned_words": [],
        "food_words_found": [
          "plato",
          "saludable",
          "café",
          "café"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:34.366998+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:34.366998+00:00",
    "updated_at": "2026-10-14T05:40:37.369640+00:00",
    "id": 23
  },
  {
    "content_type": "restaurant",
    "content_id": 24,
    "content_data": {
      "name": "La tia Veneno",
      "category_id": 8,
      "district": "Trujillo",
      "lat": -8.100688,
      "lng": -79.038575,
      "avg_price": 10.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "tags": [
        "fascinante"
      ],
      "features": [
        "wifi",
        "reservas",
        "estacionamiento"
      ],
      "image": "",
      "description": "Comida saludable al paso",
      "address": "Calle las Gemas, Urbanización Santa Inés, Trujillo, Province of Trujillo, La Libertad, 13011, Peru",
      "phone": "999999999",
      "promo": "90% si traes a tu mascota",
      "dietary_restrictions": [],
      "owner_id": 3,
      "owner_name": "Juan Empresario",
      "id": 24
    },
    "user_id": 1,
    "reason": "Preevaluación automática",
    "status": "pending",
    "approval_status": "PENDIENTE_REVISION",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v1",
      "content_type": "restaurant",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description",
          "category"
        ],
        "missing_fields": [
          "category"
        ],
        "critical_signal": false,
        "food_score": 25.0,
        "banned_words": [],
        "food_words_found": [
          "comida",
          "saludable"
        ]
      },
      "issues": [
        "Contenido relacionado con comida verificado correctamente.",
        "Campos requeridos ausentes: category"
      ],
      "human_review_required": true
    },
    "decision_source": "AI_PRECHECK",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; sujeta a revisión administrativa cuando corresponda.",
        "timestamp": "2026-10-14T05:40:34.560149+00:00"
      }
    ],
    "created_at": "2026-10-14T05:40:34.560149+00:00",
    "updated_at": "2026-10-14T05:40:37.560621+00:00",
    "id": 36,
    "legacy_id": 24
  },
  {
    "content_type": "restaurant",
    "content_id": 27,
    "content_data": {
      "name": "Utp",
      "district": "Victor Larco",
      "category_id": 7,
      "lat": -8.1419,
      "lng": -79.0436,
      "avg_price": 6.5,
      "rating": 3.2,
      "open_time": "12:00",
      "close_time": "22:00",
      "image": "",
      "description": "CAFE UTP",
      "address": "Vista Alegre, Víctor Larco Herrera, Trujillo, La Libertad, 13009, Perú",
      "phone": "906 963 631",
      "promo": "",
      "service_mode": "dine_in_and_delivery",
      "tags": [
        "postres",
        "cafe"
      ],
      "features": [
        "wifi",
        "reservas",
        "terraza",
        "estacionamiento",
        "pet friendly"
      ],
      "dietary_restrictions": [],
      "owner_id": 5,
      "owner_name": "Enrique",
      "id": 27,
      "dishes": [
        120,
        121,
        122,
        123,
        124,
        125,
        126,
        127
      ],
      "menu_intro": "Carta de restaurante peruano con platos como Ceviche de pescado, Causa limeña de pollo, Shambar, Arroz con pato, Lomo saltado, Pan con chicharrón, Suspiro limeño y Chicha morada."
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "ASK_AI",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 14.29,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "cafe",
          "postres"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.29,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [
        "Parece no estar relacionado con comida"
      ],
      "notes": [],
      "human_review_required": true
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-15T17:07:10.966435+00:00"
      },
      {
        "from": "PENDIENTE_REVISION",
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "Todo por la nota",
        "timestamp": "2026-10-15T17:07:11.044961+00:00"
      }
    ],
    "created_at": "2026-10-15T17:07:10.966435+00:00",
    "updated_at": "2026-10-15T17:07:11.044961+00:00",
    "id": 25,
    "admin_notes": "Todo por la nota",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-15T17:07:11.044961+00:00"
  },
  {
    "content_type": "restaurant",
    "content_id": 28,
    "content_data": {
      "name": "Pizza Rica",
      "district": "Trujillo",
      "category_id": 3,
      "lat": -8.0996,
      "lng": -79.0379,
      "avg_price": 40.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR-wdWaG3ApkfZHHpvS1cSSGZa1DE6YjjZkpm2-wrmw_WiDkcA1HbivXS5v&s=10",
      "description": "Pizza estilo argentino",
      "address": "380, Calle el Opalo, Urbanización Santa Inés, Trujillo, La Libertad, 13011, Perú",
      "phone": "942038151",
      "promo": "",
      "service_mode": "delivery_only",
      "tags": [
        "tradicional",
        "familiar"
      ],
      "features": [],
      "dietary_restrictions": [],
      "owner_id": 6,
      "owner_name": "RicaPizza",
      "id": 28,
      "dishes": [
        128,
        129,
        130,
        131,
        132,
        133,
        134,
        135,
        136,
        137,
        138,
        139,
        140
      ],
      "menu_intro": "Carta de pizzas con masa artesanal al estilo argentino, disponible en formatos medianos, grandes y personales, acompañada de opciones de combos con gaseosas."
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "PENDIENTE_REVISION",
    "ai_confidence": 0.55,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "ASK_AI",
      "ai_verdict": "PENDIENTE_REVISION",
      "final_status": "PENDIENTE_REVISION",
      "confidence": 0.55,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 10.67,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "pizza"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.35,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [
        "Parece no estar relacionado con comida"
      ],
      "notes": [],
      "human_review_required": true
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": true,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "PENDIENTE_REVISION",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-15T18:51:06.802324+00:00"
      },
      {
        "from": "PENDIENTE_REVISION",
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "bien",
        "timestamp": "2026-10-15T18:51:06.843006+00:00"
      }
    ],
    "created_at": "2026-10-15T18:51:06.802324+00:00",
    "updated_at": "2026-10-15T18:51:06.843006+00:00",
    "id": 26,
    "admin_notes": "bien",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-15T18:51:06.843006+00:00"
  },
  {
    "content_type": "restaurant",
    "content_id": 29,
    "content_data": {
      "name": "Mathias",
      "district": "La Esperanza",
      "category_id": 11,
      "lat": -8.1,
      "lng": -78.9948,
      "avg_price": 12.0,
      "rating": 4.0,
      "open_time": "12:00",
      "close_time": "22:00",
      "image": "",
      "description": "Mathias menu",
      "address": "Pesqueda, Trujillo, La Libertad, 13007, Perú",
      "phone": "998898989",
      "promo": "",
      "service_mode": "dine_in_only",
      "tags": [
        "criollo",
        "familiar"
      ],
      "features": [],
      "dietary_restrictions": [],
      "owner_id": 7,
      "owner_name": "Mathias",
      "id": 29,
      "dishes": [
        141,
        142,
        143,
        144,
        145,
        146,
        147,
        148,
        149,
        150,
        151,
        152,
        153,
        154,
        155,
        156,
        157,
        158
      ],
      "menu_intro": "Carta de restaurante peruano que incluye entradas como sopa, ceviche y papa a la huancaína, así como fondos variados de carne, pollo, mariscos y vegetales."
    },
    "user_id": 1,
    "reason": "Registro creado durante revisión administrativa",
    "status": "approved",
    "approval_status": "APROBADO_AUTOMATICAMENTE",
    "ai_verdict": "APROBADO_AUTOMATICAMENTE",
    "ai_confidence": 0.9,
    "ai_evaluation": {
      "model_version": "content-filter-rules-v2",
      "content_type": "restaurant",
      "route": "AUTO_OK",
      "ai_verdict": "APROBADO_AUTOMATICAMENTE",
      "final_status": "APROBADO_AUTOMATICAMENTE",
      "confidence": 0.9,
      "rules": {
        "required_fields": [
          "name",
          "description"
        ],
        "missing_fields": [],
        "critical_signal": false,
        "evasion_suspected": false,
        "dictionary_can_judge": true,
        "food_score": 23.0,
        "banned_words": [],
        "context_words": [],
        "food_words_found": [
          "criollo",
          "menu"
        ],
        "coverage": {
          "script_ratio": 0.0,
          "known_ratio": 0.4,
          "foreign_markers": 0,
          "unknown_language": false
        },
        "inappropriate_tags": []
      },
      "issues": [],
      "notes": [
        "Contenido culinario verificado"
      ],
      "human_review_required": false
    },
    "decision_source": "ADMIN_REVIEW",
    "flagged": false,
    "flags": [],
    "reversible": true,
    "status_history": [
      {
        "from": null,
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": null,
        "source": "AI_PRECHECK",
        "notes": "Preevaluación automática; no sustituye la revisión administrativa.",
        "timestamp": "2026-10-15T18:55:31.768371+00:00"
      },
      {
        "from": "APROBADO_AUTOMATICAMENTE",
        "to": "APROBADO_AUTOMATICAMENTE",
        "actor_user_id": 1,
        "source": "ADMIN_REVIEW",
        "notes": "Bien",
        "timestamp": "2026-10-15T18:55:31.810878+00:00"
      }
    ],
    "created_at": "2026-10-15T18:55:31.768371+00:00",
    "updated_at": "2026-10-15T18:55:31.810878+00:00",
    "id": 27,
    "admin_notes": "Bien",
    "human_decision_by": 1,
    "human_decision_at": "2026-10-15T18:55:31.810878+00:00"
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'moderation', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'moderation' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'notifications', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'notifications' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "id": 1,
    "restaurant_id": 1,
    "description": "10% de descuento en Cabrito",
    "valid_until": "2026-12-31",
    "discount_percent": 10
  },
  {
    "id": 2,
    "restaurant_id": 6,
    "description": "All you can eat los martes",
    "valid_until": "2026-08-30",
    "discount_percent": 20
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'promotions', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'promotions' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "id": 1,
    "user_id": 1,
    "restaurant_id": 2,
    "rating": 5,
    "comment": "Excelente ceviche, el mejor de Huanchaco. La vista al mar es espectacular.",
    "created_at": "2026-06-28T14:30:00",
    "updated_at": "2026-06-28T14:30:00"
  },
  {
    "id": 2,
    "user_id": 2,
    "restaurant_id": 1,
    "rating": 4,
    "comment": "Muy buena comida tradicional. El cabrito estaba delicioso.",
    "created_at": "2026-06-27T12:15:00",
    "updated_at": "2026-06-27T12:15:00"
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'reviews', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'reviews' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH origen AS (
  SELECT value AS payload FROM jsonb_array_elements($smartresto_origen$[
  {
    "id": 1,
    "username": "admin",
    "password": "scrypt:32768:8:1$hq0c66Q1eYFVnpWb$a738b8128d3410125ae1d328d71808cf36869cded890460f3cdecff30c816ab75888ee7a998f9d25a748cacf1d3be769b1e084341023286808f17c3eaf149d6e",
    "role": "admin",
    "profile": {
      "name": "Admin",
      "email": "admin@smartresto.com",
      "preferences": [],
      "restrictions": [],
      "history": []
    }
  },
  {
    "id": 2,
    "username": "nesch0811",
    "password": "scrypt:32768:8:1$Cw85oXuJI9xGxISl$5c811bc1436814ad6a2bbf23f480cf46fb10844a8cb96b34476e3d066a09544972f4e589eee8e0bb827dc1e9ecd6f3d598e6ef65b641f03e50afe9e56efdabf9",
    "role": "user",
    "profile": {
      "name": "Nancy Elizabeth Sandoval Chacón",
      "email": "liza08111522@gmail.com",
      "preferences": [
        "tradicional",
        "mariscos",
        "criolla",
        "italiana",
        "japonesa",
        "saludable"
      ],
      "restrictions": [],
      "history": []
    }
  },
  {
    "id": 3,
    "username": "empresario",
    "password": "scrypt:32768:8:1$hq0c66Q1eYFVnpWb$a738b8128d3410125ae1d328d71808cf36869cded890460f3cdecff30c816ab75888ee7a998f9d25a748cacf1d3be769b1e084341023286808f17c3eaf149d6e",
    "role": "business_owner",
    "profile": {
      "name": "Enrique Empresario",
      "email": "enrique@restaurante.com",
      "preferences": [],
      "restrictions": [],
      "history": []
    }
  },
  {
    "username": "Enrique12",
    "password": "scrypt:32768:8:1$QdQojeCQvNMF7MON$7c99c0db8c9f14b3810cd64a063e49040bf925b7d498a88abb4f728570c4f6e4d4cf7c1a247969d73980baee3d2bfdb915a0d92f6e4e5f5c346687ce3aa0a8f8",
    "role": "business_owner",
    "profile": {
      "name": "Enrique",
      "email": "dfgt.545@gmail.com",
      "preferences": [],
      "restrictions": []
    },
    "id": 5
  },
  {
    "username": "RicaPizza",
    "password": "scrypt:32768:8:1$UdHGMMbUwJaHdZBe$97ceeecd661fdfc5cc92f17004acc8648f4bbd4f5555e86fbe8ffb9b905fdd4b296e01e0717e0c5968bc6e299255ef5af88fbd8ff4624bb369ba692e6b9b54a7",
    "role": "business_owner",
    "profile": {
      "name": "RicaPizza",
      "email": "ricapizza@gmail.com",
      "preferences": [],
      "restrictions": []
    },
    "id": 6
  },
  {
    "username": "Mathias",
    "password": "scrypt:32768:8:1$GnkgFnW7swEPFgCD$318c6d1ca5738a300f64549d10587f177a3e43996c32e72e4eac6a4da1369b6272ba03bf4e8edcf9b4f3445b7079a1260702e3aa289eb794b673f2041c58a700",
    "role": "business_owner",
    "profile": {
      "name": "Mathias",
      "email": "mathias@gmail.com",
      "preferences": [],
      "restrictions": []
    },
    "id": 7
  },
  {
    "username": "Pollos",
    "password": "scrypt:32768:8:1$JRLrTClSo44CSabg$a13c61ad5942977fd0e5b8c962b34160223b5e29c2498e5730babf912984c742ac8cf16c7db8970894573f7276164a71d50eb4cb916708f01334801a0032c989",
    "role": "business_owner",
    "profile": {
      "name": "Miguel",
      "email": "pollos@gmail.com",
      "preferences": [],
      "restrictions": []
    },
    "id": 8
  }
]$smartresto_origen$::jsonb)
), nuevos AS (
  INSERT INTO public.app_records(collection,id,payload)
  SELECT 'users', (payload->>'id')::bigint, payload FROM origen
  ON CONFLICT(collection,id) DO NOTHING RETURNING id
)
SELECT 'users' AS coleccion, (SELECT count(*) FROM origen) AS en_json,
       count(*) AS insertados, (SELECT count(*) FROM origen)-count(*) AS ya_existentes FROM nuevos;

WITH identidad AS (
 SELECT pg_get_serial_sequence('public.app_records','id')::regclass AS secuencia,max(id) AS maximo FROM public.app_records
)
SELECT setval(secuencia,maximo,true) FROM identidad WHERE maximo>COALESCE(pg_sequence_last_value(secuencia),0);
COMMIT;
