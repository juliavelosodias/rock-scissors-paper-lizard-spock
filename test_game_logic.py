import random
import unittest

from game_logic import GESTOS, WINS_AGAINST, comparar, jogada_computador


class GameLogicTests(unittest.TestCase):
    def test_todas_as_vitorias(self):
        for vencedor, perdedores in WINS_AGAINST.items():
            for perdedor in perdedores:
                self.assertEqual(comparar(vencedor, perdedor)[0], "VITORIA")
                self.assertEqual(comparar(perdedor, vencedor)[0], "DERROTA")

    def test_empates(self):
        for gesto in GESTOS:
            self.assertEqual(comparar(gesto, gesto), ("EMPATE", "Jogadas iguais"))

    def test_escolha_reprodutivel(self):
        self.assertEqual(jogada_computador(random.Random(7)), "TESOURA")

    def test_jogada_invalida(self):
        with self.assertRaises(ValueError):
            comparar("BANANA", "PEDRA")


if __name__ == "__main__":
    unittest.main()

