"""La regla de devolución, sin modelo ni red."""

import unittest

from app.agents import juzgar


class Reglas(unittest.TestCase):
    def test_monto_fuera_de_tope(self):
        texto = juzgar(9, 21000, 10, 20000, False)
        self.assertTrue(texto.startswith("No corresponde"))
        self.assertIn("21000", texto)

    def test_plazo_vencido(self):
        texto = juzgar(12, 14500, 10, 20000, False)
        self.assertTrue(texto.startswith("No corresponde"))
        self.assertIn("plazo", texto)

    def test_codigo_canjeado(self):
        texto = juzgar(10, 18000, 10, 20000, True)
        self.assertTrue(texto.startswith("No corresponde"))
        self.assertIn("canjeó", texto)

    def test_corresponde(self):
        texto = juzgar(3, 8000, 10, 20000, False)
        self.assertTrue(texto.startswith("Corresponde"))
