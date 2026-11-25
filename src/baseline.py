"""Baseline com NER para candidatos a nomes e regex para padrões explícitos."""
import re
from datetime import date
from functools import lru_cache
from math import isfinite

import spacy
from spacy.language import Language
from spacy.tokens import Doc

from .schema import Contrato

LOCADOR = r"\b(?:locadora?|proprietári[oa])\b"
LOCATARIO = r"\b(?:locatári[oa]|inquilin[oa])\b"
SEPARADOR = r"\s*(?:[:=–—-]\s*)?"
MOEDA = r"(\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d+(?:,\d{2})?)(?!\d|[,.]\d)"
ENDERECO = re.compile(
    r"\b(?:imóvel(?:\s+situado\s+(?:na|no|em))?|endereço(?:\s+do\s+imóvel)?)"
    + SEPARADOR
    + r"((?:Rua|Avenida|Av\.|Travessa|Alameda|Praça|Estrada)\s+[^;\n.!?]+)",
    re.IGNORECASE,
)
ALUGUEL = re.compile(r"\baluguel(?:\s+mensal)?\s*(?:(?:de|é(?: de)?|será de)\b\s*|[:=]\s*)?R\$\s*" + MOEDA, re.I)
MULTA = re.compile(
    r"\bmulta\s+(?:rescisória|por\s+rescisão(?:\s+antecipada)?)"
    r"\s*(?:de\s+|[:=]\s*)?R\$\s*" + MOEDA, re.I,
)
PRAZO = re.compile(r"\b(?:prazo\s*(?:de\s+|[:=]\s*)?|por\s+)(\d{1,6})\s*(meses|mês|anos?)\b", re.I)
INICIO = re.compile(
    r"\b(?:início(?:\s+da\s+vigência)?|vigência|começa)"
    r"\s*(?:(?:em|a partir de)\s+|[:=]\s*)?"
    r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b", re.I,
)
INDICE = re.compile(
    r"\breajust(?:e|ado)(?:\s+anual)?\s*(?:(?:pelo|por)\s+|[:=]\s*)?"
    r"(IPCA|IGP[- ]?M|INPC|IPC[- ]?FIPE)\b", re.I,
)
PALAVRA_NOME = r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+"
NOME_ROTULADO = re.compile(
    rf"({PALAVRA_NOME}(?:[ \t]+(?:(?:da|das|de|do|dos)[ \t]+)?{PALAVRA_NOME})*)"
)


@lru_cache(maxsize=1)
def carregar_ner() -> Language:
    """Carrega o modelo português uma vez e mantém só o pipeline do NER."""
    try:
        return spacy.load("pt_core_news_sm", enable=["tok2vec", "ner"])
    except OSError as erro:
        raise RuntimeError("Instale o modelo com: python -m spacy download pt_core_news_sm") from erro


def nome_associado(doc: Doc, papel: str) -> str | None:
    """Usa entidades PER próximas a um papel e regex para rótulos explícitos."""
    for rotulo in re.finditer(papel + SEPARADOR, doc.text, re.I):
        # O rótulo explícito permite completar nomes que o NER segmenta.
        rotulado = None
        if re.search(r"[:=–—-]", rotulo.group()):
            rotulado = NOME_ROTULADO.match(doc.text, rotulo.end())
        for entidade in doc.ents:
            if entidade.label_ != "PER":
                continue
            if entidade.start_char == rotulo.end():
                if rotulado and rotulado.end() > entidade.end_char:
                    return rotulado[1]
                return entidade.text
            if entidade.end_char <= rotulo.start():
                trecho = doc.text[entidade.end_char:rotulo.start()]
                if re.fullmatch(r"[, ]+(?:doravante\s+)?", trecho, re.I):
                    return entidade.text

        if rotulado:
            return rotulado[1]
    return None


def valor_em_reais(regra: re.Pattern, texto: str) -> float | None:
    achado = regra.search(texto)
    if achado:
        valor = float(achado[1].replace(".", "").replace(",", "."))
        if isfinite(valor):
            return valor
    return None


def data_inicial(texto: str) -> date | None:
    achado = INICIO.search(texto)
    if achado:
        partes = achado[1].split("/")
        iso = "-".join(reversed(partes)) if len(partes) == 3 else achado[1]
        try:
            return date.fromisoformat(iso)
        except ValueError:
            return None
    return None


def extrair_baseline(texto: str) -> Contrato:
    """Associa candidatos ao contexto da cláusula e deixa lacunas como null."""
    doc = carregar_ner()(texto)
    endereco = ENDERECO.search(texto)
    duracao = PRAZO.search(texto)
    indice = INDICE.search(texto)
    meses = None
    if duracao and int(duracao[1]) > 0:
        fator = 12 if duracao[2].lower().startswith("ano") else 1
        meses = int(duracao[1]) * fator
    return Contrato(
        locador=nome_associado(doc, LOCADOR),
        locatario=nome_associado(doc, LOCATARIO),
        endereco_imovel=endereco[1].strip(" ,") if endereco else None,
        valor_aluguel=valor_em_reais(ALUGUEL, texto),
        prazo_meses=meses,
        data_inicio=data_inicial(texto),
        valor_multa_rescisoria=valor_em_reais(MULTA, texto),
        indice_reajuste=indice[1].upper() if indice else None,
    )
