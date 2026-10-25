# Comparador Econômico

Aplicativo interativo para consultar, visualizar e comparar indicadores
econômicos dos **5.570 municípios brasileiros**, dos estados e do Brasil,
de 2010 a 2023.

🔗 **Acesse o aplicativo:** https://comparador-economico.streamlit.app

Projeto de programação aplicada à Economia, desenvolvido por
**Otávio Campelo de Oliveira** com ferramentas gratuitas e dados públicos.

## Funcionalidades

- Consulta de indicadores por Brasil, estado ou município
- Comparação entre dois ou mais estados e entre municípios
- Gráficos de evolução e tabela de dados com colunas configuráveis
- Crescimento no período: variação total e taxa média anual
- Rankings de estados e municípios, com filtro por estado e por faixa de população
- Valores nominais e reais (a preços de 2023), em reais e em dólares

## Indicadores

| Grupo | Indicadores |
|---|---|
| PIB | Nominal e real, em R$ e em US$; per capita nominal e real, em R$ e em US$ |
| Valor adicionado bruto (VAB) | Total, agropecuária, indústria, serviços e administração pública |
| Estrutura produtiva | Participação da agropecuária, da indústria e dos serviços |
| Emprego formal | Vínculos ativos em 31 de dezembro (2020–2023) |
| Finanças públicas | Receita total bruta, despesas (empenhadas, liquidadas e pagas) e investimentos (2020–2023) |

A disponibilidade temporal varia conforme o indicador e a fonte.

## Fontes dos dados

- **IBGE:** PIB dos municípios (SIDRA, tabela 5938) e população
- **RAIS (Ministério do Trabalho e Emprego):** emprego formal e escolaridade
- **Banco Central do Brasil:** IPCA (série SGS 433) e câmbio
- **Tesouro Nacional (SICONFI/FINBRA):** indicadores de receitas, despesas e investimentos.

O PIB real é atualizado pelo deflator para valores de 2023. Os valores em dólar usam a cotação média anual (nominal) ou a cotação média de 2023 (real).

## Tecnologias

Python · pandas · Streamlit · Plotly

## Estrutura do projeto

```
comparador-economico/
├── app/
│   └── Home.py
├── dados/
│   ├── base_economica_municipal_2010_2023_v4.csv
│   └── cambio_medio_anual_2010_2023.csv
├── requirements.txt
├── LICENSE
└── README.md

```

## Próximas atualizações

- Inclusão do ano de **2024**
- Ampliação de **2010 a 2019** para os indicadores que hoje cobrem apenas parte do período

## Autor e contato

Otávio Campelo de Oliveira
📧 otavioc2009@gmail.com

💼 www.linkedin.com/in/ot%C3%A1vio-oliveira-682846otv

## Licença

Todos os direitos reservados. Veja o arquivo [LICENSE](LICENSE).
