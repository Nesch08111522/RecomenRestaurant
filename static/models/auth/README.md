# SmartResto — modelos gastronómicos locales

Cuatro GLB de geometría real, con materiales PBR y texturas incrustadas. Representaciones procedurales de referencia, no escaneos fotogramétricos ni reproducciones exactas de productos de los negocios.

La API prioriza el modelo GLB publicado del plato cuando existe; de lo contrario identifica claramente esta representación de referencia. Cada modelo es sustituible por un GLB profesional optimizado sin modificar formularios ni autenticación.

Construcción: `.work/auth-experience/build_models.py`; dependencia de compilación `trimesh==4.6.13`. Flask no necesita trimesh en producción.
