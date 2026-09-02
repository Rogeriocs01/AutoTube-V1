from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class ResultadoPublicacao:
    sucesso: bool

    video_id: Optional[str] = None
    youtube_id: Optional[str] = None

    playlist_ok: Optional[bool] = None
    thumbnail_ok: Optional[bool] = None
    drive_ok: Optional[bool] = None

    mensagem: str = ""
    etapa: Optional[str] = None

    def __bool__(self):
        return self.sucesso

    def para_dict(self):
        return asdict(self)

    @classmethod
    def sucesso_publicacao(
        cls,
        video_id,
        youtube_id,
        playlist_ok,
        thumbnail_ok,
        drive_ok,
        mensagem="Publicação concluída",
    ):
        return cls(
            sucesso=True,
            video_id=video_id,
            youtube_id=youtube_id,
            playlist_ok=playlist_ok,
            thumbnail_ok=thumbnail_ok,
            drive_ok=drive_ok,
            mensagem=mensagem,
            etapa="concluido",
        )

    @classmethod
    def falha(
        cls,
        mensagem,
        video_id=None,
        youtube_id=None,
        etapa=None,
        playlist_ok=None,
        thumbnail_ok=None,
        drive_ok=None,
    ):
        return cls(
            sucesso=False,
            video_id=video_id,
            youtube_id=youtube_id,
            playlist_ok=playlist_ok,
            thumbnail_ok=thumbnail_ok,
            drive_ok=drive_ok,
            mensagem=mensagem,
            etapa=etapa,
        )