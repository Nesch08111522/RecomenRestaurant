import unittest
from utils.menu_auditor import auditar_plato, auditar_menu


class TestAuditorMenu(unittest.TestCase):
    def test_vegano_con_huevo(self):
        r = auditar_plato(
            {
                "name": "Chaufa",
                "ingredients": ["arroz", "huevo"],
                "dietary_info": ["Vegano"],
            }
        )
        self.assertEqual(r["result"], "incoherente")
        self.assertTrue(r["requires_admin_review"])

    def test_sin_lactosa_con_queso(self):
        r = auditar_plato(
            {
                "name": "Tallarines",
                "ingredients": ["queso fresco"],
                "dietary_info": ["Sin lactosa"],
            }
        )
        self.assertEqual(r["result"], "incoherente")

    def test_sin_gluten_con_trigo(self):
        r = auditar_plato(
            {
                "name": "Pan",
                "ingredients": ["harina de trigo"],
                "dietary_info": ["Sin gluten"],
            }
        )
        self.assertEqual(r["result"], "incoherente")

    def test_sin_ingredientes_no_bloquea(self):
        r = auditar_plato({"name": "Ceviche", "ingredients": [], "dietary_info": []})
        self.assertEqual(r["publication_action"], "permitir")
        self.assertFalse(r["requires_admin_review"])

    def test_sin_ingredientes_con_etiqueta(self):
        r = auditar_plato({"name": "Ensalada", "dietary_info": ["Vegano"]})
        self.assertEqual(r["result"], "desconocido")
        self.assertEqual(r["publication_action"], "permitir_sin_verificacion_dietetica")

    def test_salsa_ambigua(self):
        r = auditar_plato(
            {
                "name": "Pasta",
                "ingredients": ["salsa verde"],
                "dietary_info": ["Sin lactosa"],
            }
        )
        self.assertEqual(r["result"], "desconocido")

    def test_sin_etiqueta_no_certifica(self):
        r = auditar_plato({"name": "Lomo saltado", "ingredients": ["carne", "papas"]})
        self.assertEqual(r["result"], "sin_contradicciones_evidentes")
        self.assertIn("no certifica", r["disclaimer"])

    def test_menu_resumen(self):
        r = auditar_menu(
            [
                {"name": "A", "ingredients": ["pollo"], "dietary_info": ["Vegano"]},
                {"name": "B", "ingredients": []},
            ]
        )
        self.assertEqual((r["total"], r["incoherentes"], r["desconocidos"]), (2, 1, 1))

    def test_no_detecta_falso_positivo_subcadena(self):
        r = auditar_plato(
            {
                "name": "Comida",
                "ingredients": ["huevos de codorniz"],
                "dietary_info": ["Vegano"],
            }
        )
        self.assertEqual(r["result"], "incoherente")

    def test_leche_deslactosada_no_certifica(self):
        r = auditar_plato(
            {
                "name": "Batido",
                "ingredients": ["leche deslactosada"],
                "dietary_info": ["Sin lactosa"],
            }
        )
        self.assertEqual(r["result"], "desconocido")


if __name__ == "__main__":
    unittest.main()
