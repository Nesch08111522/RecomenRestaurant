import ast
from pathlib import Path

def test_migration_has_no_embedded_postgres_credentials():
    tree=ast.parse(Path('migrar.py').read_text(encoding='utf-8-sig'))
    assert not any(isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith(('postgres://','postgresql://')) for n in ast.walk(tree)), 'Las URI deben venir del entorno'
