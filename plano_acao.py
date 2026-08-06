import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
from supabase import create_client, Client

# ── Configuração da página ──────────────────────────────────────
st.set_page_config(
    page_title='Plano de Ação — Portabilidade',
    page_icon='📋',
    layout='wide'
)

# ── Conexão Supabase ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

TABELA = "plano_acao"
DIAS_ESTAGNACAO = 7  # dias sem atualização para virar alerta

# ── Carregar dados ──────────────────────────────────────────────
@st.cache_data(ttl=60)
def carregar_dados():
    resp = supabase.table(TABELA).select("*").execute()
    df = pd.DataFrame(resp.data)

    if df.empty:
        return df

    hoje = pd.Timestamp(date.today())

    df['prazo'] = pd.to_datetime(df['prazo'], errors='coerce')
    df['data_finalizacao'] = pd.to_datetime(df['data_finalizacao'], errors='coerce')
    df['atualizado_em'] = pd.to_datetime(df['atualizado_em'], errors='coerce')

    def calcular_status(row):
        if pd.notna(row['data_finalizacao']):
            return 'Concluído'
        elif pd.notna(row['prazo']) and row['prazo'] < hoje:
            return 'Atrasado'
        else:
            return 'Em andamento'

    df['status_calc'] = df.apply(calcular_status, axis=1)

    def calcular_atraso(row):
        if row['status_calc'] == 'Atrasado':
            return (hoje - row['prazo']).days
        return None

    df['dias_atraso_calc'] = df.apply(calcular_atraso, axis=1)

    # Dias sem atualização (rastreabilidade)
    def dias_sem_atualizacao(row):
        if pd.notna(row['atualizado_em']):
            return (hoje - row['atualizado_em'].normalize()).days
        return None

    df['dias_sem_atualizacao'] = df.apply(dias_sem_atualizacao, axis=1)

    def estagnada(row):
        return (
            row['status_calc'] == 'Em andamento'
            and (pd.isna(row['dias_sem_atualizacao']) or row['dias_sem_atualizacao'] >= DIAS_ESTAGNACAO)
        )

    df['estagnada'] = df.apply(estagnada, axis=1)

    df['prazo_fmt'] = df['prazo'].dt.strftime('%d/%m/%Y').fillna('—')
    df['data_finalizacao_fmt'] = df['data_finalizacao'].dt.strftime('%d/%m/%Y').fillna('—')
    df['atualizado_em_fmt'] = df['atualizado_em'].dt.strftime('%d/%m/%Y %H:%M').fillna('Nunca')

    return df

df = carregar_dados()

# ── Header ──────────────────────────────────────────────────────
st.markdown("""
<div style='background-color:#CC0000;padding:16px 24px;border-radius:10px;margin-bottom:20px;'>
    <h2 style='color:white;margin:0;'>📋 Plano de Ação — Portabilidade</h2>
    <p style='color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:13px;'>
        Conectado ao Supabase · Atualizado em {data}
    </p>
</div>
""".format(data=datetime.today().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)

if df.empty:
    st.warning("Nenhum registro encontrado na tabela.")
    st.stop()

# ── Cards de resumo ─────────────────────────────────────────────
total = len(df)
concluidas = len(df[df['status_calc'] == 'Concluído'])
atrasadas = len(df[df['status_calc'] == 'Atrasado'])
andamento = len(df[df['status_calc'] == 'Em andamento'])
estagnadas = df['estagnada'].sum()
taxa = round(concluidas / total * 100, 1) if total > 0 else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('Total de Ações', total)
c2.metric('✅ Concluídas', concluidas)
c3.metric('⚠️ Atrasadas', atrasadas)
c4.metric('🔄 Em andamento', andamento)
c5.metric('🕒 Estagnadas', int(estagnadas))
c6.metric('📈 Taxa de Conclusão', f'{taxa}%')

st.divider()

# ── Filtros ─────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    responsaveis = ['Todos'] + sorted(df['responsavel'].dropna().unique().tolist())
    filtro_resp = st.selectbox('👤 Responsável', responsaveis)

with col_f2:
    status_opts = ['Todos'] + sorted(df['status_calc'].unique().tolist())
    filtro_status = st.selectbox('📌 Status', status_opts)

with col_f3:
    busca = st.text_input('🔍 Buscar por palavra-chave')

df_filtrado = df.copy()
if filtro_resp != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['responsavel'] == filtro_resp]
if filtro_status != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['status_calc'] == filtro_status]
if busca:
    df_filtrado = df_filtrado[
        df_filtrado['problema_identificado'].str.contains(busca, case=False, na=False) |
        df_filtrado['plano_de_acao'].str.contains(busca, case=False, na=False)
    ]

st.caption(f'Exibindo {len(df_filtrado)} de {total} ações')

st.divider()

# ── Gráficos ─────────────────────────────────────────────────────
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader('Status das Ações')
    contagem = df['status_calc'].value_counts().reset_index()
    contagem.columns = ['Status', 'Qtde']
    cores = {'Concluído': '#4CAF50', 'Atrasado': '#CC0000', 'Em andamento': '#FF9800'}
    fig1 = px.pie(contagem, values='Qtde', names='Status',
                  color='Status', color_discrete_map=cores, hole=0.4)
    fig1.update_traces(textinfo='label+value+percent')
    fig1.update_layout(margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col_g2:
    st.subheader('Top 10 Responsáveis por Ações')
    top_resp = df.groupby('responsavel').size().sort_values(ascending=True).tail(10)
    fig2 = px.bar(top_resp, orientation='h', color_discrete_sequence=['#CC0000'])
    fig2.update_layout(margin=dict(t=10, b=10), xaxis_title='Qtde de Ações',
                        yaxis_title='', showlegend=False)
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
    'numero', 'responsavel', 'problema_identificado', 'plano_de_acao',
    'prazo_fmt', 'data_finalizacao_fmt', 'status_calc', 'dias_atraso_calc',
    'atualizado_em_fmt', 'atualizado_por'
]].rename(columns={
    'numero': 'Número', 'responsavel': 'Responsável',
    'problema_identificado': 'Problema', 'plano_de_acao': 'Plano de Ação',
    'prazo_fmt': 'Prazo', 'data_finalizacao_fmt': 'Finalização',
    'status_calc': 'Status', 'dias_atraso_calc': 'Dias Atraso',
    'atualizado_em_fmt': 'Última Atualização', 'atualizado_por': 'Atualizado Por'
})

styled_table = tabela.style.map(colorir_status, subset=['Status'])
st.write(styled_table)

st.divider()

# ── Editar uma ação ───────────────────────────────────────────────
st.subheader('✏️ Atualizar uma Ação')

opcoes = df.apply(lambda r: f"#{r['numero']} — {r['responsavel']} — {str(r['problema_identificado'])[:50]}", axis=1)
mapa_opcoes = dict(zip(opcoes, df['id']))

escolha = st.selectbox('Selecione a ação', ['—'] + opcoes.tolist())

if escolha != '—':
    acao_id = mapa_opcoes[escolha]
    linha = df[df['id'] == acao_id].iloc[0]

    with st.form('form_editar'):
        col1, col2 = st.columns(2)
        with col1:
            novo_comentario = st.text_area('Comentário / Andamento', value=linha.get('comentario') or '')
            novo_responsavel = st.text_input('Responsável', value=linha.get('responsavel') or '')
        with col2:
            nova_data_final = st.date_input(
                'Data de Finalização (deixe vazio se ainda não concluído)',
                value=linha['data_finalizacao'].date() if pd.notna(linha['data_finalizacao']) else None
            )
            quem_atualizou = st.text_input('Seu nome (quem está atualizando)')

        enviado = st.form_submit_button('💾 Salvar Atualização')

        if enviado:
            if not quem_atualizou.strip():
                st.error('Informe seu nome antes de salvar.')
            else:
                update_data = {
                    'comentario': novo_comentario,
                    'responsavel': novo_responsavel,
                    'atualizado_em': datetime.now().isoformat(),
                    'atualizado_por': quem_atualizou.strip(),
                }
                if nova_data_final:
                    update_data['data_finalizacao'] = nova_data_final.isoformat()

                supabase.table(TABELA).update(update_data).eq('id', acao_id).execute()
                st.success('Ação atualizada com sucesso!')
                st.cache_data.clear()
                st.rerun()

st.divider()

# ── Alertas de ações atrasadas ───────────────────────────────────
atrasadas_df = df[df['status_calc'] == 'Atrasado'].sort_values('dias_atraso_calc', ascending=False)
if len(atrasadas_df) > 0:
    st.subheader('🚨 Ações Atrasadas')
    for _, row in atrasadas_df.iterrows():
        st.error(
            f"*#{row['numero']} | {row['responsavel']}* — "
            f"{str(row['problema_identificado'])[:80]}... "
            f"| Prazo: {row['prazo_fmt']} | *{int(row['dias_atraso_calc'])} dias de atraso*"
        )

# ── Alertas de ações estagnadas (novo) ────────────────────────────
estagnadas_df = df[df['estagnada']].sort_values('dias_sem_atualizacao', ascending=False, na_position='first')
if len(estagnadas_df) > 0:
    st.subheader(f'🕒 Ações Estagnadas (sem atualização há {DIAS_ESTAGNACAO}+ dias)')
    st.caption('Estão "em andamento", dentro do prazo, mas ninguém mexeu recentemente.')
    for _, row in estagnadas_df.iterrows():
        dias_txt = f"{int(row['dias_sem_atualizacao'])} dias" if pd.notna(row['dias_sem_atualizacao']) else "nunca atualizada"
        st.warning(
            f"*#{row['numero']} | {row['responsavel']}* — "
            f"{str(row['problema_identificado'])[:80]}... "
            f"| Última atualização: *{dias_txt}*"
        )
