"""Regras do jogo Pedra, Papel, Tesoura, Lagarto e Spock."""

from __future__ import annotations

import random

GESTOS = ("PEDRA", "PAPEL", "TESOURA", "LAGARTO", "SPOCK")

WINS_AGAINST = {
    "PEDRA": ("TESOURA", "LAGARTO"),
    "PAPEL": ("PEDRA", "SPOCK"),
    "TESOURA": ("PAPEL", "LAGARTO"),
    "LAGARTO": ("SPOCK", "PAPEL"),
    "SPOCK": ("TESOURA", "PEDRA"),
}

ACOES = {
    ("TESOURA", "PAPEL"): "Tesoura corta Papel",
    ("PAPEL", "PEDRA"): "Papel cobre Pedra",
    ("PEDRA", "LAGARTO"): "Pedra esmaga Lagarto",
    ("LAGARTO", "SPOCK"): "Lagarto envenena Spock",
    ("SPOCK", "TESOURA"): "Spock quebra Tesoura",
    ("TESOURA", "LAGARTO"): "Tesoura decapita Lagarto",
    ("LAGARTO", "PAPEL"): "Lagarto come Papel",
    ("PAPEL", "SPOCK"): "Papel refuta Spock",
    ("SPOCK", "PEDRA"): "Spock vaporiza Pedra",
    ("PEDRA", "TESOURA"): "Pedra quebra Tesoura",
}


def jogada_computador(rng: random.Random | None = None) -> str:
    return (rng or random).choice(GESTOS)


def comparar(jogador: str, computador: str) -> tuple[str, str]:
    """Retorna (resultado, explicação), com resultado em VITORIA/DERROTA/EMPATE."""
    if jogador not in GESTOS or computador not in GESTOS:
        raise ValueError("Jogada inválida")
    if jogador == computador:
        return "EMPATE", "Jogadas iguais"
    if computador in WINS_AGAINST[jogador]:
        return "VITORIA", ACOES[(jogador, computador)]
    return "DERROTA", ACOES[(computador, jogador)]

