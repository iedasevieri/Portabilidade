import streamlit as st
from supabase import create_client
from datetime import date
import pandas as pd

SUPABASE_URL = "https://yjvhfhodhlxgprpxelxs.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

RESPONSAVEIS = [
    "Aline", "Borges", "Cícera e Galvão", "Cristiane", "Dani Vieira",
    "Daniela", "Diego", "Diego/Antonio", "Ednalva", "Fauzi",
    "Galvão", "Galvão, Roldão, Diego e Cícera", "Guilherme Carrasco",
    "Hebert", "Ieda", "Janaina Cruz", "Janaina/ OGS", "Marketing",
    "Natalia", "Rogerio Galvão", "Tania", "TI", "Viviane", "Viviane e Natalia",
    "Vivi"
]

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
        "atualizado_em": date.today().isoformat(),
    }).eq("id", id_).execute()

st.set_page_config(page_title="Plano de Ação | Portabilidade", layout="wide")
st.title("📋 Plano de Ação — Portabilidade ANATEL")

with st.sidebar:
    st.header("👤 Identificação")
    usuario = st.selectbox("Seu nome", ["Selecione..."] + RESPONSAVEIS)
    st.divider()
    st.header("🔍 Filtros")
    filtro_status = st.multiselect("Status", STATUS_OPCOES, default=["Em andamento", "Atrasado"])
    filtro_resp = st.multiselect("Responsável", RESPONSAVEIS)

df = carregar_dados()

if filtro_status:
    df = df[df["status"].isin(filtro_status)]
if filtro_resp:
    df = df[df["responsavel"].str.contains("|".join(filtro_resp), case=False, na=False)]

st.caption(f"Mostrando **{len(df)}** ações")

df_all = carregar_dados()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total", len(df_all))
col2.metric("✅ Concluídas", len(df_all[df_all["status"] == "Concluído"]))
col3.metric("⚠️ Atrasadas", len(df_all[df_all["status"] == "Atrasado"]))
col4.metric("🔄 Em andamento", len(df_all[df_all["status"] == "Em andamento"]))

st.divider()

if df.empty:
    st.info("Nenhuma ação encontrada com os filtros selecionados.")
else:
    for _, row in df.iterrows():
        with st.expander(f"#{row['numero']} — {row['responsavel']} | {row['status']} | Prazo: {row.get('prazo', '-')}"):
            st.markdown(f"**Problema:**\n{row['problema_identificado']}")
            st.markdown(f"**Plano de Ação:**\n{row['plano_de_acao']}")

            if row.get('comentario'):
                st.info(f"💬 Último comentário: {row['comentario']} _(por {row.get('atualizado_por', '?')})_")

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
