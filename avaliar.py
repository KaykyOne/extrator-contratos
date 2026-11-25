"""Avalia o baseline e os três prompts sobre os mesmos contratos anotados."""
import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from statistics import mean
from time import perf_counter

from src.baseline import carregar_ner, extrair_baseline
from src.llm_extractor import ErroExtracao, configurar_ambiente, consultar, modelo_configurado
from src.prompts import ESTRATEGIAS
from src.schema import Contrato

RAIZ = Path(__file__).resolve().parent
CAMPOS = tuple(Contrato.model_fields)
COLUNAS = (
    "estrategia", "origem", "avaliados", "total", "acuracia_geral",
    *CAMPOS, "tempo_medio_ms", "taxa_json_invalido", "taxa_esquema_invalido",
)


def normalizar(valor: object) -> object:
    """Compara números como decimais e ignora caixa, acentos e pontuação."""
    if isinstance(valor, str):
        decomposto = unicodedata.normalize("NFKD", valor.casefold())
        sem_acentos = "".join(char for char in decomposto if not unicodedata.combining(char))
        return " ".join(re.findall(r"[^\W_]+", sem_acentos))
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    return valor


@dataclass
class Medicoes:
    acertos: Counter = field(default_factory=Counter)
    falhas: Counter = field(default_factory=Counter)
    erros: list[str] = field(default_factory=list)
    tempos_ms: list[float] = field(default_factory=list)
    respostas: int = 0
    json_invalidos: int = 0
    esquemas_invalidos: int = 0
    avaliados: int = 0

    def comparar(self, item: dict, gold: dict, previsto: dict, tempo_ms: float) -> None:
        """Registra acertos por campo e agrupa diferenças por contrato."""
        self.avaliados += 1
        self.tempos_ms.append(tempo_ms)
        diferencas = []
        for campo, esperado in gold.items():
            obtido = previsto[campo]
            if normalizar(esperado) == normalizar(obtido):
                self.acertos[campo] += 1
            else:
                diferencas.append(
                    f"- `{campo}` · esperado {formatar_json(esperado)} · extraído {formatar_json(obtido)}"
                )
        if diferencas and len(self.erros) < 3:
            trecho = "".join([f"> {linha}\n" for linha in item["texto"].splitlines()]).rstrip()
            titulo = f"### {item['id']} ({item['estilo']})"
            self.erros.append("\n\n".join([titulo, trecho, "\n".join(diferencas)]))

    def contar_respostas(self, resultado) -> None:
        self.respostas += resultado.respostas
        self.json_invalidos += resultado.json_invalidos
        self.esquemas_invalidos += resultado.esquemas_invalidos

    def resumir(self, estrategia: str, origem: str, total: int) -> dict:
        return {
            "estrategia": estrategia,
            "origem": origem,
            "avaliados": self.avaliados,
            "total": total,
            "acuracia_geral": proporcao(self.acertos.total(), self.avaliados * len(CAMPOS)),
            **{campo: proporcao(self.acertos[campo], self.avaliados) for campo in CAMPOS},
            "tempo_medio_ms": round(mean(self.tempos_ms), 2) if self.tempos_ms else None,
            "taxa_json_invalido": proporcao(self.json_invalidos, self.respostas),
            "taxa_esquema_invalido": proporcao(self.esquemas_invalidos, self.respostas),
        }


def proporcao(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def formatar_json(valor: object) -> str:
    return f"`{json.dumps(valor, ensure_ascii=False)}`"


def mostrar_progresso(mensagem: str) -> None:
    """Mostra o andamento imediatamente e deixa a tabela na saída padrão."""
    print(mensagem, file=sys.stderr, flush=True)


def avaliar_estrategia(dataset: list[dict], estrategia: str, offline: bool,
                       progresso: Callable[[str, int], None] | None = None) -> Medicoes:
    medicoes = Medicoes()
    total = len(dataset)
    for numero, item in enumerate(dataset, start=1):
        etapa = f"[{estrategia}] {numero}/{total} ({item['id']})"
        if estrategia != "baseline" and not offline:
            mostrar_progresso(f"{etapa} consultando a API DeepSeek…")
        gold = Contrato.model_validate_json(json.dumps(item["gold"])).model_dump(mode="json")
        inicio = perf_counter()
        try:
            if estrategia == "baseline":
                previsto = extrair_baseline(item["texto"])
            else:
                saida = consultar(item["texto"], estrategia, offline)
                previsto = saida.registro.contrato
                medicoes.contar_respostas(saida.registro)
        except ErroExtracao as erro:
            medicoes.contar_respostas(erro)
            medicoes.falhas[str(erro)] += 1
            if not offline:
                mostrar_progresso(f"{etapa} · {erro}")
        else:
            tempo_ms = (perf_counter() - inicio) * 1000
            medicoes.comparar(item, gold, previsto.model_dump(mode="json"), tempo_ms)
        if progresso:
            progresso(estrategia, numero)
    mostrar_progresso(f"[{estrategia}] {medicoes.avaliados}/{total} contratos com saída validada.")
    return medicoes


def tabela_markdown(linhas: list[dict], colunas: tuple[str, ...]) -> str:
    tabela = ["| " + " | ".join(colunas) + " |", "| " + " | ".join(["---"] * len(colunas)) + " |"]
    for linha in linhas:
        valores = []
        for coluna in colunas:
            valor = linha[coluna]
            if valor is None:
                valores.append("—")
            elif isinstance(valor, float) and coluna != "tempo_medio_ms":
                valores.append(f"{valor:.2%}")
            else:
                valores.append(str(valor))
        tabela.append("| " + " | ".join(valores) + " |")
    return "\n".join(tabela)


def salvar_relatorios(linhas: list[dict], erros: list[str], modo: str) -> None:
    destino = RAIZ / "resultados"
    destino.mkdir(exist_ok=True)
    with (destino / "metricas.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(linhas)

    resumo = COLUNAS[:5] + COLUNAS[-3:]
    por_campo = ("estrategia", *CAMPOS)
    documento = "\n\n".join([
        "# Métricas de extração",
        modo,
        tabela_markdown(linhas, resumo),
        "## Acurácia por campo",
        tabela_markdown(linhas, por_campo),
        "A acurácia considera saídas validadas, inclusive campos nulos corretos. "
        "A geral é a proporção de acertos sobre todos os campos avaliados. "
        "A cobertura aparece em avaliados/total. O tempo mede cada extração concluída, "
        "incluindo a repetição quando houver. O modelo spaCy é carregado antes do cronômetro. "
        "As taxas usam todas as respostas da API observadas como denominador, inclusive "
        "as tentativas rejeitadas. No modo cache, o tempo é de leitura e as taxas "
        "são históricas para os registros recuperados. — indica métrica indisponível.",
    ])
    (destino / "metricas.md").write_text(documento + "\n", encoding="utf-8")
    (destino / "erros.md").write_text("\n\n".join(["# Exemplos de erro", *erros]) + "\n", encoding="utf-8")
    print(documento)


def executar_avaliacao(usar_cache: bool = False,
                       progresso: Callable[[str, int], None] | None = None) -> None:
    """Executa a mesma avaliação pelo terminal ou pela interface Flask."""
    configurar_ambiente()
    tem_chave = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    offline = usar_cache or not tem_chave
    modelo = modelo_configurado()
    modo = f"Modelo configurado: `{modelo}`. "
    if usar_cache:
        modo += "Modo offline solicitado."
    elif not tem_chave:
        modo += "DEEPSEEK_API_KEY ausente. Modo offline automático para o LLM."
    else:
        modo += "Chamadas novas à API para cada estratégia de LLM."

    dataset = json.loads((RAIZ / "data" / "dataset.json").read_text(encoding="utf-8"))
    mostrar_progresso(modo.replace("`", ""))
    mostrar_progresso(f"{len(dataset)} contratos por estratégia. Carregando o modelo spaCy…")
    carregar_ner()
    linhas = []
    erros = []
    for estrategia in ("baseline", *ESTRATEGIAS):
        origem = "local" if estrategia == "baseline" else "cache" if offline else "API"
        medicoes = avaliar_estrategia(dataset, estrategia, offline, progresso)
        if not medicoes.avaliados:
            origem = "indisponível"
        linhas.append(medicoes.resumir(estrategia, origem, len(dataset)))
        erros.append(f"## {estrategia}")
        if medicoes.falhas:
            erros.extend(f"- {total} ocorrência(s) · {mensagem}" for mensagem, total in medicoes.falhas.items())
        erros.extend(medicoes.erros)
        if medicoes.avaliados and not medicoes.erros:
            erros.append("Nenhuma divergência nas saídas validadas.")
    salvar_relatorios(linhas, erros, modo)
    mostrar_progresso("Relatórios gravados em resultados/.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Usa o cache de respostas reais.")
    argumentos = parser.parse_args()
    executar_avaliacao(usar_cache=argumentos.offline)


if __name__ == "__main__":
    main()
