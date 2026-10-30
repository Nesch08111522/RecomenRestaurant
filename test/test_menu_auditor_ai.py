import json
import unittest
from unittest.mock import Mock
from utils.menu_auditor_ai import auditar_plato_con_ia


class TestAuditorMenuIA(unittest.TestCase):
    def setUp(self):
        self.ambiguous = {
            "id": 7,
            "name": "Tallarines verdes",
            "ingredients": ["pasta", "salsa"],
            "dietary_info": ["sin lactosa"],
        }
        self.answer = json.dumps(
            {
                "summary": "Falta conocer la salsa.",
                "questions": ["¿La salsa contiene lácteos?"],
                "needs_owner_confirmation": True,
            }
        )

    def test_consulta_cuando_hay_ambiguedad(self):
        mock = Mock(return_value=self.answer)
        result = auditar_plato_con_ia(self.ambiguous, consultar_ia=mock)
        self.assertEqual(result["ai"]["status"], "ok")
        self.assertEqual(result["result"], "desconocido")
        self.assertTrue(result["requires_owner_confirmation"])
        mock.assert_called_once()

    def test_no_consulta_si_hay_contradiccion(self):
        mock = Mock()
        result = auditar_plato_con_ia(
            {"name": "Chaufa", "ingredients": ["huevo"], "dietary_info": ["vegano"]},
            consultar_ia=mock,
        )
        self.assertEqual(result["result"], "incoherente")
        mock.assert_not_called()

    def test_no_consulta_sin_etiqueta(self):
        mock = Mock()
        result = auditar_plato_con_ia(
            {"name": "Arroz", "ingredients": ["arroz"]}, consultar_ia=mock
        )
        self.assertEqual(result["ai"]["status"], "not_needed")
        mock.assert_not_called()

    def test_fallo_de_proveedor_no_rompe_auditoria(self):
        mock = Mock(side_effect=RuntimeError("sin servicio"))
        result = auditar_plato_con_ia(self.ambiguous, consultar_ia=mock)
        self.assertEqual(result["ai"]["status"], "unavailable")
        self.assertEqual(result["result"], "desconocido")

    def test_json_invalido_se_descarta(self):
        result = auditar_plato_con_ia(
            self.ambiguous, consultar_ia=Mock(return_value="```json\n{}\n```")
        )
        self.assertEqual(result["ai"]["status"], "unavailable")

    def test_json_con_campos_extra_se_descarta(self):
        data = json.loads(self.answer)
        data["publication_action"] = "aprobar"
        result = auditar_plato_con_ia(
            self.ambiguous, consultar_ia=Mock(return_value=json.dumps(data))
        )
        self.assertEqual(result["ai"]["status"], "unavailable")

    def test_ia_no_puede_certificar_ni_cambiar_estado(self):
        result = auditar_plato_con_ia(
            self.ambiguous, consultar_ia=Mock(return_value=self.answer)
        )
        self.assertEqual(
            result["publication_action"], "permitir_sin_verificacion_dietetica"
        )
        self.assertTrue(result["ai"]["suggestion"]["needs_owner_confirmation"])

    def test_no_modifica_datos_originales(self):
        dish = dict(self.ambiguous)
        auditar_plato_con_ia(dish, consultar_ia=Mock(return_value=self.answer))
        self.assertEqual(dish, self.ambiguous)


if __name__ == "__main__":
    unittest.main()
