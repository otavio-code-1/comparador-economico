
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px


# --------------------------------------------------
# 1. Configuração da página
# --------------------------------------------------

st.set_page_config(
    page_title="Comparador Econômico",
    page_icon="📊",
    layout="wide",
)

st.title("Comparador Econômico")
st.write(
    "Compare indicadores econômicos dos municípios brasileiros "
    "ao longo do tempo."
)


# --------------------------------------------------
# 2. Carregamento da base de dados
# --------------------------------------------------

CAMINHO_BASE = (
    Path(__file__).resolve().parents[1]
    / "dados"
    / "base_economica_municipal_2010_2023_v3.csv"
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
        "coluna": "participacao_servicos_total_pct",
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

if ufs_selecionadas is None:
    municipios_filtrados = base[
        ["codigo_municipio", "municipio"]
    ].drop_duplicates()
else:
    municipios_filtrados = base.loc[
        base["uf"].astype(str).str.strip().isin(ufs_selecionadas),
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

col_inicio, col_fim = st.columns(2)

anos_disponiveis = sorted(base["ano"].unique().tolist())

with col_inicio:
    ano_inicio = st.selectbox(
        "Ano inicial",
        options=anos_disponiveis,
        index=0,
    )

with col_fim:
    ano_fim = st.selectbox(
        "Ano final",
        options=anos_disponiveis,
        index=len(anos_disponiveis) - 1,
    )

if ano_inicio > ano_fim:
    st.warning("O ano inicial deve ser menor ou igual ao ano final.")
    st.stop()


# --------------------------------------------------
# 6. Aplicação dos filtros
# --------------------------------------------------

consulta = base.loc[
    base["ano"].between(ano_inicio, ano_fim)
].copy()

if ufs_selecionadas is not None:
    consulta = consulta.loc[
        consulta["uf"].astype(str).str.strip().isin(ufs_selecionadas)
    ]

if municipio_selecionado is not None:
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
    st.info("Não foram encontrados dados para os filtros selecionados.")
    st.stop()


# --------------------------------------------------
# 7. Preparação do gráfico e da tabela
# --------------------------------------------------

if info_indicador["tipo"] == "per_capita":

    # Identifica qual PIB usar no cálculo agregado
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
        dados_validos.groupby("ano")
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

    dados_grafico = dados_grafico[["ano", "valor"]]

else:

    # Calcula as participações setoriais usando os valores agregados
    if info_indicador["tipo"] == "percentual":

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
            dados_validos.groupby("ano")[colunas_necessarias]
            .sum()
            .reset_index()
        )

        # Participação = VAB do setor / VAB total × 100
        dados_grafico["valor"] = (
            dados_grafico[colunas_setoriais].sum(axis=1)
            / dados_grafico["vab_total_mil_reais"]
            * 100
        )

        dados_grafico = dados_grafico[["ano", "valor"]]

    else:

        # Agrega os demais indicadores por ano
        dados_grafico = (
            consulta.groupby("ano")[coluna_indicador]
            .agg(info_indicador["agregacao"])
            .reset_index()
            .rename(columns={coluna_indicador: "valor"})
        )

        # Converte PIB total em reais para milhões de reais.
        # Os indicadores em dólares já estão em milhões de dólares.
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

        # O VAB setorial está originalmente em mil reais.
        # Para exibir em milhões de reais, divide-se por mil.
        elif info_indicador["tipo"] == "vab_total":
            dados_grafico["valor"] = (
                dados_grafico["valor"] / 1_000
            )

# Remove observações sem valor
dados_grafico = dados_grafico.dropna(subset=["valor"])

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
    )

    # Formato numérico brasileiro nos valores do tooltip:
    # 91.968,328
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
        hoverlabel=dict(
            namelength=-1,
        ),
    )

    # Aplica separadores brasileiros aos números do eixo
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

tabela = dados_grafico.copy()
tabela = tabela.rename(
    columns={
        "ano": "Ano",
        "valor": f"Valor ({info_indicador['unidade']})",
    }
)

coluna_valor = f"Valor ({info_indicador['unidade']})"


def formatar_numero(valor):
    if pd.isna(valor):
        return "—"

    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", "."
    )


tabela[coluna_valor] = tabela[coluna_valor].apply(formatar_numero)

st.dataframe(
    tabela,
    use_container_width=True,
    hide_index=True,
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
# 11. Notas metodológicas
# --------------------------------------------------

st.divider()

st.subheader("Sobre os dados")

st.markdown(
    """
    - **PIB nominal:** valores correntes de cada ano.
    - **PIB real:** valores ajustados para reais de 2023, conforme a base.
    - **PIB per capita:** valor por habitante; não é apresentado em milhões.
    - **População:** número de habitantes.
    - **Emprego formal:** vínculos ativos em 31 de dezembro.
    - A disponibilidade temporal varia conforme o indicador e sua fonte.
    """
)

if info_indicador["tipo"] == "per_capita" and (
    estado_selecionado == "Todos" and municipio_selecionado is None
):
    st.caption(
        "No gráfico nacional, o PIB per capita representa a média simples "
        "dos valores municipais disponíveis, e não o PIB per capita "
        "calculado pela divisão do PIB nacional pela população nacional."
    )
