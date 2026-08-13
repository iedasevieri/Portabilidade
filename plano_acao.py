import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from supabase import create_client, Client
from exportar_ppt import gerar_ppt

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
TABELA_ACOMP = "acompanhamento_semanal"
DIAS_ESTAGNACAO = 7  # dias sem atualização para virar alerta

# ── Timeline (fixo no código — atualizar manualmente conforme novos marcos) ──
TIMELINE_EVENTOS = {
    "Maio": [
        {
            "data": "06/05/2026",
            "titulo": "Instabilidade sistêmica SAP",
            "corpo": (
                "Após migração do SAP, houve abertura recorrente de CCARDs de erro "
                "para validação de inconsistências sistêmicas, com impacto direto nas vendas.\n\n"
                "Foi destacado que, apesar da efetivação da venda, não havia visibilidade por canal, "
                "impossibilitando o reflexo correto para os times comerciais.\n\n"
                "Em acompanhamento por Amanda e Cícera."
            ),
        },
    ],
    "Junho": [
        {
            "data": "01/06/2026",
            "titulo": "Portabilidade Indevida — Flex",
            "corpo": (
                "Aumento de reclamações relacionadas à sobreposição de números, principalmente "
                "em clientes multilinhas, com perda de linhas ativas.\n\n"
                "**Tratativa em andamento:** Ajuste no app (Flex). Implementação de pop-up/alerta "
                "de confirmação na jornada de portabilidade, com bloqueio para inconsistências "
                "(ex: número já ativo).\n\n"
                "- **Previsão de implantação:** 30/06/26\n"
                "- **Previsão de correção postergada para 15/09**, pois em 18/08 entrará em produção "
                "o Novo Plano Flex, não pode subir em produção em conjunto."
            ),
        },
        {
            "data": "06/06/2026",
            "titulo": "Portin interno Nucel > Claro — Não ativo na Claro",
            "corpo": (
                "Identificação de linhas portadas que não estavam ativas corretamente na base Claro, "
                "assim o cliente portado estava ficando sem serviço.\n\n"
                "**Tratativas:**\n"
                "1. Ajustar a implementação do canal SMS 1970 para garantir a validação do chip Claro "
                "no fluxo de portabilidade — **implementado dia 25/06/26**\n"
                "2. Criar job de suspensão para solucionar linhas sem serviço:\n"
                "   - Job de suspensão previsto para 27/06\n"
                "   - Job de suspensão postergado para o dia 04/07. Decisão executiva, devido a alguns "
                "incidentes que ocorreram no MVNO.\n"
                "   - Job de suspensão: Implantação 06/07\n"
                "   - Job de suspensão desligado dia 16/07, pois não estava gerando protocolo no PS8. "
                "Precisa aguardar correção do PS8 para gerar protocolo de conflito. Além disso, alguns "
                "casos não chegam a concluir a portabilidade, devido à falta de estrutura."
            ),
        },
        {
            "data": "09/06/2026",
            "titulo": "Template envio WhatsApp para aceite do SMS",
            "corpo": (
                "**28/05/2026:** Criação de novo Template para aceite do SMS.\n\n"
                "**09/06/2026:** Relatórios de disparo de SMS estavam vindo zerados ou sem dados. "
                "O time Blip confirmou que não há registro de disparos dos novos templates no período, "
                "indicando possível falha na execução da jornada ou integração entre sistemas, com "
                "risco de impacto na conversão da portabilidade.\n\n"
                "**Implementação dia 28/06.**"
            ),
        },
    ],
}

STATUS_OPCOES = ['Em andamento', 'Atrasado', 'Concluído']
TIPO_OPCOES = ['Investigação/Acompanhamento', 'Antigo', 'Sistema', 'Melhoria de Processo']

STATUS_CORES = {'Em andamento': '#FF9800', 'Atrasado': '#CC0000', 'Concluído': '#4CAF50'}
STATUS_ICONES = {'Em andamento': '🔄', 'Atrasado': '🚨', 'Concluído': '✅'}

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
    df['atualizado_em'] = pd.to_datetime(df['atualizado_em'], errors='coerce', utc=True).dt.tz_localize(None)

    # Status calculado automaticamente a partir das datas (fallback)
    def calcular_status(row):
        if pd.notna(row['data_finalizacao']):
            return 'Concluído'
        elif pd.notna(row['prazo']) and row['prazo'] < hoje:
            return 'Atrasado'
        else:
            return 'Em andamento'

    df['status_calc'] = df.apply(calcular_status, axis=1)

    # Status "oficial": o que foi definido manualmente tem prioridade;
    # se nunca foi definido (ou tem grafia diferente), usa o calculado pelas datas
    def normalizar_status(val):
        if pd.isna(val) or not str(val).strip():
            return None
        v = str(val).strip().lower()
        if 'conclu' in v:
            return 'Concluído'
        if 'atras' in v:
            return 'Atrasado'
        if 'andam' in v:
            return 'Em andamento'
        return None

    if 'status' in df.columns:
        df['status_exibicao'] = df['status'].apply(normalizar_status)
        df['status_exibicao'] = df['status_exibicao'].fillna(df['status_calc'])
    else:
        df['status_exibicao'] = df['status_calc']

    # Atraso de prazo (independente do status manual escolhido)
    def calcular_atraso(row):
        if pd.notna(row['prazo']) and row['prazo'] < hoje and pd.isna(row['data_finalizacao']):
            return (hoje - row['prazo']).days
        return None

    df['dias_atraso_calc'] = df.apply(calcular_atraso, axis=1)
    df['dias_atraso_calc'] = pd.to_numeric(
    df['dias_atraso_calc'],
    errors='coerce'
).astype('Int64')

    # Dias sem atualização (rastreabilidade)
    def dias_sem_atualizacao(row):
        if pd.notna(row['atualizado_em']):
            return (hoje - row['atualizado_em'].normalize()).days
        return None

    df['dias_sem_atualizacao'] = df.apply(dias_sem_atualizacao, axis=1)

    def estagnada(row):
        return (
            row['status_exibicao'] == 'Em andamento'
            and (pd.isna(row['dias_sem_atualizacao']) or row['dias_sem_atualizacao'] >= DIAS_ESTAGNACAO)
        )

    df['estagnada'] = df.apply(estagnada, axis=1)

    if 'tipo' not in df.columns:
        df['tipo'] = None

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

# ── Timeline ────────────────────────────────────────────────────
with st.expander('🗓️ Timeline', expanded=True):
    st.markdown(
        "<h1 style='color:#CC0000;font-weight:800;margin:0 0 8px;'>Timeline</h1>"
        "<div style='height:5px;background-color:#CC0000;border-radius:2px;margin-bottom:20px;'></div>",
        unsafe_allow_html=True
    )
    colunas_meses = st.columns(len(TIMELINE_EVENTOS))
    for col, (mes, eventos) in zip(colunas_meses, TIMELINE_EVENTOS.items()):
        with col:
            st.markdown(
                f"<div style='text-align:center;font-weight:700;letter-spacing:1px;"
                f"color:#333;margin-bottom:14px;'>{mes.upper()}</div>",
                unsafe_allow_html=True
            )
            for ev in eventos:
                st.markdown(
                    f"<div style='color:#CC0000;font-size:12px;font-weight:700;margin-bottom:2px;'>"
                    f"● {ev['data']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(f"**{ev['titulo']}**")
                st.markdown(ev['corpo'])
                st.markdown("<div style='margin-bottom:22px;'></div>", unsafe_allow_html=True)

st.divider()

# ── Ações em Acompanhamento na Semana (lista manual) ───────────────
@st.cache_data(ttl=60)
def carregar_acompanhamento():
    resp = supabase.table(TABELA_ACOMP).select("*").execute()
    dfa = pd.DataFrame(resp.data)
    if not dfa.empty:
        dfa['semana_referencia'] = pd.to_datetime(dfa['semana_referencia'], errors='coerce')
        dfa['criado_em'] = pd.to_datetime(dfa['criado_em'], errors='coerce', utc=True).dt.tz_localize(None)
    return dfa

st.subheader('🗓️ Ações em Acompanhamento na Semana')
st.caption('Lista manual, cadastrada semana a semana — independente do status das ações do plano de ação.')

hoje_d = date.today()
col_sem1, col_sem2 = st.columns([1, 3])
with col_sem1:
    dia_ref_semana = st.date_input('Semana de referência', value=hoje_d, key='semana_ref_input')
segunda_semana = dia_ref_semana - timedelta(days=dia_ref_semana.weekday())
domingo_semana = segunda_semana + timedelta(days=6)
with col_sem2:
    st.markdown(
        f"<div style='padding-top:28px;color:#555;'>Semana de "
        f"<b>{segunda_semana.strftime('%d/%m/%Y')}</b> a <b>{domingo_semana.strftime('%d/%m/%Y')}</b></div>",
        unsafe_allow_html=True
    )

with st.expander('➕ Adicionar item de acompanhamento'):
    with st.form('form_acomp', clear_on_submit=True):
        nova_desc_acomp = st.text_area('O que está sendo acompanhado *')
        novo_resp_acomp = st.text_input('Responsável (opcional)')
        quem_criou_acomp = st.text_input('Seu nome *')
        enviar_acomp = st.form_submit_button('➕ Adicionar')

        if enviar_acomp:
            if not nova_desc_acomp.strip() or not quem_criou_acomp.strip():
                st.error('Preencha os campos obrigatórios: descrição e seu nome.')
            else:
                supabase.table(TABELA_ACOMP).insert({
                    'descricao': nova_desc_acomp.strip(),
                    'responsavel': novo_resp_acomp.strip(),
                    'semana_referencia': segunda_semana.isoformat(),
                    'criado_por': quem_criou_acomp.strip(),
                    'criado_em': datetime.now().isoformat(),
                }).execute()
                st.success('Item adicionado!')
                st.cache_data.clear()
                st.rerun()

df_acomp = carregar_acompanhamento()
if not df_acomp.empty:
    itens_semana = df_acomp[df_acomp['semana_referencia'].dt.date == segunda_semana]
else:
    itens_semana = pd.DataFrame()

if len(itens_semana) == 0:
    st.info('Nenhum item cadastrado para esta semana ainda.')
else:
    for _, row in itens_semana.sort_values('criado_em').iterrows():
        resp_txt = f" — *{row['responsavel']}*" if row.get('responsavel') else ''
        meta_txt = row['criado_em'].strftime('%d/%m %H:%M') if pd.notna(row['criado_em']) else ''
        col_txt, col_del = st.columns([8, 1])
        with col_txt:
            st.markdown(
                f"- {row['descricao']}{resp_txt}  \n"
                f"<span style='font-size:11px;color:#888;'>cadastrado por {row['criado_por']} em {meta_txt}</span>",
                unsafe_allow_html=True
            )
        with col_del:
            if st.button('🗑️', key=f"del_acomp_{row['id']}"):
                supabase.table(TABELA_ACOMP).delete().eq('id', row['id']).execute()
                st.cache_data.clear()
                st.rerun()

st.divider()

# ── Filtros ─────────────────────────────────────────────────────
st.subheader('🔍 Filtros')
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    responsaveis = ['Todos'] + sorted(df['responsavel'].dropna().unique().tolist())
    filtro_resp = st.selectbox('👤 Responsável', responsaveis)

with col_f2:
    status_opts = ['Todos'] + sorted(df['status_exibicao'].dropna().unique().tolist())
    filtro_status = st.selectbox('📌 Status', status_opts)

with col_f3:
    tipo_opts = ['Todos'] + sorted(df['tipo'].dropna().unique().tolist())
    filtro_tipo = st.selectbox('🏷️ Tipo', tipo_opts)

with col_f4:
    busca = st.text_input('🔍 Buscar por palavra-chave')

col_p1, col_p2 = st.columns([1, 2])
with col_p1:
    periodo_opts = ['Todos', 'Últimos 30 dias', 'Últimos 3 meses', 'Últimos 6 meses', 'Ano atual', 'Personalizado']
    filtro_periodo = st.selectbox('📅 Período (Prazo)', periodo_opts)

data_ini, data_fim = None, None
if filtro_periodo == 'Personalizado':
    with col_p2:
        intervalo = st.date_input('Selecione o intervalo', value=(date.today().replace(day=1), date.today()))
        if isinstance(intervalo, tuple) and len(intervalo) == 2:
            data_ini, data_fim = intervalo

hoje_ts = pd.Timestamp(date.today())
if filtro_periodo == 'Últimos 30 dias':
    data_ini = hoje_ts - pd.Timedelta(days=30)
elif filtro_periodo == 'Últimos 3 meses':
    data_ini = hoje_ts - pd.Timedelta(days=90)
elif filtro_periodo == 'Últimos 6 meses':
    data_ini = hoje_ts - pd.Timedelta(days=180)
elif filtro_periodo == 'Ano atual':
    data_ini = pd.Timestamp(date(date.today().year, 1, 1))

df_filtrado = df.copy()
if filtro_resp != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['responsavel'] == filtro_resp]
if filtro_status != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['status_exibicao'] == filtro_status]
if filtro_tipo != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['tipo'] == filtro_tipo]
if busca:
    df_filtrado = df_filtrado[
        df_filtrado['problema_identificado'].str.contains(busca, case=False, na=False) |
        df_filtrado['plano_de_acao'].str.contains(busca, case=False, na=False)
    ]
if data_ini is not None:
    df_filtrado = df_filtrado[df_filtrado['prazo'] >= pd.Timestamp(data_ini)]
if data_fim is not None:
    df_filtrado = df_filtrado[df_filtrado['prazo'] <= pd.Timestamp(data_fim)]

st.caption(f'Exibindo {len(df_filtrado)} de {len(df)} ações')

with st.expander('📤 Exportar PPT'):
    st.caption('Gera uma apresentação com capa, resumo (cards + gráfico) e tabela detalhada, usando os filtros aplicados acima.')
    if st.button('Gerar apresentação'):
        with st.spinner('Gerando PPT...'):
            partes_filtro = []
            if filtro_resp != 'Todos':
                partes_filtro.append(f'Responsável: {filtro_resp}')
            if filtro_status != 'Todos':
                partes_filtro.append(f'Status: {filtro_status}')
            if filtro_tipo != 'Todos':
                partes_filtro.append(f'Tipo: {filtro_tipo}')
            if filtro_periodo != 'Todos':
                partes_filtro.append(f'Período: {filtro_periodo}')
            if busca:
                partes_filtro.append(f'Busca: "{busca}"')
            filtros_texto = ' · '.join(partes_filtro) if partes_filtro else 'Todas as ações'

            saida = '/tmp/plano_acao_export.pptx'
            gerar_ppt(None, df_filtrado, filtros_texto, saida)

            with open(saida, 'rb') as f:
                st.download_button(
                    '⬇️ Baixar PPT',
                    data=f.read(),
                    file_name=f'Plano_de_Acao_Portabilidade_{date.today().strftime("%Y%m%d")}.pptx',
                    mime='application/vnd.openxmlformats-officedocument.presentationml.presentation'
                )

st.divider()

# ── Cards de resumo (respeitam os filtros acima) ──────────────────
total = len(df_filtrado)
concluidas = len(df_filtrado[df_filtrado['status_exibicao'] == 'Concluído'])
atrasadas = len(df_filtrado[df_filtrado['status_exibicao'] == 'Atrasado'])
andamento = len(df_filtrado[df_filtrado['status_exibicao'] == 'Em andamento'])
estagnadas = df_filtrado['estagnada'].sum()
taxa = round(concluidas / total * 100, 1) if total > 0 else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('Total de Ações', total)
c2.metric('✅ Concluídas', concluidas)
c3.metric('⚠️ Atrasadas', atrasadas)
c4.metric('🔄 Em andamento', andamento)
c5.metric('🕒 Estagnadas', int(estagnadas))
c6.metric('📈 Taxa de Conclusão', f'{taxa}%')

st.divider()

# ── Gráficos ─────────────────────────────────────────────────────
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader('Status das Ações')
    contagem = df_filtrado['status_exibicao'].value_counts().reset_index()
    contagem.columns = ['Status', 'Qtde']
    fig1 = px.pie(contagem, values='Qtde', names='Status',
                  color='Status', color_discrete_map=STATUS_CORES, hole=0.4)
    fig1.update_traces(textinfo='label+value+percent')
    fig1.update_layout(margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col_g2:
    st.subheader('Ações por Tipo e Status')

    grafico_tipo_status = (
        df_filtrado
        .groupby(['tipo', 'status_exibicao'])
        .size()
        .reset_index(name='Quantidade')
    )

    fig2 = px.bar(
        grafico_tipo_status,
        x='tipo',
        y='Quantidade',
        color='status_exibicao',
        barmode='group',
        color_discrete_map={
            'Concluído': '#2E7D32',      # Verde
            'Em andamento': '#F9A825',  # Amarelo
            'Atrasado': '#C62828'       # Vermelho
        }
    )

    fig2.update_layout(
        margin=dict(t=10, b=10),
        xaxis_title='Tipo',
        yaxis_title='Quantidade',
        legend_title='Status'
    )

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
    'numero', 'responsavel', 'tipo', 'problema_identificado', 'plano_de_acao',
    'prazo_fmt', 'data_finalizacao_fmt', 'status_exibicao', 'dias_atraso_calc',
    'atualizado_em_fmt', 'atualizado_por'
]].rename(columns={
    'numero': 'Número', 'responsavel': 'Responsável', 'tipo': 'Tipo',
    'problema_identificado': 'Problema', 'plano_de_acao': 'Plano de Ação',
    'prazo_fmt': 'Prazo', 'data_finalizacao_fmt': 'Finalização',
    'status_exibicao': 'Status', 'dias_atraso_calc': 'Dias Atraso',
    'atualizado_em_fmt': 'Última Atualização', 'atualizado_por': 'Atualizado Por'
})

styled_table = tabela.style.map(colorir_status, subset=['Status'])
st.write(styled_table)
import io

buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    tabela.to_excel(writer, index=False, sheet_name="Acoes Detalhadas")

st.download_button(
    label="📥 Baixar Excel",
    data=buffer.getvalue(),
    file_name="acoes_detalhadas.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
st.divider()

# ── Criar nova ação ────────────────────────────────────────────────
st.subheader('➕ Criar Nova Ação')

with st.expander('Abrir formulário de nova ação'):
    with st.form('form_criar', clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            novo_problema = st.text_area('Problema Identificado *')
            novo_plano = st.text_area('Plano de Ação *')
            novo_resp = st.text_input('Responsável *')
            novo_tipo = st.selectbox('Tipo *', TIPO_OPCOES)
        with col2:
            novo_prazo = st.date_input('Prazo *', value=date.today())
            novo_status_criacao = st.selectbox('Status inicial', STATUS_OPCOES)
            comentario_criacao = st.text_area('Comentário / Contexto (opcional)')
            criado_por = st.text_input('Seu nome (quem está criando) *')

        criar = st.form_submit_button('➕ Criar Ação')

        if criar:
            faltando = []
            if not novo_problema.strip(): faltando.append('Problema Identificado')
            if not novo_plano.strip(): faltando.append('Plano de Ação')
            if not novo_resp.strip(): faltando.append('Responsável')
            if not criado_por.strip(): faltando.append('Seu nome')

            if faltando:
                st.error('Preencha os campos obrigatórios: ' + ', '.join(faltando))
            else:
                try:
                    numeros_validos = pd.to_numeric(df['numero'], errors='coerce').dropna()
                    proximo_numero = str(int(numeros_validos.max()) + 1) if len(numeros_validos) > 0 else '1'
                except Exception:
                    proximo_numero = str(len(df) + 1)

                novo_registro = {
                    'numero': proximo_numero,
                    'problema_identificado': novo_problema.strip(),
                    'plano_de_acao': novo_plano.strip(),
                    'responsavel': novo_resp.strip(),
                    'prazo': novo_prazo.isoformat(),
                    'status': novo_status_criacao,
                    'tipo': novo_tipo,
                    'comentario': comentario_criacao.strip(),
                    'atualizado_em': datetime.now().isoformat(),
                    'atualizado_por': criado_por.strip(),
                    'criado_por': criado_por.strip(),
                }
                supabase.table(TABELA).insert(novo_registro).execute()
                st.success(f'Ação #{proximo_numero} criada com sucesso!')
                st.cache_data.clear()
                st.rerun()

st.divider()

# ── Editar uma ação ───────────────────────────────────────────────
st.subheader('✏️ Atualizar uma Ação')
st.caption('A lista abaixo respeita os filtros selecionados acima (Responsável, Status, Tipo, busca).')

if len(df_filtrado) == 0:
    st.info('Nenhuma ação corresponde aos filtros selecionados.')
else:
    opcoes = df_filtrado.apply(lambda r: f"#{r['numero']} — {r['responsavel']} — {str(r['problema_identificado'])[:50]}", axis=1)
    mapa_opcoes = dict(zip(opcoes, df_filtrado['id']))

    escolha = st.selectbox('Selecione a ação', ['—'] + opcoes.tolist())

    if escolha != '—':
        acao_id = mapa_opcoes[escolha]
        linha = df[df['id'] == acao_id].iloc[0]
        status_atual = linha['status_exibicao']
        tipo_atual = linha.get('tipo')

        with st.form('form_editar'):
            col1, col2 = st.columns(2)
            with col1:
                indice_status = STATUS_OPCOES.index(status_atual) if status_atual in STATUS_OPCOES else 0
                novo_status = st.selectbox('Status', STATUS_OPCOES, index=indice_status)
                indice_tipo = TIPO_OPCOES.index(tipo_atual) if tipo_atual in TIPO_OPCOES else 0
                novo_tipo_edicao = st.selectbox('Tipo', TIPO_OPCOES, index=indice_tipo)
                novo_responsavel = st.text_input('Responsável', value=linha.get('responsavel') or '')
            with col2:
                nova_data_final = st.date_input(
                    'Data de Finalização (deixe vazio se ainda não concluído)',
                    value=linha['data_finalizacao'].date() if pd.notna(linha['data_finalizacao']) else None
                )
                quem_atualizou = st.text_input('Seu nome (quem está atualizando)')

            novo_comentario = st.text_area(
                'Comentário / Andamento',
                value=linha.get('comentario') or '',
                help='Obrigatório sempre que o status é alterado.'
            )

            enviado = st.form_submit_button('💾 Salvar Atualização')

            if enviado:
                erros = []
                if not quem_atualizou.strip():
                    erros.append('Informe seu nome.')
                if novo_status != status_atual and not novo_comentario.strip():
                    erros.append('Comentário é obrigatório ao mudar o status.')

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    update_data = {
                        'status': novo_status,
                        'tipo': novo_tipo_edicao,
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

        with st.expander('🗑️ Excluir esta ação'):
            st.warning(f"Isso vai apagar permanentemente a ação #{linha['numero']} — {linha['responsavel']}. Não tem como desfazer.")
            confirmar = st.checkbox('Sim, quero excluir essa ação permanentemente', key=f'confirmar_exclusao_{acao_id}')
            if st.button('🗑️ Excluir definitivamente', disabled=not confirmar):
                supabase.table(TABELA).delete().eq('id', acao_id).execute()
                st.success('Ação excluída.')
                st.cache_data.clear()
                st.rerun()

st.divider()

# ── Alertas de ações estagnadas ────────────────────────────────────
estagnadas_df = df[df['estagnada']].sort_values('dias_sem_atualizacao', ascending=False, na_position='first')
if len(estagnadas_df) > 0:
    st.subheader(f'🕒 Ações Estagnadas (sem atualização há {DIAS_ESTAGNACAO}+ dias)')
    st.caption('Estão "em andamento", dentro do prazo, mas ninguém mexeu recentemente.')
    for _, row in estagnadas_df.iterrows():
        dias_txt = f"{int(row['dias_sem_atualizacao'])} dias" if pd.notna(row['dias_sem_atualizacao']) else "nunca atualizada"
        st.warning(
            f"**#{row['numero']} | {row['responsavel']}** — "
            f"{str(row['problema_identificado'])[:80]}... "
            f"| Última atualização: **{dias_txt}**"
        )
