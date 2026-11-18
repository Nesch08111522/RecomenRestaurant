import unittest
from utils.moderation_explain import (
    evaluar_restaurante,
    estado_pendiente,
    motivo_contenido,
)


class FilterStub:
    @staticmethod
    def filter_restaurant(restaurant):
        return {"is_ok": True, "issues": [], "result": {"food_score": 65}}


class TestModeracion(unittest.TestCase):
    def test_mrd_detectado(self):
        r = evaluar_restaurante({"name": "Calla Mrd"}, FilterStub)
        self.assertTrue(r["needs_review"])
        self.assertIn("ofensivo", r["issues"][0])

    def test_nombre_normal(self):
        self.assertFalse(
            evaluar_restaurante({"name": "O Rica Pizza"}, FilterStub)["needs_review"]
        )

    def test_rechazado_no_reaparece_pendiente(self):
        self.assertFalse(
            estado_pendiente({"verified": False, "approval_status": "rejected"})
        )

    def test_pendiente_real(self):
        self.assertTrue(
            estado_pendiente({"verified": False, "approval_status": "pending"})
        )

    def test_motivo_generico_no_es_infraccion(self):
        self.assertIn(
            "No se registró", motivo_contenido({"reason": "Preevaluación automática"})
        )


if __name__ == "__main__":
    unittest.main()
