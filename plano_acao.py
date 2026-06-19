import streamlit as st
from supabase import create_client
from datetime import datetime
import pandas as pd

SUPABASE_URL = "https://yjvhfhodhlxgprpxelxs.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

RESPONSAVEIS = sorted([
    "Aline", "Borges", "Cícera", "Cícera e Galvão", "Cristiane", "Dani Vieira",
    "Daniela", "Diego", "Diego/Antonio", "Ednalva", "Fauzi",
    "Galvão", "Galvão, Roldão, Diego e Cícera", "Guilherme Carrasco",
    "Hebert", "Ieda", "Janaina Cruz", "Janaina/ OGS", "Marketing",
    "Natalia", "Rogerio Galvão", "Roldão", "Tânia", "Tânia e Dani Vieira",
    "TI", "Viviane", "Viviane e Natalia", "Vivi"
])

STATUS_OPCOES = ["Em andamento", "Concluído", "Atrasado", "Cancelado"]
STATUS_ICONS = {"Concluído": "✅", "Atrasado": "⚠️", "Em andamento": "🔄", "Cancelado": "❌"}

st.set_page_config(page_title="Plano de Ação | Portabilidade", layout="wide")

# ============================
# CSS
# ============================
st.markdown("""
<style>
.header-box {
    background-color: #cc0000;
    padding: 24px 32px;
    border-radius: 8px;
    margin-bottom: 24px;
}
.header-box h1 {
    color: white;
    margin: 0;
    font-size: 2rem;
}
.header-box p {
    color: rgba(255,255,255,0.85);
    margin: 6px 0 0 0;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ============================
# SUPABASE
# ============================
@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def carregar_dados():
    sb = get_supabase()
    result = sb.table("plano_acao").select("*").order("numero").execute()
    return pd.DataFrame(result.data)

def atualizar_registro(id_, status, comentario, responsavel):
    sb = get_supabase()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    sb.table("plano_acao").update({
        "status": status,
        "comentario": comentario,
        "atualizado_por": responsavel,
        "atualizado_em": datetime.now().isoformat(),
    }).eq("id", id_).execute()

def cadastrar_acao(dados):
    sb = get_supabase()
    sb.table("plano_acao").insert(dados).execute()

# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.header("👤 Identificação")
    usuario = st.selectbox("Seu nome", ["Selecione..."] + RESPONSAVEIS)

# ============================
# CARREGAR DADOS
# ============================
df_all = carregar_dados()

total = len(df_all)
concluidas = len(df_all[df_all["status"] == "Concluído"])
atrasadas = len(df_all[df_all["status"] == "Atrasado"])
em_andamento = len(df_all[df_all["status"] == "Em andamento"])
taxa = f"{round(concluidas / total * 100, 1)}%" if total > 0 else "0%"
agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

# ============================
# HEADER
# ============================
st.markdown(f"""
<div class="header-box">
    <h1>📋 Plano de Ação — Portabilidade</h1>
    <p>Atualizado automaticamente · {agora_str}</p>
</div>
""", unsafe_allow_html=True)

# ============================
# MÉTRICAS
# ============================
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total de Ações", total)
col2.metric("✅ Concluídas", concluidas)
col3.metric("⚠️ Atrasadas", atrasadas)
col4.metric("🔄 Em andamento", em_andamento)
col5.metric("📈 Taxa de Conclusão", taxa)

st.divider()

# ============================
# TABS
# ============================
aba_acoes, aba_nova = st.tabs(["📋 Ações", "➕ Nova Ação"])

# ============================
# ABA AÇÕES
# ============================
with aba_acoes:
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown("👤 **Filtrar por responsável**")
        filtro_resp = st.selectbox("", ["Todos"] + RESPONSAVEIS, label_visibility="collapsed", key="f_resp")
    with col_f2:
        st.markdown("📌 **Filtrar por status**")
        filtro_status = st.selectbox("", ["Todos"] + STATUS_OPCOES, label_visibility="collapsed", key="f_status")
    with col_f3:
        st.markdown("🔍 **Buscar por palavra-chave**")
        busca = st.text_input("", placeholder="Digite para buscar...", label_visibility="collapsed", key="busca")

    # Aplicar filtros
    df = df_all.copy()
    if filtro_resp != "Todos":
        df = df[df["responsavel"].str.contains(filtro_resp, case=False, na=False)]
    if filtro_status != "Todos":
        df = df[df["status"] == filtro_status]
    if busca:
        df = df[
            df["problema_identificado"].str.contains(busca, case=False, na=False) |
            df["plano_de_acao"].str.contains(busca, case=False, na=False)
        ]

    st.caption(f"Mostrando **{len(df)}** ações")
    st.divider()

    if df.empty:
        st.info("Nenhuma ação encontrada.")
    else:
        for _, row in df.iterrows():
            prazo_str = row.get('prazo') or '-'
            icon = STATUS_ICONS.get(row['status'], "")
            
            # Montar info de última atualização
            ultima_atualizacao = ""
            if row.get('atualizado_por') and row.get('atualizado_em'):
                try:
                    dt = datetime.fromisoformat(str(row['atualizado_em']))
                    dt_str = dt.strftime("%d/%m/%Y %H:%M")
                    ultima_atualizacao = f" · Atualizado por **{row['atualizado_por']}** em {dt_str}"
                except:
                    ultima_atualizacao = f" · Atualizado por **{row['atualizado_por']}**"

            with st.expander(f"#{row['numero']} — {row['responsavel']} | {icon} {row['status']} | Prazo: {prazo_str}"):
                st.markdown(f"**Problema:**\n{row['problema_identificado']}")
                st.markdown(f"**Plano de Ação:**\n{row['plano_de_acao']}")

                if row.get('observacao'):
                    st.caption(f"📝 {row['observacao']}")

                if row.get('comentario'):
                    st.info(f"💬 **Comentário:** {row['comentario']}{ultima_atualizacao}")
                elif ultima_atualizacao:
                    st.caption(f"🕐{ultima_atualizacao}")

                if usuario != "Selecione...":
                    col_s, col_c = st.columns([1, 2])
                    with col_s:
                        novo_status = st.selectbox(
                            "Novo status", STATUS_OPCOES,
                            index=STATUS_OPCOES.index(row["status"]) if row["status"] in STATUS_OPCOES else 0,
                            key=f"status_{row['id']}"
                        )
                    with col_c:
                        comentario = st.text_input(
                            "Comentário (opcional)",
                            value=row.get("comentario") or "",
                            key=f"comentario_{row['id']}"
                        )
                    if st.button("💾 Salvar", key=f"salvar_{row['id']}"):
                        atualizar_registro(row["id"], novo_status, comentario, usuario)
                        st.success(f"✅ Salvo! {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                        st.rerun()
                else:
                    st.warning("Selecione seu nome na barra lateral para editar.")

# ============================
# ABA NOVA AÇÃO
# ============================
with aba_nova:
    if usuario == "Selecione...":
        st.warning("Selecione seu nome na barra lateral para cadastrar uma nova ação.")
    else:
        st.subheader("➕ Cadastrar Nova Ação")
        proximo_numero = int(df_all["numero"].max()) + 1 if len(df_all) > 0 else 1
        st.caption(f"Número da ação: **#{proximo_numero}**")

        problema = st.text_area("Problema Identificado *", height=100)
        plano = st.text_area("Plano de Ação *", height=100)
        responsavel_acao = st.selectbox("Responsável *", ["Selecione..."] + RESPONSAVEIS, key="resp_nova")
        prazo = st.date_input("Prazo", value=None, key="prazo_nova")
        observacao = st.text_input("Observação (opcional)")

        if st.button("✅ Cadastrar Ação", type="primary"):
            if not problema or not plano or responsavel_acao == "Selecione...":
                st.error("Preencha os campos obrigatórios: Problema, Plano de Ação e Responsável.")
            else:
                dados = {
                    "numero": proximo_numero,
                    "origem": "Fórum de Portabilidade",
                    "data_entrada": datetime.now().strftime("%Y-%m-%d"),
                    "problema_identificado": problema,
                    "plano_de_acao": plano,
                    "responsavel": responsavel_acao,
                    "prazo": prazo.isoformat() if prazo else None,
                    "data_finalizacao": None,
                    "status": "Em andamento",
                    "dias_atraso": None,
                    "observacao": observacao or None,
                    "comentario": None,
                    "atualizado_por": usuario,
                    "atualizado_em": datetime.now().isoformat(),
                }
                cadastrar_acao(dados)
                st.success(f"✅ Ação #{proximo_numero} cadastrada com sucesso!")
                st.rerun()
