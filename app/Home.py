
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import hashlib


# --------------------------------------------------
# 1. Configuração da página
# --------------------------------------------------

st.set_page_config(
    page_title="Comparador Econômico",
    page_icon="📊",
    layout="wide",
)


# --------------------------------------------------
# 2. Carregamento da base de dados
# --------------------------------------------------

CAMINHO_BASE = (
    Path(__file__).resolve().parents[1]
    / "dados"
    / "base_economica_municipal_2010_2023_v4.csv"
)

@st.cache_data
def carregar_base(caminho, ultima_modificacao):
    dados = pd.read_csv(caminho, low_memory=False)

    colunas_numericas = [
        "codigo_municipio",
        "ano",
        "pib_nominal_reais",
        "pib_real_2023",
        "pib_per_capita_nominal",
        "pib_per_capita_real_2023",
        "populacao",
        "vinculos_ativos_31_12",
        "fiscal_receita_total_bruta",
        "fiscal_despesas_totais_empenhadas",
        "fiscal_despesas_totais_liquidadas",
        "fiscal_despesas_totais_pagas",
        "fiscal_investimentos_empenhados",
    ]

    for coluna in colunas_numericas:
        if coluna in dados.columns:
            dados[coluna] = pd.to_numeric(
                dados[coluna], errors="coerce"
            )

    # Carrega as médias anuais do dólar
    caminho_cambio = (
        Path(caminho).parent
        / "cambio_medio_anual_2010_2023.csv"
    )

    cambio = pd.read_csv(caminho_cambio)
    cambio["ano"] = pd.to_numeric(cambio["ano"], errors="raise")

    # Associa o câmbio a cada ano da base econômica
    dados = dados.merge(
        cambio[["ano", "cambio_medio_brl_por_usd"]],
        on="ano",
        how="left",
        validate="many_to_one",
    )

    # PIB nominal convertido pela média cambial de cada ano
    dados["pib_nominal_usd_milhoes"] = (
        dados["pib_nominal_reais"]
        / dados["cambio_medio_brl_por_usd"]
        / 1_000_000
    )

    # PIB real convertido pelo câmbio médio fixo de 2023
    cambio_2023 = cambio.loc[
        cambio["ano"] == 2023,
        "cambio_medio_brl_por_usd",
    ].iloc[0]

    
    dados["pib_real_usd_2023_milhoes"] = (
        dados["pib_real_2023"]
        / cambio_2023
        / 1_000_000
    )

    # PIB per capita nominal em dólares correntes
    dados["pib_per_capita_nominal_usd"] = (
        dados["pib_nominal_reais"]
        / dados["populacao"]
        / dados["cambio_medio_brl_por_usd"]
    )

    # PIB per capita real em dólares de 2023
    dados["pib_per_capita_real_usd_2023"] = (
        dados["pib_real_2023"]
        / dados["populacao"]
        / cambio_2023
    )

    return dados

if not CAMINHO_BASE.exists():
    st.error(
        "Não foi possível encontrar a base de dados. "
        "Confira se o arquivo CSV está na pasta dados."
    )
    st.stop()

base = carregar_base(
    str(CAMINHO_BASE),
    CAMINHO_BASE.stat().st_mtime,
)

if base.empty:
    st.error("A base de dados está vazia.")
    st.stop()

base["ano"] = pd.to_numeric(base["ano"], errors="coerce")
base = base.dropna(subset=["ano"]).copy()
base["ano"] = base["ano"].astype(int)


# --------------------------------------------------
# 3. Indicadores gerais da base
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    total_municipios = base["codigo_municipio"].nunique()
    st.metric(
        "Municípios",
        f"{total_municipios:,}".replace(",", "."),
    )

with col2:
    st.metric(
        "Registros",
        f"{len(base):,}".replace(",", "."),
    )

with col3:
    ano_minimo = int(base["ano"].min())
    ano_maximo = int(base["ano"].max())
    st.metric("Período disponível", f"{ano_minimo}–{ano_maximo}")


st.divider()


# --------------------------------------------------
# 4. Seleção do indicador
# --------------------------------------------------

indicadores = {
    "PIB nominal": {
        "coluna": "pib_nominal_reais",
        "unidade": "R$ milhões",
        "tipo": "pib_total",
        "agregacao": "sum",
    },
    "PIB real": {
        "coluna": "pib_real_2023",
        "unidade": "R$ milhões",
        "tipo": "pib_total",
        "agregacao": "sum",
    },
    "PIB nominal (US$ milhões)": {
        "coluna": "pib_nominal_usd_milhoes",
        "unidade": "US$ milhões",
        "tipo": "pib_total",
        "agregacao": "sum",
    },
    "PIB real (US$ milhões de 2023)": {
        "coluna": "pib_real_usd_2023_milhoes",
        "unidade": "US$ milhões de 2023",
        "tipo": "pib_total",
        "agregacao": "sum",
    },
    "PIB per capita nominal": {
        "coluna": "pib_per_capita_nominal",
        "unidade": "R$ por habitante",
        "tipo": "per_capita",
        "agregacao": "mean",
    },
    "PIB per capita real": {
        "coluna": "pib_per_capita_real_2023",
        "unidade": "R$ por habitante",
        "tipo": "per_capita",
        "agregacao": "mean",
    },
    "PIB per capita nominal (US$)": {
        "coluna": "pib_per_capita_nominal_usd",
        "unidade": "US$ por habitante",
        "tipo": "per_capita",
        "agregacao": "mean",
    },
    "PIB per capita real (US$ de 2023)": {
        "coluna": "pib_per_capita_real_usd_2023",
        "unidade": "US$ de 2023 por habitante",
        "tipo": "per_capita",
        "agregacao": "mean",
    },
    "Emprego formal": {
        "coluna": "vinculos_ativos_31_12",
        "unidade": "vínculos ativos",
        "tipo": "quantidade",
        "agregacao": "sum",
    },
    "Receita total bruta": {
        "coluna": "fiscal_receita_total_bruta",
        "unidade": "R$ milhões",
        "tipo": "fiscal_total",
        "agregacao": "sum",
    },
    "Despesas totais empenhadas": {
        "coluna": "fiscal_despesas_totais_empenhadas",
        "unidade": "R$ milhões",
        "tipo": "fiscal_total",
        "agregacao": "sum",
    },
    "Despesas totais liquidadas": {
        "coluna": "fiscal_despesas_totais_liquidadas",
        "unidade": "R$ milhões",
        "tipo": "fiscal_total",
        "agregacao": "sum",
    },
    "Despesas totais pagas": {
        "coluna": "fiscal_despesas_totais_pagas",
        "unidade": "R$ milhões",
        "tipo": "fiscal_total",
        "agregacao": "sum",
    },
    "Investimentos empenhados": {
        "coluna": "fiscal_investimentos_empenhados",
        "unidade": "R$ milhões",
        "tipo": "fiscal_total",
        "agregacao": "sum",
    },
    "VAB total": {
        "coluna": "vab_total_mil_reais",
        "unidade": "R$ milhões",
        "tipo": "vab_total",
        "agregacao": "sum",
    },
    "VAB da agropecuária": {
        "coluna": "vab_agropecuaria_mil_reais",
        "unidade": "R$ milhões",
        "tipo": "vab_total",
        "agregacao": "sum",
    },
    "VAB da indústria": {
        "coluna": "vab_industria_mil_reais",
        "unidade": "R$ milhões",
        "tipo": "vab_total",
        "agregacao": "sum",
    },
    "VAB dos serviços": {
        "coluna": "vab_servicos_mil_reais",
        "unidade": "R$ milhões",
        "tipo": "vab_total",
        "agregacao": "sum",
    },
    "VAB da administração pública": {
        "coluna": "vab_administracao_publica_mil_reais",
        "unidade": "R$ milhões",
        "tipo": "vab_total",
        "agregacao": "sum",
    },
    
    "Participação da agropecuária": {
        "coluna": "participacao_agropecuaria_pct",
        "unidade": "%",
        "tipo": "percentual",
        "agregacao": "mean",
    },
    "Participação da indústria": {
        "coluna": "participacao_industria_pct",
        "unidade": "%",
        "tipo": "percentual",
        "agregacao": "mean",
    },
    "Participação dos serviços": {
        "coluna": "participacao_servicos_pct",
        "unidade": "%",
        "tipo": "percentual",
        "agregacao": "mean",
    },
        "Participação total dos serviços": {
        "coluna": "vab_servicos_mil_reais",
        "unidade": "%",
        "tipo": "percentual",
        "agregacao": "mean",
    },
}

indicadores_disponiveis = {
    nome: info
    for nome, info in indicadores.items()
    if info["coluna"] in base.columns
}

indicador_nome = st.selectbox(
    "Indicador econômico",
    options=list(indicadores_disponiveis.keys()),
)

info_indicador = indicadores_disponiveis[indicador_nome]
coluna_indicador = info_indicador["coluna"]

st.caption(f"Unidade de exibição: {info_indicador['unidade']}")


# --------------------------------------------------
# 5. Filtros geográficos e temporais
# --------------------------------------------------

st.subheader("Filtros")

col_estado, col_municipio = st.columns(2)

estados_disponiveis = sorted(
    base["estado"].dropna().astype(str).unique().tolist()
)

with col_estado:
    estado_selecionado = st.selectbox(
        "Estado",
        options=["Todos"] + estados_disponiveis,
    )

if estado_selecionado == "Todos":
    ufs_selecionadas = None
else:
    ufs_selecionadas = (
        base.loc[
            base["estado"].astype(str) == estado_selecionado,
            "uf",
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )


# Seleção de estados para comparação
estados_comparacao = st.multiselect(
    "Estados para comparar",
    options=estados_disponiveis,
    help="Selecione dois ou mais estados para comparar seus indicadores.",
)

# Define os estados utilizados na consulta
if estados_comparacao:
    ufs_comparacao = (
        base.loc[
            base["estado"].astype(str).isin(estados_comparacao),
            "uf",
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
else:
    ufs_comparacao = None

# Define os municípios disponíveis conforme os filtros
if ufs_selecionadas is not None:
    ufs_municipios = ufs_selecionadas
elif ufs_comparacao is not None:
    ufs_municipios = ufs_comparacao
else:
    ufs_municipios = None

if ufs_municipios is None:
    municipios_filtrados = base[
        ["codigo_municipio", "municipio"]
    ].drop_duplicates()
else:
    municipios_filtrados = base.loc[
        base["uf"].astype(str).str.strip().isin(ufs_municipios),
        ["codigo_municipio", "municipio"],
    ].drop_duplicates()

municipios_filtrados = municipios_filtrados.sort_values("municipio")

opcoes_municipios = [
    (int(codigo), nome)
    for codigo, nome in municipios_filtrados[
        ["codigo_municipio", "municipio"]
    ].itertuples(index=False, name=None)
    if pd.notna(codigo) and pd.notna(nome)
]

# Seleção de municípios para comparação
municipios_comparacao = st.multiselect(
    "Municípios para comparar",
    options=opcoes_municipios,
    format_func=lambda opcao: opcao[1],
    help="Selecione dois ou mais municípios para compará-los.",
)

with col_municipio:
    municipio_selecionado = st.selectbox(
        "Município",
        options=[None] + opcoes_municipios,
        format_func=lambda opcao: (
            "Todos os municípios"
            if opcao is None
            else opcao[1]
        ),
    )

# Define os anos disponíveis conforme o indicador
if (
    indicador_nome == "Emprego formal"
    or info_indicador["tipo"] == "fiscal_total"
):
    anos_disponiveis = sorted(
        base.loc[
            base["ano"].between(2020, 2023)
            & base[coluna_indicador].notna(),
            "ano",
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )
else:
    anos_disponiveis = sorted(
        base["ano"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

if not anos_disponiveis:
    st.warning(
        "Não há anos com dados disponíveis para este indicador."
    )
    st.stop()

# Seleção do período
col_inicio, col_fim = st.columns(2)

with col_inicio:
    ano_inicio = st.selectbox(
        "Ano inicial",
        options=anos_disponiveis,
        index=0,
        format_func=lambda ano: str(ano),
        key=f"ano_inicio_{indicador_nome}",
    )

with col_fim:
    anos_finais = [
        ano for ano in anos_disponiveis
        if ano >= ano_inicio
    ]

    ano_fim = st.selectbox(
        "Ano final",
        options=anos_finais,
        index=len(anos_finais) - 1,
        format_func=lambda ano: str(ano),
        key=f"ano_fim_{indicador_nome}",
    )


# --------------------------------------------------
# 6. Aplicação dos filtros
# --------------------------------------------------

consulta = base.loc[
    base["ano"].between(ano_inicio, ano_fim)
].copy()

# Aplica os filtros de estado
if estados_comparacao:
    consulta = consulta.loc[
        consulta["uf"].astype(str).str.strip().isin(
            ufs_comparacao
        )
    ]
elif ufs_selecionadas is not None:
    consulta = consulta.loc[
        consulta["uf"].astype(str).str.strip().isin(
            ufs_selecionadas
        )
    ]

# Se houver municípios selecionados para comparação,
# utiliza todos eles na consulta
if municipios_comparacao:
    codigos_comparacao = [
        codigo for codigo, nome in municipios_comparacao
    ]

    consulta = consulta.loc[
        consulta["codigo_municipio"].isin(codigos_comparacao)
    ]

# Caso contrário, mantém o filtro de município individual
elif municipio_selecionado is not None:
    codigo_municipio = municipio_selecionado[0]

    consulta = consulta.loc[
        consulta["codigo_municipio"] == codigo_municipio
    ]

st.caption(
    f"Consulta: {len(consulta):,} registros encontrados.".replace(
        ",", "."
    )
)

if consulta.empty:
    st.info(
        "Não foram encontrados dados para os filtros selecionados."
    )


# --------------------------------------------------
# 7. Preparação do gráfico e da tabela
# --------------------------------------------------

# Define o nível de agrupamento dos dados.
# Para estados, agrupa só por UF (o nome do estado é preenchido depois),
# pois o groupby descarta linhas com chave ausente.
if estados_comparacao:
    chaves_agrupamento = ["uf", "ano"]
elif municipios_comparacao:
    chaves_agrupamento = [
        "codigo_municipio",
        "municipio",
        "ano",
    ]
else:
    chaves_agrupamento = ["ano"]

if info_indicador["tipo"] == "per_capita":

    # Identifica qual PIB usar no cálculo
    if indicador_nome in (
        "PIB per capita real",
        "PIB per capita real (US$ de 2023)",
    ):
        coluna_pib = "pib_real_2023"
    else:
        coluna_pib = "pib_nominal_reais"

    dados_validos = consulta.dropna(
        subset=[coluna_pib, "populacao"]
    ).copy()

    dados_grafico = (
        dados_validos.groupby(chaves_agrupamento)
        .agg(
            pib_total=(coluna_pib, "sum"),
            populacao_total=("populacao", "sum"),
        )
        .reset_index()
    )

    dados_grafico["valor"] = (
        dados_grafico["pib_total"]
        / dados_grafico["populacao_total"]
    )

    # Converte o PIB per capita para dólares
    if indicador_nome == "PIB per capita nominal (US$)":

        cambio_por_ano = (
            dados_validos.groupby("ano")[
                "cambio_medio_brl_por_usd"
            ]
            .first()
            .rename("cambio")
            .reset_index()
        )

        dados_grafico = dados_grafico.merge(
            cambio_por_ano,
            on="ano",
            how="left",
        )

        dados_grafico["valor"] = (
            dados_grafico["valor"] / dados_grafico["cambio"]
        )

    elif indicador_nome == "PIB per capita real (US$ de 2023)":

        cambio_2023 = base.loc[
            base["ano"] == 2023,
            "cambio_medio_brl_por_usd",
        ].dropna().iloc[0]

        dados_grafico["valor"] = (
            dados_grafico["valor"] / cambio_2023
        )

    dados_grafico = dados_grafico[
        chaves_agrupamento + ["valor"]
    ]


elif info_indicador["tipo"] == "percentual":

    # Calcula as participações setoriais
    componentes = {
        "Participação da agropecuária": [
            "vab_agropecuaria_mil_reais",
        ],
        "Participação da indústria": [
            "vab_industria_mil_reais",
        ],
        "Participação dos serviços": [
            "vab_servicos_mil_reais",
        ],
        "Participação total dos serviços": [
            "vab_servicos_mil_reais",
            "vab_administracao_publica_mil_reais",
        ],
    }

    colunas_setoriais = componentes[indicador_nome]

    colunas_necessarias = [
        "vab_total_mil_reais",
        *colunas_setoriais,
    ]

    dados_validos = consulta.dropna(
        subset=colunas_necessarias
    ).copy()

    dados_grafico = (
        dados_validos.groupby(chaves_agrupamento)[
            colunas_necessarias
        ]
        .sum()
        .reset_index()
    )

    # Participação = VAB do setor / VAB total × 100
    dados_grafico["valor"] = (
        dados_grafico[colunas_setoriais].sum(axis=1)
        / dados_grafico["vab_total_mil_reais"]
        * 100
    )

    dados_grafico = dados_grafico[
        chaves_agrupamento + ["valor"]
    ]


else:

    # Soma de grupo totalmente vazio vira NaN (e não 0),
    # para o ano sem dado não aparecer como zero
    if info_indicador["agregacao"] == "sum":
        funcao_agregacao = lambda s: s.sum(min_count=1)
    else:
        funcao_agregacao = info_indicador["agregacao"]

    # Agrega o indicador no nível de comparação escolhido
    dados_grafico = (
        consulta.groupby(chaves_agrupamento)[coluna_indicador]
        .agg(funcao_agregacao)
        .reset_index()
        .rename(columns={coluna_indicador: "valor"})
    )

    # Converte PIB total de reais para milhões de reais
    if (
        info_indicador["tipo"] == "pib_total"
        and coluna_indicador not in (
            "pib_nominal_usd_milhoes",
            "pib_real_usd_2023_milhoes",
        )
    ):
        dados_grafico["valor"] = (
            dados_grafico["valor"] / 1_000_000
        )

    # Converte VAB de mil reais para milhões de reais
    elif info_indicador["tipo"] == "vab_total":
        dados_grafico["valor"] = (
            dados_grafico["valor"] / 1_000
        )

    # Converte indicadores fiscais de reais para milhões
    elif info_indicador["tipo"] == "fiscal_total":
        dados_grafico["valor"] = (
            dados_grafico["valor"] / 1_000_000
        )

# Remove observações sem valor
dados_grafico = dados_grafico.dropna(
    subset=["valor"]
).copy()

# Para comparação de estados, traz o nome do estado a partir da UF
if estados_comparacao:
    mapa_uf_estado = (
        base.dropna(subset=["estado"])
        .assign(uf_limpa=lambda d: d["uf"].astype(str).str.strip())
        .drop_duplicates("uf_limpa")
        .set_index("uf_limpa")["estado"]
    )

    dados_grafico["estado"] = (
        dados_grafico["uf"].astype(str).str.strip().map(mapa_uf_estado)
    )

# Prepara o ano para exibição
dados_grafico["ano"] = (
    dados_grafico["ano"].astype(int).astype(str)
)


# --------------------------------------------------
# 8. Gráfico de evolução
# --------------------------------------------------

st.subheader("Evolução do indicador")

if not dados_grafico.empty:
    grafico = dados_grafico.copy()
    grafico["ano"] = grafico["ano"].astype(int).astype(str)

    fig = px.line(
        grafico,
        x="ano",
        y="valor",
        markers=True,
        labels={
            "ano": "Ano",
            "valor": info_indicador["unidade"],
        },
        category_orders={
            "ano": grafico["ano"].tolist(),
        },
    )

    if municipios_comparacao:
        fig = px.line(
            grafico,
            x="ano",
            y="valor",
            color="municipio",
            markers=True,
            labels={
                "ano": "Ano",
                "valor": info_indicador["unidade"],
                "municipio": "Município",
            },
            category_orders={
                "ano": sorted(grafico["ano"].unique().tolist()),
            },
        )
    else:
        fig = px.line(
            grafico,
            x="ano",
            y="valor",
            markers=True,
            labels={
                "ano": "Ano",
                "valor": info_indicador["unidade"],
            },
            category_orders={
                "ano": sorted(grafico["ano"].unique().tolist()),
            },
        )

    if estados_comparacao:
        fig = px.line(
            grafico,
            x="ano",
            y="valor",
            color="estado",
            markers=True,
            labels={
                "ano": "Ano",
                "valor": info_indicador["unidade"],
                "estado": "Estado",
            },
            category_orders={
                "ano": sorted(grafico["ano"].unique().tolist()),
            },
        )

    elif municipios_comparacao:
        fig = px.line(
            grafico,
            x="ano",
            y="valor",
            color="municipio",
            markers=True,
            labels={
                "ano": "Ano",
                "valor": info_indicador["unidade"],
                "municipio": "Município",
            },
            category_orders={
                "ano": sorted(grafico["ano"].unique().tolist()),
            },
        )

    else:
        fig = px.line(
            grafico,
            x="ano",
            y="valor",
            markers=True,
            labels={
                "ano": "Ano",
                "valor": info_indicador["unidade"],
            },
            category_orders={
                "ano": sorted(grafico["ano"].unique().tolist()),
            },
        )

    # Formato numérico dos valores no tooltip
    fig.update_traces(
        hovertemplate=(
            "Ano: %{x}<br>"
            "Valor: %{y:,.3f}"
            "<extra></extra>"
        )
    )

    # Ajustes visuais do gráfico
    fig.update_layout(
        xaxis_title="Ano",
        yaxis_title=info_indicador["unidade"],
        hoverlabel=dict(namelength=-1),
    )

    # Mantém os anos como categorias, sem valores intermediários
    anos_grafico = sorted(grafico["ano"].unique().tolist())
    
    fig.update_xaxes(
        type="category",
        tickmode="array",
        tickvals=anos_grafico,
        ticktext=anos_grafico,
    )

    # Formatação numérica do eixo vertical
    fig.update_yaxes(
        tickformat=",.2f",
        separatethousands=True,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"locale": "pt-BR"},
    )

else:
    st.info("Não há valores disponíveis para construir o gráfico.")


# --------------------------------------------------
# 9. Tabela de dados
# --------------------------------------------------

st.subheader("Tabela de dados")

coluna_valor = f"Valor ({info_indicador['unidade']})"


def formatar_numero(valor):
    if pd.isna(valor):
        return "—"

    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", "."
    )


# Define o modo e as colunas padrão da tabela
if estados_comparacao:
    modo_tabela = "estados"
    ordem_linhas = ["estado", "ano_num"]
    nomes_colunas = {
        "estado": "Estado",
        "uf": "UF",
        "ano": "Ano",
        "valor": coluna_valor,
    }
    colunas_padrao = ["Estado", "Ano", coluna_valor]
elif municipios_comparacao:
    modo_tabela = "municipios"
    ordem_linhas = ["municipio", "ano_num"]
    nomes_colunas = {
        "codigo_municipio": "Código do município",
        "municipio": "Município",
        "ano": "Ano",
        "valor": coluna_valor,
    }
    colunas_padrao = [
        "Código do município", "Município", "Ano", coluna_valor
    ]
else:
    modo_tabela = "unico"
    ordem_linhas = ["ano_num"]
    nomes_colunas = {
        "ano": "Ano",
        "valor": coluna_valor,
    }
    colunas_padrao = ["Ano", coluna_valor]

# Monta a tabela com todas as colunas possíveis do modo
tabela = dados_grafico.copy()
tabela["ano_num"] = tabela["ano"].astype(int)
tabela = tabela.sort_values(ordem_linhas).reset_index(drop=True)

tabela["valor"] = tabela["valor"].apply(formatar_numero)

tabela = tabela[list(nomes_colunas.keys())].rename(columns=nomes_colunas)

# A chave do widget muda quando o indicador, o estado ou o município
# mudam, o que faz as colunas voltarem ao padrão
assinatura_selecao = str(
    (
        indicador_nome,
        modo_tabela,
        tuple(sorted(estados_comparacao)),
        tuple(sorted(c for c, _ in municipios_comparacao)),
        estado_selecionado,
        municipio_selecionado,
    )
)
chave_colunas = "colunas_tabela_" + hashlib.md5(
    assinatura_selecao.encode()
).hexdigest()

colunas_escolhidas = st.multiselect(
    "Colunas da tabela (a ordem segue a sequência em que você as seleciona)",
    options=list(tabela.columns),
    default=colunas_padrao,
    key=chave_colunas,
)

if not colunas_escolhidas:
    st.warning("Selecione pelo menos uma coluna para exibir a tabela.")
    colunas_escolhidas = colunas_padrao

st.dataframe(
    tabela[colunas_escolhidas],
    use_container_width=True,
    hide_index=True,
)


# --------------------------------------------------
# 9.1 Crescimento no período (estados e municípios)
# --------------------------------------------------

if estados_comparacao or municipios_comparacao:

    st.subheader("Crescimento no período")

    if ano_inicio == ano_fim:
        st.info(
            "Selecione um ano inicial diferente do final "
            "para ver o crescimento."
        )
    else:
        if estados_comparacao:
            chave_entidade = ["estado"]
            rotulo_entidade = "Estado"
        else:
            chave_entidade = ["codigo_municipio", "municipio"]
            rotulo_entidade = "Município"

        nome_entidade = chave_entidade[-1]

        # Nesta altura o ano em dados_grafico é texto; usa cópia numérica
        d = dados_grafico.assign(
            ano_num=dados_grafico["ano"].astype(int)
        )

        valor_inicial = (
            d.loc[d["ano_num"] == ano_inicio]
            .set_index(chave_entidade)["valor"]
            .rename("valor_inicial")
        )
        valor_final = (
            d.loc[d["ano_num"] == ano_fim]
            .set_index(chave_entidade)["valor"]
            .rename("valor_final")
        )

        crescimento = pd.concat(
            [valor_inicial, valor_final], axis=1
        ).reset_index()

        eh_percentual = info_indicador["tipo"] == "percentual"
        n_anos = ano_fim - ano_inicio

        if eh_percentual:
            # Para participações, a diferença em pontos percentuais
            # é mais correta do que a variação percentual
            crescimento["variacao"] = (
                crescimento["valor_final"]
                - crescimento["valor_inicial"]
            )
            rotulo_variacao = "Variação (p.p.)"
            crescimento["taxa_anual"] = pd.NA
        else:
            base_valida = crescimento["valor_inicial"] > 0

            crescimento["variacao"] = (
                (crescimento["valor_final"]
                 / crescimento["valor_inicial"] - 1) * 100
            ).where(base_valida)

            crescimento["taxa_anual"] = (
                ((crescimento["valor_final"]
                  / crescimento["valor_inicial"]) ** (1 / n_anos) - 1)
                * 100
            ).where(base_valida & (crescimento["valor_final"] > 0))

            rotulo_variacao = "Variação total (%)"

        crescimento = crescimento.sort_values(
            "variacao", ascending=False
        )

        # Gráfico de barras da variação
        dados_barra = crescimento.dropna(subset=["variacao"])

        if not dados_barra.empty:
            fig_cresc = px.bar(
                dados_barra,
                x=nome_entidade,
                y="variacao",
                color=nome_entidade,
                labels={
                    nome_entidade: rotulo_entidade,
                    "variacao": rotulo_variacao,
                },
            )
            fig_cresc.update_layout(showlegend=False)
            fig_cresc.update_yaxes(
                tickformat=",.1f", separatethousands=True
            )
            st.plotly_chart(
                fig_cresc,
                use_container_width=True,
                config={"locale": "pt-BR"},
            )

        # Tabela
        tabela_cresc = pd.DataFrame(
            {
                rotulo_entidade: crescimento[nome_entidade],
                f"Valor em {ano_inicio}": crescimento[
                    "valor_inicial"
                ].apply(formatar_numero),
                f"Valor em {ano_fim}": crescimento[
                    "valor_final"
                ].apply(formatar_numero),
                rotulo_variacao: crescimento["variacao"].apply(
                    formatar_numero
                ),
            }
        )

        if not eh_percentual:
            tabela_cresc["Taxa média anual (%)"] = crescimento[
                "taxa_anual"
            ].apply(formatar_numero)

        st.dataframe(
            tabela_cresc,
            use_container_width=True,
            hide_index=True,
        )

        if info_indicador["tipo"] in (
            "pib_total", "per_capita", "fiscal_total", "vab_total"
        ) and "real" not in indicador_nome.lower():
            st.caption(
                "Atenção: este indicador está em valores nominais, "
                "então o crescimento inclui a inflação. Para comparar "
                "o crescimento efetivo, use a versão real."
            )

        st.caption(
            "Entidades sem dado no ano inicial ou no final aparecem "
            "com '—'."
        )


# --------------------------------------------------
# 10. Visualização dos registros originais filtrados
# --------------------------------------------------

with st.expander("Consultar registros municipais da base"):
    colunas_visualizacao = [
        coluna
        for coluna in [
            "municipio",
            "uf",
            "ano",
            "pib_nominal_reais",
            "pib_real_2023",
            "pib_per_capita_nominal",
            "pib_per_capita_real_2023",
            "populacao",
            "vinculos_ativos_31_12",
        ]
        if coluna in consulta.columns
    ]

    registros = consulta[colunas_visualizacao].copy()

    st.dataframe(
        registros,
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# 10.1 Ranking
# --------------------------------------------------


st.divider()
st.header("Ranking")
st.caption(f"Indicador do ranking: {indicador_nome}")

# Ano padrão: 2023 (ou o último disponível, se o indicador não tiver 2023)
indice_ano_padrao = (
    anos_disponiveis.index(2023)
    if 2023 in anos_disponiveis
    else len(anos_disponiveis) - 1
)

col_r1, col_r2, col_r3, col_r4 = st.columns(4)

with col_r1:
    nivel_ranking = st.radio(
        "Nível",
        options=["Estados", "Municípios"],
        index=0,
        horizontal=True,
        key="rk_nivel",
    )

with col_r2:
    ano_ranking = st.selectbox(
        "Ano do ranking",
        options=anos_disponiveis,
        index=indice_ano_padrao,
        key=f"rk_ano_{indicador_nome}",
    )

with col_r3:
    quantidade_ranking = st.selectbox(
        "Quantidade exibida",
        options=[10, 20, 50, 100],
        index=0,
        key="rk_quantidade",
    )

with col_r4:
    ordem_ranking = st.radio(
        "Ordem",
        options=["Maiores valores", "Menores valores"],
        index=0,
        key="rk_ordem",
    )

dados_ano = base.loc[base["ano"] == ano_ranking].copy()

# Filtros exclusivos do ranking de municípios
if nivel_ranking == "Municípios":

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        estado_ranking = st.selectbox(
            "Restringir a um estado (opcional)",
            options=["Todos"] + estados_disponiveis,
            index=0,
            key="rk_estado",
        )

    faixas_populacao = [
        0, 5_000, 10_000, 20_000, 50_000,
        100_000, 500_000, 1_000_000, 50_000_000,
    ]

    def formatar_faixa(valor):
        if valor == faixas_populacao[-1]:
            return "sem limite"
        return f"{valor:,}".replace(",", ".")

    with col_f2:
        pop_min, pop_max = st.select_slider(
            "Faixa de população do município (habitantes)",
            options=faixas_populacao,
            value=(faixas_populacao[0], faixas_populacao[-1]),
            format_func=formatar_faixa,
            key="rk_faixa_pop",
        )

    if estado_ranking != "Todos":
        dados_ano = dados_ano.loc[
            dados_ano["estado"].astype(str) == estado_ranking
        ]

    if pop_min > faixas_populacao[0]:
        dados_ano = dados_ano.loc[dados_ano["populacao"] >= pop_min]

    if pop_max < faixas_populacao[-1]:
        dados_ano = dados_ano.loc[dados_ano["populacao"] <= pop_max]

    chaves_rk = ["codigo_municipio", "municipio", "uf"]
else:
    chaves_rk = ["uf"]


SIGLAS_UF = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
}


def sigla_uf(valor):
    """Converte o código da UF (ex.: 41) em sigla (ex.: PR).
    Se o valor já for uma sigla, devolve como está."""
    numero = pd.to_numeric(valor, errors="coerce")
    if pd.isna(numero):
        return str(valor).strip()
    return SIGLAS_UF.get(int(numero), str(valor).strip())


def calcular_valor_ranking(dados, chaves):
    """Calcula o indicador selecionado para cada grupo de `chaves`."""
    tipo = info_indicador["tipo"]

    if tipo == "per_capita":
        if indicador_nome in (
            "PIB per capita real",
            "PIB per capita real (US$ de 2023)",
        ):
            coluna_pib_rk = "pib_real_2023"
        else:
            coluna_pib_rk = "pib_nominal_reais"

        validos = dados.dropna(subset=[coluna_pib_rk, "populacao"])

        resultado = (
            validos.groupby(chaves)
            .agg(
                pib_total=(coluna_pib_rk, "sum"),
                populacao_total=("populacao", "sum"),
            )
            .reset_index()
        )
        resultado["valor"] = (
            resultado["pib_total"] / resultado["populacao_total"]
        )

        if indicador_nome == "PIB per capita nominal (US$)":
            cambio_ano = (
                dados["cambio_medio_brl_por_usd"].dropna().iloc[0]
            )
            resultado["valor"] = resultado["valor"] / cambio_ano

        elif indicador_nome == "PIB per capita real (US$ de 2023)":
            cambio_base = base.loc[
                base["ano"] == 2023, "cambio_medio_brl_por_usd"
            ].dropna().iloc[0]
            resultado["valor"] = resultado["valor"] / cambio_base

    elif tipo == "percentual":
        componentes_rk = {
            "Participação da agropecuária": [
                "vab_agropecuaria_mil_reais",
            ],
            "Participação da indústria": [
                "vab_industria_mil_reais",
            ],
            "Participação dos serviços": [
                "vab_servicos_mil_reais",
            ],
            "Participação total dos serviços": [
                "vab_servicos_mil_reais",
                "vab_administracao_publica_mil_reais",
            ],
        }
        colunas_setor = componentes_rk[indicador_nome]
        colunas_nec = ["vab_total_mil_reais", *colunas_setor]

        validos = dados.dropna(subset=colunas_nec)

        resultado = (
            validos.groupby(chaves)[colunas_nec].sum().reset_index()
        )
        resultado["valor"] = (
            resultado[colunas_setor].sum(axis=1)
            / resultado["vab_total_mil_reais"]
            * 100
        )

    else:
        if info_indicador["agregacao"] == "sum":
            funcao = lambda s: s.sum(min_count=1)
        else:
            funcao = info_indicador["agregacao"]

        resultado = (
            dados.groupby(chaves)[coluna_indicador]
            .agg(funcao)
            .reset_index()
            .rename(columns={coluna_indicador: "valor"})
        )

        if (
            tipo == "pib_total"
            and coluna_indicador not in (
                "pib_nominal_usd_milhoes",
                "pib_real_usd_2023_milhoes",
            )
        ):
            resultado["valor"] = resultado["valor"] / 1_000_000
        elif tipo == "vab_total":
            resultado["valor"] = resultado["valor"] / 1_000
        elif tipo == "fiscal_total":
            resultado["valor"] = resultado["valor"] / 1_000_000

    return resultado[chaves + ["valor"]].dropna(subset=["valor"])


if dados_ano.empty:
    st.info("Nenhum registro encontrado para os filtros do ranking.")
else:
    ranking = calcular_valor_ranking(dados_ano, chaves_rk)

    # População do grupo (soma), para exibir na tabela
    populacao_grupo = (
        dados_ano.groupby(chaves_rk)["populacao"]
        .sum(min_count=1)
        .rename("populacao")
        .reset_index()
    )
    ranking = ranking.merge(populacao_grupo, on=chaves_rk, how="left")

    # Nome do estado a partir da UF
    mapa_uf_nome = (
        base.dropna(subset=["estado"])
        .assign(uf_limpa=lambda d: d["uf"].astype(str).str.strip())
        .drop_duplicates("uf_limpa")
        .set_index("uf_limpa")["estado"]
    )

    if nivel_ranking == "Estados":
        ranking["nome"] = (
            ranking["uf"].astype(str).str.strip().map(mapa_uf_nome)
            .fillna(ranking["uf"].astype(str))
        )
    else:
        ranking["nome"] = (
            ranking["municipio"]
            + " ("
            + ranking["uf"].map(sigla_uf)
            + ")"
        )

    # Posição considerando TODOS os grupos, antes de cortar o Top N
    crescente = ordem_ranking == "Menores valores"
    ranking = ranking.sort_values(
        "valor", ascending=crescente
    ).reset_index(drop=True)
    ranking["posicao"] = ranking.index + 1
    total_ranking = len(ranking)

    if ranking.empty:
        st.info("Não há valores disponíveis para este ranking.")
    else:
        # Destaque do município selecionado no filtro principal
        codigo_destaque = None
        if (
            nivel_ranking == "Municípios"
            and municipio_selecionado is not None
        ):
            codigo_destaque = municipio_selecionado[0]
            linha = ranking.loc[
                ranking["codigo_municipio"] == codigo_destaque
            ]
            if not linha.empty:
                st.success(
                    f"{municipio_selecionado[1]} ocupa a posição "
                    f"{int(linha['posicao'].iloc[0])} de {total_ranking} "
                    f"em {ano_ranking}."
                )
            else:
                st.info(
                    f"{municipio_selecionado[1]} não está neste ranking "
                    "(sem dado ou fora dos filtros)."
                )

        topo = ranking.head(quantidade_ranking).copy()

        if codigo_destaque is not None:
            topo["destaque"] = (
                topo["codigo_municipio"] == codigo_destaque
            ).map({True: "Selecionado", False: "Demais"})
            cor = "destaque"
            mapa_cores = {
                "Selecionado": "#E4572E",
                "Demais": "#4C78A8",
            }
        else:
            cor = None
            mapa_cores = None

        rotulo_nivel = (
            "Município" if nivel_ranking == "Municípios" else "Estado"
        )

        fig_rank = px.bar(
            topo,
            x="valor",
            y="nome",
            orientation="h",
            color=cor,
            color_discrete_map=mapa_cores,
            labels={
                "valor": info_indicador["unidade"],
                "nome": rotulo_nivel,
            },
        )
        fig_rank.update_yaxes(
            autorange="reversed", type="category"
        )
        fig_rank.update_xaxes(
            tickformat=",.2f", separatethousands=True
        )
        fig_rank.update_layout(
            showlegend=False,
            height=max(350, 28 * len(topo) + 120),
        )
        st.plotly_chart(
            fig_rank,
            use_container_width=True,
            config={"locale": "pt-BR"},
        )

        # Tabela do ranking
        def formatar_inteiro(valor):
            if pd.isna(valor):
                return "—"
            return f"{int(valor):,}".replace(",", ".")

        tabela_rank = pd.DataFrame(
            {
                "Posição": topo["posicao"],
                rotulo_nivel: topo["nome"],
                "População": topo["populacao"].apply(formatar_inteiro),
                f"Valor ({info_indicador['unidade']})": topo[
                    "valor"
                ].apply(formatar_numero),
            }
        )

        st.dataframe(
            tabela_rank,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            f"{total_ranking} {nivel_ranking.lower()} com dado em "
            f"{ano_ranking}."
        )

        if (
            info_indicador["tipo"] == "per_capita"
            and nivel_ranking == "Municípios"
        ):
            st.caption(
                "Dica: municípios muito pequenos podem liderar o PIB per "
                "capita por causa de uma única grande atividade. Use a "
                "faixa de população para comparar cidades de porte "
                "semelhante."
            )


# --------------------------------------------------
# 11. Notas metodológicas
# --------------------------------------------------

st.divider()

st.subheader("Sobre os dados")

st.markdown(
    r"""
    - **PIB nominal:** valores correntes de cada ano.
    - **PIB real:** valores ajustados para reais de 2023, conforme a base.
    - **PIB nominal (US\$ milhões):** PIB nominal de cada ano dividido pela cotação média anual do dólar (R\$ por US\$).
    - **PIB real (US\$ milhões de 2023):** PIB real, a preços de 2023, dividido pela cotação média do dólar em 2023.
    - **PIB per capita nominal:** valor corrente por habitante; não é apresentado em milhões.
    - **PIB per capita real:** valor ajustado para reais de 2023 por habitante; não é apresentado em milhões.
    - **PIB per capita nominal (US\$):** valor corrente por habitante dividido pela cotação média anual do dólar; não é apresentado em milhões.
    - **PIB per capita real (US\$ de 2023):** valor real (a preços de 2023) por habitante dividido pela cotação média do dólar em 2023; não é apresentado em milhões.
    - **Emprego formal:** vínculos ativos em 31 de dezembro.
    - **VAB (total e setoriais):** valor adicionado bruto, apresentado em R\$ milhões.
    - **Participações setoriais:** VAB do setor dividido pelo VAB total, em %. A participação total dos serviços soma serviços e administração pública.
    - **Receitas e despesas fiscais:** valores em R\$ milhões, disponíveis para 2020–2023.
    - A disponibilidade temporal varia conforme o indicador e sua fonte.
    """
)

st.markdown(
    "**Fontes:** IBGE (PIB municipal e população), RAIS, "
    "Banco Central do Brasil (IPCA e câmbio), Tesouro Nacional (SICONFI/FINBRA)."
)

if info_indicador["tipo"] == "per_capita":
    st.caption(
        "O PIB per capita de municípios, estados e do Brasil é calculado "
        "dividindo o PIB total do recorte pela sua população total."
    )

st.divider()
st.markdown("**Contato:** otavioc2009@gmail.com")