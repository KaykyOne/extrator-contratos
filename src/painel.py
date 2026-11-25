"""Adapta os relatórios da avaliação para gráficos e exemplos na interface."""
import csv
import re
from datetime import datetime
from pathlib import Path

CAMPOS = {
    "locador": "Locador", "locatario": "Locatário", "endereco_imovel": "Endereço",
    "valor_aluguel": "Aluguel", "prazo_meses": "Prazo", "data_inicio": "Início",
    "valor_multa_rescisoria": "Multa rescisória", "indice_reajuste": "Índice de reajuste",
}


def percentual(valor: float | None) -> str:
    if valor is None:
        return "—"
    texto = f"{valor * 100:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",") + "%"


def duracao(ms: float | None) -> str:
    if ms is None:
        return "—"
    valor, unidade = (ms / 1000, "s") if ms >= 1000 else (ms, "ms")
    return f"{valor:.2f} {unidade}".replace(".", ",")


def valor_legivel(valor: object, campo: str) -> str:
    """Formata os cartões sem alterar os tipos e valores do JSON."""
    if campo in ("valor_aluguel", "valor_multa_rescisoria"):
        reais = f"{valor:,.2f}".translate(str.maketrans(",.", ".,"))
        return f"R$ {reais}"
    if campo == "prazo_meses":
        return f"{valor} {'mês' if valor == 1 else 'meses'}"
    if campo == "data_inicio":
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y")
    return str(valor)


def ler_metricas(pasta: Path) -> tuple[list[dict], str | None]:
    """Lê o CSV atual a cada visita, inclusive avaliações feitas pelo CLI."""
    try:
        with (pasta / "metricas.csv").open(encoding="utf-8", newline="") as arquivo:
            linhas = list(csv.DictReader(arquivo))
            atualizado = datetime.fromtimestamp((pasta / "metricas.csv").stat().st_mtime)
    except FileNotFoundError:
        return [], None

    for linha in linhas:
        for campo in ("acuracia_geral", "tempo_medio_ms", "taxa_json_invalido", *CAMPOS):
            linha[campo] = float(linha[campo]) if linha.get(campo) else None
    return linhas, atualizado.strftime("%d/%m/%Y às %H:%M")


def ler_exemplos(pasta: Path) -> tuple[list[dict], list[dict]]:
    """Lê a estrutura que o avaliador grava em erros.md, inclusive relatórios anteriores."""
    try:
        texto = (pasta / "erros.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], []

    exemplos = []
    falhas = []
    blocos = re.split(r"^## (.+)\n", texto, flags=re.M)
    for estrategia, bloco in zip(blocos[1::2], blocos[2::2], strict=True):
        for falha in re.findall(r"^- (\d+ ocorrência\(s\) · .+)$", bloco, re.M):
            falhas.append({"estrategia": estrategia, "texto": falha})
        contratos = re.split(r"^### (.+)\n", bloco, flags=re.M)
        for titulo, corpo in zip(contratos[1::2], contratos[2::2], strict=True):
            trecho = "\n".join(re.findall(r"^> ?(.*)$", corpo, re.M))
            diferencas = [
                {"campo": CAMPOS.get(campo, campo), "esperado": esperado, "extraido": extraido}
                for campo, esperado, extraido in re.findall(
                    r"^- `([^\n]+?)` · esperado `([^\n]*?)` · extraído `([^\n]*?)`$", corpo, re.M
                )
            ]
            exemplos.append({"estrategia": estrategia, "titulo": titulo, "id": titulo.split()[0],
                             "trecho": trecho, "diferencas": diferencas})
    return exemplos, falhas
