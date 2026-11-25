# Exemplos de erro

## baseline

### C03 (formal)

> São partes deste instrumento Sávio de Miralva, locador, e Cíntala de Nebrisol, locatária. Endereço do imóvel: Travessa da Areia Doce, 15. Aluguel mensal: R$ 810,00. Início: 05/10/2030. Prazo de 6 meses. Reajuste por INPC.

- `locatario` · esperado `"Cíntala de Nebrisol"` · extraído `null`

### C05 (informal)

> Cevina de Umbrafim é a proprietária; Ruvano de Solvedra vai morar na Rua Folha de Prata, 18. Ele paga 980 reais todo mês. São 8 meses começando no dia 02/05/2032.

- `locador` · esperado `"Cevina de Umbrafim"` · extraído `null`
- `locatario` · esperado `"Ruvano de Solvedra"` · extraído `null`
- `endereco_imovel` · esperado `"Rua Folha de Prata, 18"` · extraído `null`
- `valor_aluguel` · esperado `980.0` · extraído `null`
- `prazo_meses` · esperado `8` · extraído `null`
- `data_inicio` · esperado `"2032-05-02"` · extraído `null`

### C06 (informal)

> Proprietário: Mirolo de Salnuvem. Inquilina: Vília de Laranéu. Endereço: Rua Pedra de Farinha, 500. O aluguel é R$ 1150,50 por 10 meses. Começa em 09/01/2030. Se sair antes, paga R$ 575,25. Reajuste pelo IPCA.

- `valor_multa_rescisoria` · esperado `575.25` · extraído `null`

## zero-shot

Nenhuma divergência nas saídas validadas.

## few-shot

Nenhuma divergência nas saídas validadas.

## persona

Nenhuma divergência nas saídas validadas.
