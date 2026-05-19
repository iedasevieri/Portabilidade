import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

# ── Configuração da página ──────────────────────────────────────
st.set_page_config(
    page_title='Plano de Ação — Portabilidade',
    page_icon='📋',
    layout='wide'
)

# ── Carregar dados ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def carregar_dados():
    df = pd.read_excel('plano_acao.xlsx', sheet_name='🗂 Base')
    hoje = pd.Timestamp(date.today())

    # Recalcula status automaticamente
    def calcular_status(row):
        if pd.notna(row['Data Finalização']):
            return 'Concluído'
        elif pd.notna(row['Prazo']) and row['Prazo'] < hoje:
            return 'Atrasado'
        else:
            return 'Em andamento'

    df['Status'] = df.apply(calcular_status, axis=1)

    # Dias de atraso recalculado
    def calcular_atraso(row):
        if row['Status'] == 'Atrasado':
            return (hoje - row['Prazo']).days
        return None

    df['Dias Atraso'] = df.apply(calcular_atraso, axis=1)
    df['Prazo_fmt'] = df['Prazo'].dt.strftime('%d/%m/%Y')
    df['Data Finalização_fmt'] = df['Data Finalização'].dt.strftime('%d/%m/%Y').fillna('—')

    return df

df = carregar_dados()

# ── Header ──────────────────────────────────────────────────────
st.markdown("""
<div style='background-color:#CC0000;padding:16px 24px;border-radius:10px;margin-bottom:20px;'>
    <h2 style='color:white;margin:0;'>📋 Plano de Ação — Portabilidade</h2>
    <p style='color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:13px;'>
        Atualizado automaticamente · {data}
    </p>
</div>
""".format(data=datetime.today().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)

# ── Cards de resumo ─────────────────────────────────────────────
total = len(df)
concluidas = len(df[df['Status'] == 'Concluído'])
atrasadas = len(df[df['Status'] == 'Atrasado'])
andamento = len(df[df['Status'] == 'Em andamento'])
taxa = round(concluidas / total * 100, 1) if total > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('Total de Ações', total)
c2.metric('✅ Concluídas', concluidas)
c3.metric('⚠️ Atrasadas', atrasadas, delta=f'-{atrasadas}', delta_color='inverse')
c4.metric('🔄 Em andamento', andamento)
c5.metric('📈 Taxa de Conclusão', f'{taxa}%')

st.divider()

# ── Filtros ─────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    responsaveis = ['Todos'] + sorted(df['Responsável'].dropna().unique().tolist())
    filtro_resp = st.selectbox('👤 Responsável', responsaveis)

with col_f2:
    status_opts = ['Todos'] + sorted(df['Status'].unique().tolist())
    filtro_status = st.selectbox('📌 Status', status_opts)

with col_f3:
    busca = st.text_input('🔍 Buscar por palavra-chave')

# Aplicar filtros
df_filtrado = df.copy()
if filtro_resp != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Responsável'] == filtro_resp]
if filtro_status != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['Status'] == filtro_status]
if busca:
    df_filtrado = df_filtrado[
        df_filtrado['Problema Identificado'].str.contains(busca, case=False, na=False) |
        df_filtrado['Plano de Ação'].str.contains(busca, case=False, na=False)
    ]

st.caption(f'Exibindo {len(df_filtrado)} de {total} ações')

st.divider()

# ── Gráficos ─────────────────────────────────────────────────────
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader('Status das Ações')
    contagem = df['Status'].value_counts().reset_index()
    contagem.columns = ['Status', 'Qtde']
    cores = {'Concluído': '#4CAF50', 'Atrasado': '#CC0000', 'Em andamento': '#FF9800'}
    fig1 = px.pie(contagem, values='Qtde', names='Status',
                  color='Status', color_discrete_map=cores, hole=0.4)
    fig1.update_traces(textinfo='label+value+percent')
    fig1.update_layout(margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col_g2:
    st.subheader('Top 10 Responsáveis por Ações')
    top_resp = df.groupby('Responsável').size().sort_values(ascending=True).tail(10)
    fig2 = px.bar(top_resp, orientation='h',
                  color_discrete_sequence=['#CC0000'])
    fig2.update_layout(margin=dict(t=10, b=10),
                       xaxis_title='Qtde de Ações',
                       yaxis_title='',
                       showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Tabela principal ─────────────────────────────────────────────
st.subheader('📋 Ações Detalhadas')

def colorir_status(val):
    if val == 'Concluído':
        return 'background-color: #E8F5E9; color: #2E7D32'
    elif val == 'Atrasado':
        return 'background-color: #FFEBEE; color: #C62828; font-weight:bold'
    elif val == 'Em andamento':
        return 'background-color: #FFF3E0; color: #E65100'
    return ''

tabela = df_filtrado[[
    'Número', 'Responsável', 'Problema Identificado',
    'Plano de Ação', 'Prazo_fmt', 'Data Finalização_fmt',
    'Status', 'Dias Atraso'
]].rename(columns={
    'Prazo_fmt': 'Prazo',
    'Data Finalização_fmt': 'Finalizado em',
    'Dias Atraso': 'Dias Atraso'
})

styled_table = tabela.style.map(
    colorir_status,
    subset=['Status']
)

st.write(styled_table)



st.divider()

# ── Alertas de ações atrasadas ───────────────────────────────────
atrasadas_df = df[df['Status'] == 'Atrasado'].sort_values('Dias Atraso', ascending=False)
if len(atrasadas_df) > 0:
    st.subheader('🚨 Ações Atrasadas')
    for _, row in atrasadas_df.iterrows():
        st.error(
            f"**#{row['Número']} | {row['Responsável']}** — "
            f"{str(row['Problema Identificado'])[:80]}... "
            f"| Prazo: {row['Prazo_fmt']} | **{int(row['Dias Atraso'])} dias de atraso**"
        )
        