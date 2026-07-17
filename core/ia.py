import base64
from pathlib import Path

import cv2
from openai import OpenAI
from pydantic import BaseModel


MODELO_IA = "gpt-5.6"
QUANTIDADE_FRAMES = 5


class MetadadosGerados(BaseModel):
    titulo: str
    descricao: str


def extrair_frames_base64(
    caminho_video: Path,
    quantidade: int = QUANTIDADE_FRAMES,
) -> list[str]:
    captura = cv2.VideoCapture(str(caminho_video))

    if not captura.isOpened():
        raise RuntimeError("Não foi possível abrir o vídeo.")

    total_frames = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames <= 0:
        captura.release()
        raise RuntimeError("Não foi possível identificar os frames do vídeo.")

    # Evita exatamente o primeiro e o último frame.
    posicoes = [
        int(total_frames * percentual)
        for percentual in (0.10, 0.30, 0.50, 0.70, 0.90)
    ][:quantidade]

    imagens_base64 = []

    try:
        for posicao in posicoes:
            captura.set(cv2.CAP_PROP_POS_FRAMES, posicao)

            sucesso, frame = captura.read()

            if not sucesso:
                continue

            sucesso, imagem_codificada = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 80],
            )

            if not sucesso:
                continue

            imagens_base64.append(
                base64.b64encode(
                    imagem_codificada.tobytes()
                ).decode("utf-8")
            )

    finally:
        captura.release()

    if not imagens_base64:
        raise RuntimeError(
            "Não foi possível extrair imagens válidas do vídeo."
        )

    return imagens_base64


def gerar_metadados_com_ia(caminho_video: Path):
    if not caminho_video.exists():
        print(f"\nVídeo não encontrado: {caminho_video}")
        return None

    try:
        print("\nExtraindo quadros do vídeo...")

        imagens = extrair_frames_base64(caminho_video)

        conteudo = [
            {
                "type": "input_text",
                "text": (
                    "Analise os quadros deste vídeo curto de tecnologia. "
                    "Crie um título chamativo e claro para YouTube Shorts, "
                    "sem inventar detalhes que não aparecem nas imagens. "
                    "O título deve ter no máximo 90 caracteres. "
                    "Crie também uma descrição curta em português do Brasil, "
                    "com uma chamada para interação e as hashtags "
                    "#tecnologia e #shorts. "
                    "Não mencione que analisou quadros ou imagens."
                ),
            }
        ]

        for imagem in imagens:
            conteudo.append(
                {
                    "type": "input_image",
                    "image_url": (
                        f"data:image/jpeg;base64,{imagem}"
                    ),
                    "detail": "low",
                }
            )

        print("Solicitando título e descrição à IA...")

        cliente = OpenAI()

        resposta = cliente.responses.parse(
            model=MODELO_IA,
            input=[
                {
                    "role": "user",
                    "content": conteudo,
                }
            ],
            text_format=MetadadosGerados,
        )

        resultado = resposta.output_parsed

        if resultado is None:
            print("A IA não retornou metadados válidos.")
            return None

        return {
            "titulo": resultado.titulo.strip(),
            "descricao": resultado.descricao.strip(),
        }

    except Exception as erro:
        print(f"\nErro durante a análise com IA: {erro}")
        return None