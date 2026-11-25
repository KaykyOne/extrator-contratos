# extrator-contratos

Projeto universitário de PLN e IA generativa em Python 3.10+. Extrai oito campos de contratos de aluguel em português e devolve um objeto JSON validado com Pydantic. **Todos os textos e dados do projeto são fictícios.**

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt && python -m spacy download pt_core_news_sm
cp .env.example .env
```

No Windows PowerShell, ative o ambiente com `.venv\Scripts\Activate.ps1`. Para as chamadas online, preencha `DEEPSEEK_API_KEY` no arquivo `.env`, que está no `.gitignore`. Use somente contratos fictícios no modo online, pois o texto é enviado à API.

O modelo configurado por padrão é `deepseek-v4-pro` em modo sem raciocínio, com `temperature=0`. O identificador `deepseek-chat`, solicitado no enunciado, foi aposentado pela DeepSeek em 24/07/2026. É possível selecioná-lo com `DEEPSEEK_MODEL=deepseek-chat` para reproduzir a configuração histórica. A API atual pode rejeitar esse identificador. [Comunicado da DeepSeek](https://api-docs.deepseek.com/news/news260424/) · [Parâmetros da API](https://api-docs.deepseek.com/api/create-chat-completion/)

## Aplicação

```bash
python app.py
```

Abra [http://localhost:5000](http://localhost:5000). Cole o contrato, selecione uma estratégia e clique em **Extrair**. A página mostra o JSON, o tempo, a origem da saída e os campos ausentes. `POST /extrair` também aceita um objeto JSON com `texto`, `estrategia` e `offline`. As estratégias aceitas são `baseline`, `zero-shot`, `few-shot` e `persona`.

Em **Resultados**, compare a acurácia geral em barras, a acurácia por campo em uma tabela colorida, a cobertura, o tempo médio e exemplos de erro. O painel abre com o último relatório salvo. **Rodar avaliação** permite iniciar e acompanhar uma execução pelo navegador. Para demonstrar a extração com um texto que entrou na avaliação, carregue **Contrato C05 da avaliação** na aba **Extrair**.

O baseline funciona localmente após instalar o modelo spaCy. Para reproduzir respostas reais sem internet, extraia antes em modo online e repita com **Modo offline (cache)** marcado. O cache depende do texto, da estratégia de prompt e do modelo. **Carregar exemplo offline** preenche um contrato com saída ilustrativa preparada para que a interface possa ser demonstrada sem uma primeira chamada à API.

## Avaliação

```bash
python avaliar.py
```

Com uma chave, o avaliador faz 72 chamadas iniciais, uma para cada par de contrato e estratégia de LLM, e repete a chamada uma vez se a resposta for inválida. O terminal mostra qual contrato está sendo consultado e imprime a tabela ao terminar. Para reaproveitar somente respostas reais salvas, inclusive após interromper uma execução online, use `python avaliar.py --offline`. Sem chave, esse modo é ativado automaticamente. Quando não há uma resposta real para um contrato, a cobertura diminui. O exemplo ilustrativo da interface fica fora da avaliação.

A acurácia geral compara todos os campos das saídas validadas com o gabarito. A avaliação ignora diferenças de caixa, acentuação e pontuação em strings e compara números por valor decimal. Um `null` correto conta como acerto. O tempo médio inclui eventuais repetições e, no modo offline, mede a leitura do cache. As taxas de JSON malformado e esquema inválido são calculadas por resposta da API, inclusive nas novas tentativas. Os valores do cache refletem as tentativas históricas associadas às respostas salvas.

| Resultado | Arquivo |
| --- | --- |
| Métricas em formato tabular | `resultados/metricas.csv` |
| Resumo e acurácia por campo | `resultados/metricas.md` |
| Divergências e falhas de execução | `resultados/erros.md` |

## Técnicas

- **Baseline.** O NER do modelo `pt_core_news_sm` identifica candidatos do tipo pessoa. Rótulos e padrões de contexto associam nomes aos papéis. Expressões regulares procuram datas, valores e outras cláusulas explícitas. O baseline é limitado em conversas indiretas e valores por extenso. [Modelo português do spaCy](https://spacy.io/models/pt/)
- **Zero-shot.** Recebe apenas instruções e o contrato. **Few-shot.** Inclui três pares de entrada e saída para mostrar formato, conversões e uso de `null`. **Persona + few-shot.** Mantém os mesmos pares e orienta o modelo a conferir a evidência textual como analista de documentos.
- **Validação.** O JSON mode é solicitado à API, e o Pydantic confere as oito chaves, os tipos e as datas. Uma saída vazia, malformada ou fora do esquema dá direito a nova tentativa. A avaliação com gabarito mede se o conteúdo extraído corresponde ao texto. [JSON mode da DeepSeek](https://api-docs.deepseek.com/guides/json_mode/)

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `src/schema.py` | Esquema de saída |
| `src/baseline.py` | NER e expressões regulares |
| `src/llm_extractor.py` e `src/prompts.py` | Cliente DeepSeek e estratégias |
| `src/cache.py` | Cache JSON local em `.cache/llm/` |
| `data/gerar_dataset.py` e `data/dataset.json` | 24 textos fictícios anotados à mão |
| `data/demo_offline.json` | Exemplo ilustrativo da interface |
| `avaliar.py` | Avaliação e geração de relatórios |
| `app.py`, `templates/`, `static/` e `src/painel.py` | Servidor, interface de extração e painel de resultados |

Para regenerar o conjunto de avaliação, execute `python data/gerar_dataset.py`.
