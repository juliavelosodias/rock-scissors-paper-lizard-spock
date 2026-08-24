"""Classificação heurística de gestos a partir dos 21 landmarks do MediaPipe."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class ResultadoGesto:
    gesto: str
    confianca: float
    pontuacoes: dict[str, float]


def _pontos(landmarks: object) -> np.ndarray:
    origem = getattr(landmarks, "landmark", landmarks)
    pontos = np.asarray([[p.x, p.y, getattr(p, "z", 0.0)] for p in origem], dtype=float)
    if pontos.shape != (21, 3):
        raise ValueError("São necessários exatamente 21 landmarks")
    return pontos


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _angulo(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba, bc = a - b, c - b
    denominador = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denominador < 1e-9:
        return 0.0
    cosseno = float(np.clip(np.dot(ba, bc) / denominador, -1.0, 1.0))
    return math.degrees(math.acos(cosseno))


def _faixa(valor: float, inicio: float, fim: float, margem: float) -> float:
    """Pontuação suave: 1 dentro da faixa, cai linearmente até zero."""
    if inicio <= valor <= fim:
        return 1.0
    distancia = inicio - valor if valor < inicio else valor - fim
    return max(0.0, 1.0 - distancia / margem)


def _maior_que(valor: float, limite: float, margem: float) -> float:
    return float(np.clip((valor - limite + margem) / margem, 0.0, 1.0))


def _menor_que(valor: float, limite: float, margem: float) -> float:
    return float(np.clip((limite + margem - valor) / margem, 0.0, 1.0))


def _minimo(*valores: float) -> float:
    return float(min(valores))


def _caracteristicas(landmarks: object) -> dict[str, object]:
    p = _pontos(landmarks)
    # Escala robusta: largura da palma (5-17) combinada com pulso-dedo médio (0-9).
    escala = (_dist(p[5], p[17]) + _dist(p[0], p[9])) / 2.0
    if escala < 1e-6:
        raise ValueError("Landmarks degenerados")

    dedos = {
        "indicador": (5, 6, 7, 8),
        "medio": (9, 10, 11, 12),
        "anelar": (13, 14, 15, 16),
        "minimo": (17, 18, 19, 20),
    }
    extensao: dict[str, float] = {}
    angulos: dict[str, float] = {}
    for nome, (mcp, pip, dip, tip) in dedos.items():
        angulo_pip = _angulo(p[mcp], p[pip], p[tip])
        angulo_dip = _angulo(p[pip], p[dip], p[tip])
        alcance = _dist(p[tip], p[mcp]) / escala
        angulos[nome] = angulo_pip
        extensao[nome] = _minimo(
            _maior_que(angulo_pip, 145.0, 25.0),
            _maior_que(angulo_dip, 145.0, 25.0),
            _maior_que(alcance, 0.72, 0.22),
        )

    angulo_polegar = _angulo(p[2], p[3], p[4])
    alcance_polegar = _dist(p[4], p[2]) / escala
    extensao_polegar = _minimo(
        _maior_que(angulo_polegar, 135.0, 30.0),
        _maior_que(alcance_polegar, 0.48, 0.18),
    )

    return {
        "p": p,
        "escala": escala,
        "ext": extensao,
        "ext_polegar": extensao_polegar,
        "angulos": angulos,
        "dist_pontas": {
            "im": _dist(p[8], p[12]) / escala,
            "ma": _dist(p[12], p[16]) / escala,
            "am": _dist(p[16], p[20]) / escala,
            "pi": _dist(p[4], p[8]) / escala,
        },
        "dist_articulacoes": {
            "im": _dist(p[7], p[11]) / escala,
            "ma": _dist(p[11], p[15]) / escala,
            "am": _dist(p[15], p[19]) / escala,
        },
    }


def detectar_spock(landmarks: object) -> float:
    """Confiança de Spock: quatro dedos retos, dois pares e vão central."""
    f = _caracteristicas(landmarks)
    e, d, j = f["ext"], f["dist_pontas"], f["dist_articulacoes"]

    valores_extensao = list(e.values())
    media_extensao = sum(valores_extensao) / 4.0
    # Mindinho e anelar costumam parecer levemente curvos por perspectiva.
    dedos_estendidos = _minimo(
        _maior_que(media_extensao, 0.62, 0.18),
        _maior_que(min(valores_extensao), 0.38, 0.22),
    )

    pares = _minimo(
        _menor_que(d["im"], 0.52, 0.18),
        _menor_que(d["am"], 0.52, 0.18),
    )
    razao_pontas = d["ma"] / max((d["im"] + d["am"]) / 2.0, 0.05)
    razao_articulacoes = j["ma"] / max((j["im"] + j["am"]) / 2.0, 0.05)
    separacao = max(razao_pontas, razao_articulacoes)
    vao = _maior_que(d["ma"], 0.30, 0.16)
    return _minimo(
        dedos_estendidos,
        pares,
        vao,
        _maior_que(separacao, 1.12, 0.30),
    )


def detectar_lagarto(landmarks: object) -> float:
    """Confiança do C usando abertura, curvatura e estado dos outros dedos."""
    f = _caracteristicas(landmarks)
    e, a, d, p = f["ext"], f["angulos"], f["dist_pontas"], f["p"]
    escala = float(f["escala"])
    indicador_curvo = _faixa(a["indicador"], 72.0, 145.0, 28.0)
    abertura_c = _faixa(d["pi"], 0.32, 1.02, 0.18)
    angulo_polegar = _angulo(p[2], p[3], p[4])
    polegar_util = max(
        _faixa(angulo_polegar, 75.0, 170.0, 25.0),
        _maior_que(_dist(p[4], p[2]) / escala, 0.32, 0.18),
    )
    # Ponta do indicador e polegar devem se projetar à frente das bases, formando boca do C.
    projecao = _minimo(
        _maior_que(_dist(p[8], p[5]) / escala, 0.42, 0.20),
        _maior_que(_dist(p[4], p[2]) / escala, 0.30, 0.16),
    )
    curvaturas = [1.0 - e[n] for n in ("medio", "anelar", "minimo")]
    outros_curvos = _maior_que(sum(curvaturas) / 3.0, 0.38, 0.28)

    # Abertura e indicador curvo são travas contra Pedra e Papel. Demais sinais
    # são combinados para tolerar anatomia e rotação diferentes.
    forma = (
        0.34 * indicador_curvo
        + 0.22 * polegar_util
        + 0.22 * projecao
        + 0.22 * outros_curvos
    )
    return _minimo(abertura_c, indicador_curvo, forma)


def reconhecer_com_confianca(landmarks: object, limite: float = 0.68) -> ResultadoGesto:
    f = _caracteristicas(landmarks)
    e, d = f["ext"], f["dist_pontas"]
    aberto = [e[n] for n in ("indicador", "medio", "anelar", "minimo")]
    fechado = [1.0 - x for x in aberto]

    spock = detectar_spock(landmarks)
    lagarto = detectar_lagarto(landmarks)
    j = f["dist_articulacoes"]
    separacao_papel = max(
        d["ma"] / max((d["im"] + d["am"]) / 2.0, 0.05),
        j["ma"] / max((j["im"] + j["am"]) / 2.0, 0.05),
    )
    papel = _minimo(
        *aberto,
        float(f["ext_polegar"]),
        _menor_que(d["ma"], 0.55, 0.20),
        _menor_que(separacao_papel, 1.18, 0.25),
    )
    tesoura = _minimo(
        e["indicador"], e["medio"], 1.0 - e["anelar"], 1.0 - e["minimo"],
        _maior_que(d["im"], 0.18, 0.12),
    )
    pedra = _minimo(*fechado, _menor_que(d["pi"], 0.78, 0.25))

    pontuacoes = {
        "PEDRA": pedra,
        "PAPEL": papel,
        "TESOURA": tesoura,
        "LAGARTO": lagarto,
        "SPOCK": spock,
    }
    ordenadas = sorted(pontuacoes.items(), key=lambda item: item[1], reverse=True)
    gesto, confianca = ordenadas[0]
    # Exige margem sobre a segunda hipótese para tratar poses ambíguas como desconhecidas.
    if confianca < limite or confianca - ordenadas[1][1] < 0.10:
        gesto = "DESCONHECIDO"
    return ResultadoGesto(gesto, round(float(confianca), 3), pontuacoes)


def reconhecer_gesto(landmarks: object) -> str:
    return reconhecer_com_confianca(landmarks).gesto
