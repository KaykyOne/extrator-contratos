"""Cliente DeepSeek com JSON mode, validação e uma nova tentativa."""
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from .cache import RegistroCache, caminho_cache, ler_cache, salvar_cache
from .prompts import montar_mensagens
from .schema import Contrato

RAIZ = Path(__file__).resolve().parents[1]
MODELO_LEGADO = "deepseek-chat"
MODELO_PADRAO = "deepseek-v4-pro"


class ErroExtracao(Exception):
    """Falha que pode ser exibida no app e registrada na avaliação."""

    def __init__(self, mensagem: str, status: int, respostas: int = 0,
                 json_invalidos: int = 0, esquemas_invalidos: int = 0):
        super().__init__(mensagem)
        self.status = status
        self.respostas = respostas
        self.json_invalidos = json_invalidos
        self.esquemas_invalidos = esquemas_invalidos


@dataclass(frozen=True)
class SaidaLLM:
    registro: RegistroCache
    origem: str


def configurar_ambiente() -> None:
    """Variáveis do processo têm prioridade sobre o arquivo local."""
    load_dotenv(RAIZ / ".env")


def modelo_configurado() -> str:
    return os.getenv("DEEPSEEK_MODEL", "").strip() or MODELO_PADRAO


@lru_cache(maxsize=1)
def cliente_deepseek(chave: str) -> OpenAI:
    # Desativa tentativas automáticas do SDK para medir as chamadas do projeto.
    return OpenAI(api_key=chave, base_url="https://api.deepseek.com", timeout=30, max_retries=0)


def consultar(texto: str, estrategia: str, offline: bool = False) -> SaidaLLM:
    """Executa online ou reproduz uma resposta real anteriormente salva."""
    configurar_ambiente()
    modelo = modelo_configurado()
    # Formulários HTML podem enviar CRLF para o mesmo texto do dataset.
    texto_normalizado = texto.replace("\r\n", "\n").replace("\r", "\n")
    mensagens = montar_mensagens(texto_normalizado, estrategia)
    caminho = caminho_cache(modelo, mensagens)
    if offline:
        registro = ler_cache(caminho)
        if registro is None:
            raise ErroExtracao("Nenhuma resposta em cache para este texto e estratégia.", 404)
        return SaidaLLM(registro, "cache")

    chave = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not chave:
        raise ErroExtracao("Configure DEEPSEEK_API_KEY no .env ou use o modo offline.", 503)

    cliente = cliente_deepseek(chave)
    registro = obter_resposta(cliente, modelo, mensagens)
    try:
        salvar_cache(caminho, registro)
    except OSError as erro:
        # Uma falha de escrita não invalida a extração que já foi concluída.
        logging.getLogger(__name__).warning("Falha ao gravar o cache: %s", erro)
    return SaidaLLM(registro, "api")


def obter_resposta(cliente: OpenAI, modelo: str, mensagens: list[dict[str, str]]) -> RegistroCache:
    """Conta separadamente JSON malformado e objetos fora do esquema."""
    respostas = json_invalidos = esquemas_invalidos = 0
    # O modo sem raciocínio permite a amostragem com temperature=0 no V4-Pro.
    opcoes = {"extra_body": {"thinking": {"type": "disabled"}}} if modelo != MODELO_LEGADO else {}
    for _ in range(2):
        try:
            resposta = cliente.chat.completions.create(
                model=modelo, messages=mensagens,
                # Temperatura zero reduz a variação entre execuções comparáveis.
                temperature=0, response_format={"type": "json_object"}, max_tokens=600,
                **opcoes,
            )
        except (APITimeoutError, RateLimitError, APIConnectionError, APIStatusError) as erro:
            mensagem, status = descrever_erro(erro, modelo)
            raise ErroExtracao(mensagem, status, respostas, json_invalidos, esquemas_invalidos) from erro

        conteudo = resposta.choices[0].message.content if resposta.choices else ""
        respostas += 1
        try:
            contrato = Contrato.model_validate_json(conteudo or "")
        except ValidationError as erro:
            if any(item["type"] == "json_invalid" for item in erro.errors()):
                json_invalidos += 1
            else:
                esquemas_invalidos += 1
            mensagens = [*mensagens, {"role": "user", "content": (
                "Refaça a extração do contrato acima. Retorne um objeto JSON válido "
                "com as oito chaves, tipos corretos e null quando faltar informação."
            )}]
        else:
            return RegistroCache(contrato=contrato, respostas=respostas,
                                 json_invalidos=json_invalidos, esquemas_invalidos=esquemas_invalidos)

    raise ErroExtracao(
        "DeepSeek retornou JSON inválido ou fora do esquema nas duas tentativas.",
        502, respostas, json_invalidos, esquemas_invalidos,
    )


def descrever_erro(erro: Exception, modelo: str) -> tuple[str, int]:
    """Traduz os erros do SDK sem devolver detalhes sensíveis da chamada."""
    if isinstance(erro, APITimeoutError):
        return "A API do DeepSeek excedeu o tempo limite. Tente novamente.", 504
    if isinstance(erro, RateLimitError):
        return "A API do DeepSeek atingiu o limite de requisições. Aguarde e tente novamente.", 429
    if isinstance(erro, APIConnectionError):
        return "Não foi possível conectar à API do DeepSeek.", 502
    if erro.status_code in (401, 403):
        return "A API do DeepSeek recusou a autenticação. Verifique DEEPSEEK_API_KEY.", 503
    if erro.status_code == 402:
        return "A conta DeepSeek está sem saldo para a chamada.", 503
    if erro.status_code in (400, 404) and modelo == MODELO_LEGADO:
        return "O modelo deepseek-chat foi aposentado. Use DEEPSEEK_MODEL=deepseek-v4-pro.", 503
    return f"A API do DeepSeek retornou HTTP {erro.status_code}.", 502
