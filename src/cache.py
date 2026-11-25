"""Persistência local de respostas validadas, com um arquivo por consulta."""
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, Field, ValidationError

from .schema import Contrato

DIRETORIO_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "llm"


class RegistroCache(BaseModel):
    contrato: Contrato
    respostas: int = Field(ge=1, le=2)
    json_invalidos: int = Field(ge=0, le=1)
    esquemas_invalidos: int = Field(ge=0, le=1)


def caminho_cache(modelo: str, mensagens: list[dict[str, str]]) -> Path:
    """Mudanças no modelo, texto ou prompt geram uma nova chave."""
    chave = json.dumps([modelo, mensagens], ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(chave.encode("utf-8")).hexdigest()
    return DIRETORIO_CACHE / f"{digest}.json"


def ler_cache(caminho: Path) -> RegistroCache | None:
    """Trata um arquivo ausente ou corrompido como falta no cache."""
    try:
        return RegistroCache.model_validate_json(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError):
        return None


def salvar_cache(caminho: Path, registro: RegistroCache) -> None:
    """Uma troca atômica evita que leitores vejam um JSON parcialmente escrito."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=caminho.parent, delete=False, mode="w", encoding="utf-8") as arquivo:
        temporario = Path(arquivo.name)
        try:
            arquivo.write(registro.model_dump_json(indent=2) + "\n")
            arquivo.close()
            temporario.replace(caminho)
        finally:
            temporario.unlink(missing_ok=True)
