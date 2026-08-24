"""Interface OpenCV do jogo Pedra, Papel, Tesoura, Lagarto e Spock."""

from __future__ import annotations

import time
from pathlib import Path
import shutil
import tempfile
from bisect import bisect_right

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageSequence

from game_logic import comparar, jogada_computador
from gesture_recognition import reconhecer_com_confianca

LARGURA, ALTURA = 1120, 720
TEMPO_CONTAGEM = 3.0
TEMPO_ESTAVEL = 1.0
TEMPO_RESULTADO = 3.0

# Paleta institucional em BGR (formato usado pelo OpenCV).
VERDE = (54, 137, 0)
VERDE_ESCURO = (31, 78, 0)
VERDE_CLARO = (112, 196, 72)
BRANCO = (255, 255, 255)
CINZA_CLARO = (225, 230, 228)

ARQUIVOS_GIF = {
    "PEDRA": "pedra.gif",
    "PAPEL": "paper.gif",
    "TESOURA": "scissors.gif",
    "LAGARTO": "lizard.gif",
    "SPOCK": "spock.gif",
}


def preparar_recursos_mediapipe() -> None:
    """Contorna falha nativa do MediaPipe com caminhos Windows não ASCII."""
    pacote = Path(mp.__file__).resolve().parent
    if pacote.as_posix().isascii():
        return

    from mediapipe.python import solution_base

    versao = getattr(mp, "__version__", "desconhecida")
    raiz_cache = Path(tempfile.gettempdir()) / "rpsls_mediapipe" / versao
    modulos_cache = raiz_cache / "mediapipe" / "modules"
    marcador = raiz_cache / ".completo"
    if not marcador.exists():
        modulos_cache.mkdir(parents=True, exist_ok=True)
        for nome in ("hand_landmark", "palm_detection"):
            shutil.copytree(
                pacote / "modules" / nome,
                modulos_cache / nome,
                dirs_exist_ok=True,
            )
        marcador.write_text(versao, encoding="ascii")

    # SolutionBase calcula raiz dos modelos usando seu próprio __file__.
    solution_base.__file__ = str(
        raiz_cache / "mediapipe" / "python" / "solution_base.py"
    )


def carregar_gifs(tamanho_maximo=230):
    """Carrega GIFs como frames BGRA mantendo duração e proporção."""
    pasta = Path(__file__).resolve().parent / "scr"
    animacoes = {}
    for gesto, nome in ARQUIVOS_GIF.items():
        caminho = pasta / nome
        if not caminho.exists():
            continue

        frames, finais, acumulado = [], [], 0.0
        with Image.open(caminho) as gif:
            for quadro in ImageSequence.Iterator(gif):
                imagem = quadro.convert("RGBA")
                imagem.thumbnail((tamanho_maximo, tamanho_maximo), Image.Resampling.LANCZOS)
                rgba = np.asarray(imagem).copy()
                frames.append(cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
                duracao_ms = int(quadro.info.get("duration", gif.info.get("duration", 100)))
                acumulado += max(20, duracao_ms) / 1000.0
                finais.append(acumulado)
        if frames:
            animacoes[gesto] = (frames, finais, acumulado)
    return animacoes


def desenhar_gif(frame, animacao, decorrido):
    frames, finais, duracao_total = animacao
    instante = decorrido % duracao_total
    indice = min(bisect_right(finais, instante), len(frames) - 1)
    gif = frames[indice]
    altura, largura = gif.shape[:2]
    x, y = 22, ALTURA - altura - 22
    destino = frame[y:y + altura, x:x + largura]
    alpha = gif[:, :, 3:4].astype(np.float32) / 255.0
    destino[:] = (gif[:, :, :3] * alpha + destino * (1.0 - alpha)).astype(np.uint8)


def texto(frame, conteudo, posicao, escala=0.7, cor=BRANCO, espessura=2):
    """Texto arcade nítido, sem antialiasing, com sombra em bloco."""
    conteudo = str(conteudo).upper()
    escala_pixel = escala * 1.18
    x, y = posicao
    cv2.putText(
        frame, conteudo, (x + 3, y + 3), cv2.FONT_HERSHEY_PLAIN,
        escala_pixel, VERDE_ESCURO, espessura + 2, cv2.LINE_8,
    )
    cv2.putText(
        frame, conteudo, (x, y), cv2.FONT_HERSHEY_PLAIN,
        escala_pixel, cor, espessura, cv2.LINE_8,
    )


def texto_centralizado(frame, conteudo, y, escala=0.7, cor=BRANCO, espessura=2, limite=LARGURA):
    conteudo = str(conteudo).upper()
    tamanho, _ = cv2.getTextSize(conteudo, cv2.FONT_HERSHEY_PLAIN, escala * 1.18, espessura)
    texto(frame, conteudo, ((limite - tamanho[0]) // 2, y), escala, cor, espessura)


def caixa(frame, inicio, fim, fundo=VERDE_ESCURO, borda=CINZA_CLARO, espessura=2):
    cv2.rectangle(frame, inicio, fim, fundo, -1)
    cv2.rectangle(frame, inicio, fim, borda, espessura, cv2.LINE_8)
    # Cantos quadrados duplos reforçam linguagem visual de jogo 8-bit.
    x1, y1 = inicio
    x2, y2 = fim
    for x, y in ((x1, y1), (x2 - 8, y1), (x1, y2 - 8), (x2 - 8, y2 - 8)):
        cv2.rectangle(frame, (x, y), (x + 8, y + 8), borda, -1)


def painel(frame, estado, gesto, confianca, placar, rodada, animacoes, agora):
    cv2.rectangle(frame, (790, 0), (LARGURA, ALTURA), VERDE, -1)
    cv2.rectangle(frame, (0, 0), (LARGURA, 62), VERDE, -1)
    cv2.line(frame, (0, 61), (LARGURA, 61), CINZA_CLARO, 3, cv2.LINE_8)
    texto_centralizado(
        frame, "PEDRA  PAPEL  TESOURA  LAGARTO  SPOCK",
        42, 1.12, BRANCO, 2,
    )

    caixa(frame, (18, 78), (430, 151), VERDE_ESCURO, BRANCO, 2)
    texto(frame, f"GESTO: {gesto}", (35, 108), 0.92, BRANCO, 2)
    texto(frame, f"CONFIANCA: {confianca:.0%}", (35, 137), 0.70, CINZA_CLARO, 2)

    caixa(frame, (804, 82), (1105, 202), VERDE_ESCURO, CINZA_CLARO, 2)
    texto_centralizado(frame[:, 790:], "PLACAR", 113, 0.92, BRANCO, 2, 330)
    texto(frame, f"VOCE: {placar['VITORIA']}", (825, 143), 0.68)
    texto(frame, f"CPU: {placar['DERROTA']}", (825, 168), 0.68)
    texto(frame, f"EMPATES: {placar['EMPATE']}", (825, 193), 0.68)

    texto(frame, "GESTOS", (815, 253), 0.78, BRANCO)
    legenda = [
        "PEDRA = punho fechado", "PAPEL = mao aberta", "TESOURA = dois dedos",
        "LAGARTO = mao em C", "SPOCK = saudacao vulcana",
    ]
    for i, linha in enumerate(legenda):
        texto(frame, linha, (815, 286 + i * 31), 0.48, CINZA_CLARO, 1)

    texto(frame, "Q: SAIR  R: REINICIAR", (815, 690), 0.48, CINZA_CLARO, 1)
    if estado == "CONTAGEM":
        numero = max(1, 3 - int(rodada["decorrido"]))
        texto_centralizado(frame, str(numero), 390, 4.0, BRANCO, 8, 790)
        texto_centralizado(frame, "PREPARE SEU GESTO", 455, 0.95, limite=790)
    elif estado == "CAPTURA":
        texto_centralizado(frame, "JA! MANTENHA O GESTO", 405, 1.10, VERDE_CLARO, 3, 790)
        progresso = min(1.0, rodada.get("estavel", 0.0) / TEMPO_ESTAVEL)
        cv2.rectangle(frame, (245, 435), (645, 455), CINZA_CLARO, -1)
        cv2.rectangle(frame, (245, 435), (245 + int(400 * progresso), 455), VERDE, -1)
    elif estado == "RESULTADO":
        cores = {"VITORIA": VERDE_CLARO, "DERROTA": CINZA_CLARO, "EMPATE": BRANCO}
        rotulos = {"VITORIA": "VOCE VENCEU!", "DERROTA": "COMPUTADOR VENCEU", "EMPATE": "EMPATE"}
        texto_centralizado(frame, rotulos[rodada["resultado"]], 330, 1.35, cores[rodada["resultado"]], 3, 790)
        texto_centralizado(frame, f"VOCE: {rodada['jogador']}", 380, 0.92, limite=790)
        texto_centralizado(frame, f"CPU: {rodada['computador']}", 418, 0.92, limite=790)
        texto_centralizado(frame, rodada["acao"], 462, 0.72, CINZA_CLARO, 2, 790)
        gesto_animado = (
            rodada["computador"]
            if rodada["resultado"] == "DERROTA"
            else rodada["jogador"]
        )
        if gesto_animado in animacoes:
            desenhar_gif(
                frame,
                animacoes[gesto_animado],
                agora - rodada["inicio_resultado"],
            )
    else:
        texto_centralizado(frame, "MOSTRE UM GESTO PARA COMECAR", 405, 0.94, BRANCO, 2, 790)


def executar() -> None:
    if not hasattr(mp, "solutions"):
        versao = getattr(mp, "__version__", "desconhecida")
        raise RuntimeError(
            f"MediaPipe {versao} não oferece mp.solutions. "
            "Instale as versões testadas com: "
            "python -m pip install --force-reinstall -r requirements.txt"
        )

    preparar_recursos_mediapipe()
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not camera.isOpened():
        raise RuntimeError("Não foi possível abrir a webcam. Verifique permissões e uso por outro aplicativo.")

    mp_hands = mp.solutions.hands
    desenho = mp.solutions.drawing_utils
    estilos = mp.solutions.drawing_styles
    estado, inicio_estado = "ESPERA", time.monotonic()
    candidato, inicio_estavel = None, None
    placar = {"VITORIA": 0, "DERROTA": 0, "EMPATE": 0}
    rodada: dict[str, object] = {}
    animacoes = carregar_gifs()
    nome_janela = "Pedra, Papel, Tesoura, Lagarto e Spock"
    cv2.namedWindow(nome_janela, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(nome_janela, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    with mp_hands.Hands(
        static_image_mode=False, max_num_hands=1, model_complexity=1,
        min_detection_confidence=0.65, min_tracking_confidence=0.65,
    ) as hands:
        try:
            while True:
                ok, imagem = camera.read()
                if not ok:
                    raise RuntimeError("A webcam parou de fornecer imagens.")
                imagem = cv2.flip(imagem, 1)
                imagem = cv2.resize(imagem, (790, ALTURA))
                resultado_mp = hands.process(cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB))
                gesto, confianca = "DESCONHECIDO", 0.0
                if resultado_mp.multi_hand_landmarks:
                    mao = resultado_mp.multi_hand_landmarks[0]
                    leitura = reconhecer_com_confianca(mao)
                    gesto, confianca = leitura.gesto, leitura.confianca
                    desenho.draw_landmarks(
                        imagem, mao, mp_hands.HAND_CONNECTIONS,
                        estilos.get_default_hand_landmarks_style(),
                        estilos.get_default_hand_connections_style(),
                    )

                agora = time.monotonic()
                if estado == "ESPERA" and gesto != "DESCONHECIDO":
                    estado, inicio_estado = "CONTAGEM", agora
                    rodada["decorrido"] = 0.0
                elif estado == "CONTAGEM":
                    rodada["decorrido"] = agora - inicio_estado
                    if agora - inicio_estado >= TEMPO_CONTAGEM:
                        estado, candidato, inicio_estavel = "CAPTURA", None, None
                elif estado == "CAPTURA":
                    if gesto == "DESCONHECIDO":
                        candidato, inicio_estavel = None, None
                    elif gesto != candidato:
                        candidato, inicio_estavel = gesto, agora
                    else:
                        rodada["estavel"] = agora - inicio_estavel
                        if rodada["estavel"] >= TEMPO_ESTAVEL:
                            computador = jogada_computador()
                            resultado, acao = comparar(gesto, computador)
                            placar[resultado] += 1
                            rodada.update(
                                jogador=gesto,
                                computador=computador,
                                resultado=resultado,
                                acao=acao,
                                inicio_resultado=agora,
                            )
                            estado, inicio_estado = "RESULTADO", agora
                elif estado == "RESULTADO" and agora - inicio_estado >= TEMPO_RESULTADO:
                    estado, inicio_estado, candidato, inicio_estavel = "ESPERA", agora, None, None
                    rodada = {}

                tela = cv2.copyMakeBorder(imagem, 0, 0, 0, LARGURA - 790, cv2.BORDER_CONSTANT, value=VERDE)
                painel(tela, estado, gesto, confianca, placar, rodada, animacoes, agora)
                # Linhas discretas simulam monitor arcade sem esconder a webcam.
                tela[::4, :790] = (tela[::4, :790] * 0.88).astype(tela.dtype)
                cv2.imshow(nome_janela, tela)
                tecla = cv2.waitKey(1) & 0xFF
                if tecla in (ord("q"), 27):
                    break
                if tecla == ord("r"):
                    placar = {"VITORIA": 0, "DERROTA": 0, "EMPATE": 0}
                    estado, inicio_estado = "ESPERA", agora
                    rodada = {}
        finally:
            camera.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    executar()
