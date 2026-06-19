import streamlit as st
from supabase import create_client
from datetime import date, datetime
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

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def carregar_dados():
    sb = get_supabase()
    result = sb.table("plano_acao").select("*").order("numero").execute()
    return pd.DataFrame(result.data)

def atualizar_registro(id_, status, comentario, responsavel):
    sb = get_supabase()
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
# PÁGINA
# ============================
st.set_page_config(page_title="Plano de Ação | Portabilidade", layout="wide")
st.title("📋 Plano de Ação — Portabilidade ANATEL")

# Sidebar
with st.sidebar:
    st.header("👤 Identificação")
    usuario = st.selectbox("Seu nome", ["Selecione..."] + RESPONSAVEIS)

    st.divider()
    st.header("🔍 Filtros")
    filtro_status = st.multiselect("Status", STATUS_OPCOES, default=["Em andamento", "Atrasado"])
    filtro_resp = st.multiselect("Responsável", RESPONSAVEIS)

# Tabs
aba_acoes, aba_nova = st.tabs(["📋 Ações", "➕ Nova Ação"])

# ============================
# ABA: AÇÕES
# ============================
with aba_acoes:
    df = carregar_dados()
    df_all = df.copy()

    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", len(df_all))
    col2.metric("✅ Concluídas", len(df_all[df_all["status"] == "Concluído"]))
    col3.metric("⚠️ Atrasadas", len(df_all[df_all["status"] == "Atrasado"]))
    col4.metric("🔄 Em andamento", len(df_all[df_all["status"] == "Em andamento"]))

    st.divider()

    # Filtros
    if filtro_status:
        df = df[df["status"].isin(filtro_status)]
    if filtro_resp:
        df = df[df["responsavel"].str.contains("|".join(filtro_resp), case=False, na=False)]

    st.caption(f"Mostrando **{len(df)}** ações")

    if df.empty:
        st.info("Nenhuma ação encontrada com os filtros selecionados.")
    else:
        for _, row in df.iterrows():
            prazo_str = row.get('prazo') or '-'
            status_icon = {"Concluído": "✅", "Atrasado": "⚠️", "Em andamento": "🔄", "Cancelado": "❌"}.get(row['status'], "")
            with st.expander(f"#{row['numero']} — {row['responsavel']} | {status_icon} {row['status']} | Prazo: {prazo_str}"):
                st.markdown(f"**Problema:**\n{row['problema_identificado']}")
                st.markdown(f"**Plano de Ação:**\n{row['plano_de_acao']}")

                if row.get('observacao'):
                    st.caption(f"📝 Observação: {row['observacao']}")
                if row.get('comentario'):
                    st.info(f"💬 Comentário: {row['comentario']} _(por {row.get('atualizado_por', '?')})_")

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
                        st.success("Atualizado com sucesso!")
                        st.rerun()
                else:
                    st.warning("Selecione seu nome na barra lateral para editar.")

# ============================
# ABA: NOVA AÇÃO
# ============================
with aba_nova:
    if usuario == "Selecione...":
        st.warning("Selecione seu nome na barra lateral para cadastrar uma nova ação.")
    else:
        st.subheader("➕ Cadastrar Nova Ação")

        df_temp = carregar_dados()
        proximo_numero = int(df_temp["numero"].max()) + 1 if len(df_temp) > 0 else 1
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
                    "data_entrada": date.today().isoformat(),
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
                }
                cadastrar_acao(dados)
                st.success(f"✅ Ação #{proximo_numero} cadastrada com sucesso!")
                st.rerun()
