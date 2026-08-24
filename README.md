# Pedra, Papel, Tesoura, Lagarto e Spock com visão computacional

Jogo local para demonstrações didáticas. OpenCV captura a webcam, MediaPipe encontra 21 pontos da mão e regras geométricas classificam cinco gestos. Nenhuma imagem é enviada para a internet.

## Requisitos

- Windows 10 ou 11, webcam e Python 3.10, 3.11 ou 3.12 de 64 bits.
- Ambiente iluminado, mão inteira visível e fundo com algum contraste.

As versões em `requirements.txt` são fixas e testadas entre si. MediaPipe 1.x não expõe a API legada `mp.solutions` usada por este projeto. Use Python 3.10, 3.11 ou 3.12 de 64 bits; Python 3.11 é a opção recomendada.

## Instalação no Windows

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Se outro MediaPipe já estiver instalado ou surgir `module 'mediapipe' has no attribute 'solutions'`, corrija o ambiente:

```powershell
python -m pip install --force-reinstall -r requirements.txt
python -c "import mediapipe as mp; print(mp.__version__, hasattr(mp, 'solutions'))"
```

O resultado esperado é `0.10.21 True`.

## Instalação no macOS

Recomenda-se usar o Python 3.11. Primeiro, clone o repositório e instale as dependências em um ambiente virtual:

```bash
git clone https://github.com/juliavelosodias/rock-scissors-paper-lizard-spock.git
cd rock-scissors-paper-lizard-spock
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Antes de executar, altere esta linha em `main.py`:

```python
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
```

para usar o backend de câmera do macOS:

```python
camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
```

Execute o jogo:

```bash
python main.py
```

Na primeira execução, autorize o Terminal a acessar a câmera em **Ajustes do Sistema → Privacidade e Segurança → Câmera**. Se a câmera não abrir, experimente trocar o índice `0` por `1` ou `2`. Pressione `Q` ou `Esc` para sair e `R` para zerar o placar.

### Projeto em pasta com acentos

MediaPipe 0.10 pode falhar ao carregar modelos nativos quando o ambiente virtual está em caminho com caracteres como `Área`. `main.py` detecta esse caso e copia somente os módulos de mão necessários para `%TEMP%\rpsls_mediapipe`, caminho ASCII usado como cache. O processamento e os modelos continuam locais; nenhuma imagem é enviada pela rede.

Se houver várias câmeras, altere `cv2.VideoCapture(0, cv2.CAP_DSHOW)` em `main.py`: tente índice `1` ou `2`. A interface abre em tela cheia com estilo arcade. Pressione `Q` ou `Esc` para sair e `R` para zerar o placar.

Em todo resultado, o GIF correspondente aparece no canto inferior esquerdo: gesto do jogador quando ele vence, gesto da CPU quando ela vence e gesto compartilhado no empate. Os arquivos ficam em `scr/`: `pedra.gif`, `paper.gif`, `scissors.gif`, `lizard.gif` e `spock.gif`. Pillow preserva animação, transparência e duração original dos quadros.

## Fluxo

```text
WEBCAM
   ↓
MEDIAPIPE
   ↓
21 PONTOS DA MÃO
   ↓
ANÁLISE DOS DEDOS
   ↓
CLASSIFICAÇÃO DO GESTO
   ↓
PEDRA / PAPEL / TESOURA / LAGARTO / SPOCK
   ↓
REGRAS DO JOGO
   ↓
RESULTADO
```

Detectar a mão significa localizar uma região que parece uma mão. Identificar landmarks significa estimar nela 21 pontos, como pulso e articulações. Extrair características transforma pontos em medidas úteis: ângulos, dedos estendidos e distâncias. Classificar compara essas medidas com os padrões dos cinco gestos. Este projeto usa regras explicáveis, não treina outra rede neural; a IA pré-treinada do MediaPipe fornece os landmarks.

## Como cada gesto é reconhecido

Todas as distâncias são divididas pelo tamanho da palma, calculado pela média entre a largura `5-17` e o segmento `0-9`. Assim, aproximar a mão da câmera muda os pixels, mas pouco altera as proporções.

- **Pedra:** indicador, médio, anelar e mínimo dobrados; polegar próximo da mão.
- **Papel:** quatro dedos e polegar estendidos, sem o vão central característico de Spock.
- **Tesoura:** indicador e médio estendidos e separados; anelar e mínimo dobrados.
- **Spock:** quatro dedos estendidos; pontas `8-12` e `16-20` próximas; vão central maior que a média dos vãos dos pares. A comparação usa pontas e articulações para tolerar perspectiva.
- **Lagarto:** exige simultaneamente indicador curvo, polegar curvo, abertura moderada entre pontas `4-8`, projeção dos dois dedos para fora da palma e outros três dedos não totalmente retos.

### Por que o Lagarto não é “qualquer mão meio fechada”

`detectar_lagarto()` combina cinco testes. O ângulo do indicador deve indicar curvatura; o polegar precisa estar curvo ou projetado; a abertura normalizada `4-8` deve ficar entre `0.32` e `1.02`; ambos precisam formar a boca do C; médio, anelar e mínimo não podem parecer uma mão aberta. Abertura e curvatura do indicador são obrigatórias. Outros sinais usam pontuação combinada para tolerar anatomia e rotação diferentes.

### Por que Papel não vira Spock

`detectar_spock()` exige dois pares próximos e um vão central grande. Papel exige cinco dedos abertos e rejeita vão central excessivo. Tesoura exige anelar e mínimo dobrados, portanto não atende Spock.

## Estabilidade e confiança

Uma pose só é aceita com confiança mínima `0.68` e vantagem de `0.10` sobre a segunda hipótese. Ao aparecer um gesto conhecido, a tela conta 3, 2, 1. Depois de “JÁ!”, o mesmo gesto deve ficar estável por 1 segundo. O resultado aparece por 3 segundos.

## Calibração para outra câmera ou pessoa

Edite os limites em `gesture_recognition.py` aos poucos, em passos de `0.03` para distâncias ou `5°` para ângulos:

- Lagarto confundido com Pedra: aumente o mínimo `0.32` de `abertura_c` ou o mínimo `0.42` da projeção do indicador.
- Lagarto difícil: reduza `0.32` ou amplie a faixa angular `72.0, 145.0`.
- Papel vira Spock: reduza o máximo `0.38` dos pares ou aumente o vão `0.43`.
- Spock vira Papel: reduza aos poucos o limite da razão `1.12`, mantendo a mão de frente para a câmera.
- Muitos falsos positivos: aumente `limite=0.68` em `reconhecer_com_confianca`.

Valores são heurísticos e dependem da anatomia, rotação da mão e lente. Para uma apresentação, teste com os participantes, marque o chão e mantenha luz frontal. Se precisar de precisão para muitas pessoas, grave exemplos rotulados e substitua as regras por um classificador treinado sobre as mesmas características normalizadas.

## Estrutura

```text
.
├── main.py                 # webcam, estados, contagem e interface
├── gesture_recognition.py  # geometria e classificação
├── game_logic.py           # regras e sorteio
├── test_game_logic.py      # testes das 25 combinações
├── requirements.txt
└── README.md
```

Rode os testes sem webcam:

```powershell
python -m unittest -v
```

## Referências open source

- [MediaPipe Hand Landmarker para Python](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python): documentação oficial sobre detecção, modos de vídeo e landmarks.
- [Exemplo oficial Hand Landmarker](https://github.com/googlesamples/mediapipe/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb): exemplo Apache-2.0 de inferência e visualização.
- [MediaPipe Hands](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md): índices dos 21 landmarks, coordenadas normalizadas e desenho das conexões.
- [hand-gesture-recognition-mediapipe](https://github.com/kinivi/hand-gesture-recognition-mediapipe): projeto Apache-2.0 de referência para normalização de pontos e classificação de gestos.

O código deste repositório foi escrito para este projeto. As referências orientaram uso da API, desenho e estratégia de normalização; nenhum classificador ou modelo delas foi copiado.
