# Métricas de extração

Modelo configurado: `deepseek-v4-pro`. Chamadas novas à API para cada estratégia de LLM.

| estrategia | origem | avaliados | total | acuracia_geral | tempo_medio_ms | taxa_json_invalido | taxa_esquema_invalido |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | local | 24 | 24 | 79.69% | 5.71 | — | — |
| zero-shot | API | 24 | 24 | 100.00% | 2336.06 | 0.00% | 0.00% |
| few-shot | API | 24 | 24 | 100.00% | 2007.02 | 0.00% | 0.00% |
| persona | API | 24 | 24 | 100.00% | 2079.67 | 0.00% | 0.00% |

## Acurácia por campo

| estrategia | locador | locatario | endereco_imovel | valor_aluguel | prazo_meses | data_inicio | valor_multa_rescisoria | indice_reajuste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 83.33% | 79.17% | 87.50% | 62.50% | 75.00% | 83.33% | 66.67% | 100.00% |
| zero-shot | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| few-shot | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| persona | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |

A acurácia considera saídas validadas, inclusive campos nulos corretos. A geral é a proporção de acertos sobre todos os campos avaliados. A cobertura aparece em avaliados/total. O tempo mede cada extração concluída, incluindo a repetição quando houver. O modelo spaCy é carregado antes do cronômetro. As taxas usam todas as respostas da API observadas como denominador, inclusive as tentativas rejeitadas. No modo cache, o tempo é de leitura e as taxas são históricas para os registros recuperados. — indica métrica indisponível.
