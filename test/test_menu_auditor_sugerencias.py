import unittest
from utils.menu_auditor import auditar_plato
from utils.menu_auditor_ai import sugerir_correccion_con_ia


class TestSugerencias(unittest.TestCase):
    def setUp(self):
        self.plato = {
            "id": 7,
            "name": "Ensalada César vegana",
            "ingredients": ["lechuga", "queso parmesano"],
            "dietary_info": ["Vegano"],
        }

    def test_sugerencia_valida(self):
        before = self.plato.copy()
        result = sugerir_correccion_con_ia(
            self.plato,
            consultar_ia=lambda *args, **kwargs: '{"summary":"Revisa la etiqueta.","options":["Retira la etiqueta vegana.","Sustituye el queso y verifica la receta."]}',
        )
        self.assertEqual(len(result["options"]), 2)
        self.assertEqual(before, self.plato)

    def test_no_pedir_si_no_hay_conflicto(self):
        with self.assertRaises(ValueError):
            sugerir_correccion_con_ia(
                {"name": "Causa", "ingredients": ["papa"]},
                consultar_ia=lambda *a, **k: "{}",
            )

    def test_rechaza_campos_extra(self):
        with self.assertRaises(ValueError):
            sugerir_correccion_con_ia(
                self.plato,
                consultar_ia=lambda *a, **k: '{"summary":"Hola","options":["Retira etiqueta"],"approved":true}',
            )

    def test_advertencia_corta(self):
        r = auditar_plato(
            {"name": "Causa", "ingredients": ["papa"], "dietary_info": ["Sin gluten"]}
        )
        self.assertNotIn("contaminación cruzada", r["observations"][-1]["reason"])


if __name__ == "__main__":
    unittest.main()
