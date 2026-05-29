import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import os

ARQUIVO = 'plano_acao.xlsx'
ABA = 'Base'

st.set_page_config(page_title='Plano de Ação — Portabilidade', page_icon='📋', layout='wide')

# ── Carregar dados ───────────────────────────────────────────
@st.cache_data(ttl=30)
def carregar_dados():
    df = pd.read_excel(ARQUIVO, sheet_name=ABA)
    hoje = pd.Timestamp(date.today())

    def calcular_status(row):
        if pd.notna(row['Data Finalização']):
            return 'Concluído'
        elif pd.notna(row['Prazo']) and row['Prazo'] < hoje:
            return 'Atrasado'
        else:
            return 'Em andamento'

    def calcular_atraso(row):
        if row['Status'] == 'Atrasado':
            return (hoje - row['Prazo']).days
        return None

    df['Status'] = df.apply(calcular_status, axis=1)
    df['Dias Atraso'] = df.apply(calcular_atraso, axis=1)
    df['Prazo_fmt'] = df['Prazo'].dt.strftime('%d/%m/%Y')
    df['Data Finalização_fmt'] = df['Data Finalização'].dt.strftime('%d/%m/%Y').fillna('—')

    # Garante coluna de comentário
    if 'Comentário' not in df.columns:
        df['Comentário'] = ''

    return df

def salvar_atualizacao(numero, novo_status, comentario, data_fin):
    wb = load_workbook(ARQUIVO)
    ws = wb[ABA]

    # Acha os índices das colunas
    headers = {cell.value: cell.column for cell in ws[1]}
    col_status = headers.get('Status')
    col_comentario = headers.get('Comentário')
    col_data_fin = headers.get('Data Finalização')
    col_numero = headers.get('Número')

    # Se coluna Comentário não existe, cria
    if not col_comentario:
        col_comentario = ws.max_column + 1
        ws.cell(row=1, column=col_comentario, value='Comentário')

    # Acha a linha do número
    for row in ws.iter_rows(min_row=2):
        if row[col_numero - 1].value == numero:
            if col_status:
                row[col_status - 1].value = novo_status
            row[col_comentario - 1].value = comentario
            if col_data_fin and novo_status == 'Concluído':
                row[col_data_fin - 1].value = data_fin
            break

    wb.save(ARQUIVO)
    st.cache_data.clear()

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div style='background:#CC0000;padding:16px 24px;border-radius:10px;margin-bottom:20px;'>
    <h2 style='color:white;margin:0;'>📋 Plano de Ação — Portabilidade</h2>
    <p style='color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:13px;'>
        Atualizado automaticamente · {data}
    </p>
</div>
""".format(data=datetime.today().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)

df = carregar_dados()

# ── Cards ─────────────────────────────────────────────────────
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

# ── SEÇÃO DE ATUALIZAÇÃO ─────────────────────────────────────
st.subheader('✏️ Atualizar status de uma ação')

col_resp, col_acao = st.columns([1, 2])

with col_resp:
    responsaveis = sorted(df['Responsável'].dropna().unique().tolist())
    resp_sel = st.selectbox('👤 Selecione seu nome', ['— Selecione —'] + responsaveis)

if resp_sel != '— Selecione —':
    acoes_resp = df[df['Responsável'] == resp_sel][
        ['Número', 'Problema Identificado', 'Status', 'Prazo_fmt', 'Comentário']
    ]

    with col_acao:
        opcoes = [
            f"#{row['Número']} — {str(row['Problema Identificado'])[:60]}..."
            for _, row in acoes_resp.iterrows()
        ]
        acao_sel = st.selectbox('📌 Selecione a ação', ['— Selecione —'] + opcoes)

    if acao_sel != '— Selecione —':
        num = int(acao_sel.split('—')[0].replace('#','').strip())
        acao_atual = acoes_resp[acoes_resp['Número'] == num].iloc[0]

        st.markdown(f"""
        <div style='background:#F9F9F9;border-left:4px solid #CC0000;padding:12px 16px;
                    border-radius:0 8px 8px 0;margin:10px 0;'>
            <strong>Ação #{num}</strong> — {acao_atual['Problema Identificado']}<br>
            <span style='font-size:12px;color:#888;'>Prazo: {acao_atual['Prazo_fmt']} · Status atual: <strong>{acao_atual['Status']}</strong></span>
        </div>
        """, unsafe_allow_html=True)

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            novo_status = st.selectbox(
                '📌 Novo status',
                ['Em andamento', 'Concluído', 'Atrasado'],
                index=['Em andamento', 'Concluído', 'Atrasado'].index(acao_atual['Status'])
                if acao_atual['Status'] in ['Em andamento', 'Concluído', 'Atrasado'] else 0
            )

        with col_s2:
            data_fin = None
            if novo_status == 'Concluído':
                data_fin = st.date_input('📅 Data de finalização', value=date.today())

        comentario = st.text_area(
            '💬 Comentário / justificativa',
            value=str(acao_atual['Comentário']) if pd.notna(acao_atual['Comentário']) else '',
            placeholder='Ex: Ação concluída após alinhamento com a equipe de TI...',
            height=100
        )

        if st.button('💾 Salvar atualização', type='primary'):
            salvar_atualizacao(num, novo_status, comentario, data_fin)
            st.success(f'✅ Ação #{num} atualizada com sucesso!')
            st.rerun()

st.divider()

# ── Filtros ──────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    filtro_resp = st.selectbox('👤 Filtrar por responsável',
                               ['Todos'] + sorted(df['Responsável'].dropna().unique().tolist()))
with col_f2:
    filtro_status = st.selectbox('📌 Filtrar por status',
                                 ['Todos'] + sorted(df['Status'].unique().tolist()))
with col_f3:
    busca = st.text_input('🔍 Buscar por palavra-chave')

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

# ── Gráficos ─────────────────────────────────────────────────
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader('Status das Ações')
    contagem = df_filtrado['Status'].value_counts().reset_index()
    contagem.columns = ['Status', 'Qtde']
    cores = {'Concluído': '#4CAF50', 'Atrasado': '#CC0000', 'Em andamento': '#FF9800'}
    fig1 = px.pie(contagem, values='Qtde', names='Status',
                  color='Status', color_discrete_map=cores, hole=0.4)
    fig1.update_traces(textinfo='label+value+percent')
    fig1.update_layout(margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col_g2:
    st.subheader('Top Responsáveis por Ações')
    top_resp = df_filtrado.groupby('Responsável').size().sort_values(ascending=True).tail(10)
    fig2 = px.bar(top_resp, orientation='h', color_discrete_sequence=['#CC0000'])
    fig2.update_layout(margin=dict(t=10, b=10), xaxis_title='Qtde', yaxis_title='', showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Tabela ───────────────────────────────────────────────────
st.subheader('📋 Ações Detalhadas')

def colorir_status(val):
    if val == 'Concluído': return 'background-color:#E8F5E9;color:#2E7D32'
    elif val == 'Atrasado': return 'background-color:#FFEBEE;color:#C62828;font-weight:bold'
    elif val == 'Em andamento': return 'background-color:#FFF3E0;color:#E65100'
    return ''

tabela = df_filtrado[[
    'Número','Responsável','Problema Identificado',
    'Plano de Ação','Prazo_fmt','Data Finalização_fmt','Status','Dias Atraso','Comentário'
]].rename(columns={'Prazo_fmt':'Prazo','Data Finalização_fmt':'Finalizado em'})

st.dataframe(
    tabela.style.applymap(colorir_status, subset=['Status']),
    use_container_width=True, hide_index=True, height=400
)

st.divider()

# ── Alertas ──────────────────────────────────────────────────
atrasadas_df = df[df['Status'] == 'Atrasado'].sort_values('Dias Atraso', ascending=False)
if len(atrasadas_df) > 0:
    st.subheader('🚨 Ações Atrasadas')
    for _, row in atrasadas_df.iterrows():
        st.error(
            f"*#{row['Número']} | {row['Responsável']}* — "
            f"{str(row['Problema Identificado'])[:80]}... "
            f"| Prazo: {row['Prazo_fmt']} | *{int(row['Dias Atraso'])} dias de atraso*"
        )
