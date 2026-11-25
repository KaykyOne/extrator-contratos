"""Interface Flask para experimentar as extrações em contratos fictícios."""
import json
import os
from pathlib import Path
from threading import Lock, Thread
from time import perf_counter

from flask import Flask, jsonify, render_template, request

from avaliar import executar_avaliacao
from src.baseline import extrair_baseline
from src.llm_extractor import ErroExtracao, configurar_ambiente, consultar
from src.painel import CAMPOS, duracao, ler_exemplos, ler_metricas, percentual, valor_legivel
from src.prompts import ESTRATEGIAS
from src.schema import Contrato

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 384 * 1024
app.json.ensure_ascii = False
LIMITE_TEXTO = 25_000
ROTULOS = {
    "baseline": "Baseline (spaCy + regex)",
    "zero-shot": "Zero-shot",
    "few-shot": "Few-shot",
    "persona": "Persona + few-shot",
}
RAIZ = Path(__file__).resolve().parent
DEMO = json.loads((RAIZ / "data" / "demo_offline.json").read_text(encoding="utf-8"))
DATASET = json.loads((RAIZ / "data" / "dataset.json").read_text(encoding="utf-8"))
EXEMPLO = next(item for item in DATASET if item["id"] == "C05")
ESTADO_AVALIACAO = {"situacao": "ociosa", "concluidos": 0,
                    "total": len(DATASET) * len(ROTULOS), "mensagem": ""}
TRAVA_AVALIACAO = Lock()
app.add_template_filter(percentual)
app.add_template_filter(duracao)
app.add_template_filter(valor_legivel)


def pagina(**contexto):
    return render_template("index.html", rotulos=ROTULOS, campos=CAMPOS,
                           demo=DEMO["texto"], exemplo=EXEMPLO,
                           limite=LIMITE_TEXTO, **contexto)


@app.get("/")
def index():
    """Abre o formulário sem carregar o spaCy ou conectar à API."""
    contrato = request.args.get("contrato")
    texto = next((item["texto"] for item in DATASET if item["id"] == contrato), "")
    return pagina(texto=texto, estrategia="baseline", offline=False)


@app.get("/resultados")
def resultados():
    """Mostra a avaliação mais recente, mesmo após reiniciar o Flask."""
    configurar_ambiente()
    pasta = RAIZ / "resultados"
    metricas, atualizado = ler_metricas(pasta)
    exemplos, falhas = ler_exemplos(pasta)
    return pagina(aba="resultados", metricas=metricas, atualizado=atualizado,
                  exemplos=exemplos, falhas=falhas, total_contratos=len(DATASET),
                  api_configurada=bool(os.getenv("DEEPSEEK_API_KEY", "").strip()))


def atualizar_progresso(estrategia: str, avaliados: int) -> None:
    with TRAVA_AVALIACAO:
        ESTADO_AVALIACAO["concluidos"] = tuple(ROTULOS).index(estrategia) * len(DATASET) + avaliados
        ESTADO_AVALIACAO["mensagem"] = f"{ROTULOS[estrategia]} · {avaliados} de {len(DATASET)} processados"


def avaliar_em_segundo_plano(offline: bool) -> None:
    try:
        executar_avaliacao(usar_cache=offline, progresso=atualizar_progresso)
    except Exception:
        app.logger.exception("Falha na avaliação solicitada pela interface")
        with TRAVA_AVALIACAO:
            ESTADO_AVALIACAO.update(situacao="erro", mensagem="A avaliação foi interrompida. Consulte o terminal do Flask.")
    else:
        with TRAVA_AVALIACAO:
            ESTADO_AVALIACAO.update(situacao="concluida", mensagem="Avaliação concluída.")


@app.route("/avaliacao", methods=["GET", "POST"])
def avaliacao():
    """Inicia uma única avaliação por vez no servidor local e permite acompanhar o progresso."""
    if request.method == "GET":
        with TRAVA_AVALIACAO:
            return jsonify(ESTADO_AVALIACAO)

    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or type(corpo.get("offline")) is not bool:
        return jsonify(erro="Selecione o modo de avaliação."), 400
    offline = corpo["offline"]
    configurar_ambiente()
    if not offline and not os.getenv("DEEPSEEK_API_KEY", "").strip():
        return jsonify(erro="Configure DEEPSEEK_API_KEY no .env para avaliar com a API."), 400

    with TRAVA_AVALIACAO:
        if ESTADO_AVALIACAO["situacao"] == "executando":
            return jsonify(erro="Já existe uma avaliação em andamento."), 409
        ESTADO_AVALIACAO.update(situacao="executando", concluidos=0, mensagem="Preparando avaliação…")
        Thread(target=avaliar_em_segundo_plano, args=(offline,), daemon=True).start()
        return jsonify(ESTADO_AVALIACAO), 202


def executar(texto: str, estrategia: str, offline: bool) -> tuple[Contrato, str]:
    """Prioriza o cache real e permite demonstrar a interface sem credenciais."""
    if estrategia == "baseline":
        try:
            return extrair_baseline(texto), "baseline"
        except RuntimeError as erro:
            raise ErroExtracao(str(erro), 503) from erro
    try:
        saida = consultar(texto, estrategia, offline)
        return saida.registro.contrato, saida.origem
    except ErroExtracao as erro:
        if offline and erro.status == 404 and texto == DEMO["texto"]:
            return Contrato.model_validate_json(json.dumps(DEMO["saida"])), "demo"
        raise


@app.post("/extrair")
def extrair():
    """Aceita o formulário da página e solicitações com Content-Type JSON."""
    corpo = request.get_json(silent=True) if request.is_json else request.form
    if request.is_json and not isinstance(corpo, dict):
        return jsonify(erro="Envie um objeto JSON com texto, estratégia e modo offline."), 400

    texto = corpo.get("texto", "")
    estrategia = corpo.get("estrategia", "baseline")
    offline = corpo.get("offline", False) if request.is_json else corpo.get("offline") == "on"
    try:
        if not isinstance(texto, str) or not texto.strip():
            raise ErroExtracao("Cole o texto de um contrato fictício.", 400)
        if len(texto) > LIMITE_TEXTO:
            raise ErroExtracao(f"O texto pode ter até {LIMITE_TEXTO} caracteres.", 400)
        if estrategia != "baseline" and estrategia not in ESTRATEGIAS:
            raise ErroExtracao("Selecione uma estratégia válida.", 400)
        if not isinstance(offline, bool):
            raise ErroExtracao("O campo offline deve ser verdadeiro ou falso.", 400)

        inicio = perf_counter()
        contrato, origem = executar(texto.strip(), estrategia, offline)
        dados = contrato.model_dump(mode="json")
        resultado = {
            "contrato": dados,
            "origem": origem,
            "tempo_ms": round((perf_counter() - inicio) * 1000, 2),
            "campos_nulos": [campo for campo, valor in dados.items() if valor is None],
        }
    except ErroExtracao as erro:
        if request.is_json:
            return jsonify(erro=str(erro)), erro.status
        return pagina(texto=texto, estrategia=estrategia, offline=offline, erro=str(erro)), erro.status

    if request.is_json:
        return jsonify(resultado)
    return pagina(texto=texto, estrategia=estrategia, offline=offline, resultado=resultado)


if __name__ == "__main__":
    app.run(host="localhost", port=5000)
