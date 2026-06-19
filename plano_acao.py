import streamlit as st
from supabase import create_client
from datetime import datetime, timezone, timedelta
import pandas as pd
from io import BytesIO

SUPABASE_URL = "https://yjvhfhodhlxgprpxelxs.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

BRASILIA = timezone(timedelta(hours=-3))

def agora_brasilia():
    return datetime.now(BRASILIA)

RESPONSAVEIS = sorted([
    "Antonio", "Aline", "Andreia", "Borges", "Cícera", "Cristiane",
    "Dani Vieira", "Diego", "Diego/Antonio", "Ednalva", "Eunice",
    "Fauzi", "Flávia", "Galvão", "Guilherme Carrasco", "Hebert",
    "Ieda", "Izabella", "Janaina Cruz", "Janaina/OGS", "Kleiton",
    "Lia Mara", "Luis Fernando", "Marketing", "Natalia", "Núbia",
    "Rogerio Galvão", "Roldão", "Stephanie", "Tânia", "TI", "Viviane"
])

STATUS_OPCOES = ["Em andamento", "Concluído", "Atrasado", "Cancelado"]
STATUS_ICONS = {"Concluído": "✅", "Atrasado": "⚠️", "Em andamento": "🔄", "Cancelado": "❌"}

st.set_page_config(page_title="Plano de Ação | Portabilidade", layout="wide")

st.markdown("""
<style>
.header-box {
    background-color: #cc0000;
    padding: 24px 32px;
    border-radius: 8px;
    margin-bottom: 24px;
}
.header-box h1 { color: white; margin: 0; font-size: 2rem; }
.header-box p { color: rgba(255,255,255,0.85); margin: 6px 0 0 0; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def carregar_dados():
    sb = get_supabase()
    result = sb.table("plano_acao").select("*").order("numero").execute()
    return pd.DataFrame(result.data)

def carregar_historico(acao_id):
    sb = get_supabase()
    result = sb.table("plano_acao_historico").select("*").eq("acao_id", acao_id).order("atualizado_em", desc=True).execute()
    return pd.DataFrame(result.data)

def salvar_historico(acao_id, numero, status_anterior, status_novo, comentario, novo_prazo, responsavel):
    sb = get_supabase()
    sb.table("plano_acao_historico").insert({
        "acao_id": int(acao_id),
        "numero": int(numero),
        "status_anterior": status_anterior,
        "status_novo": status_novo,
        "comentario": comentario or None,
        "novo_prazo": novo_prazo or None,
        "atualizado_por": responsavel,
        "atualizado_em": agora_brasilia().isoformat(),
    }).execute()

def atualizar_registro(id_, status, comentario, responsavel, novo_prazo=None):
    sb = get_supabase()
    update = {
        "status": status,
        "comentario": comentario or None,
        "atualizado_por": responsavel,
        "atualizado_em": agora_brasilia().isoformat(),
    }
    if novo_prazo:
        update["prazo"] = novo_prazo
    sb.table("plano_acao").update(update).eq("id", id_).execute()

def cadastrar_acao(dados):
    sb = get_supabase()
    sb.table("plano_acao").insert(dados).execute()

def formatar_data(dt_str):
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(str(dt_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(BRASILIA)
        return dt_br.strftime("%d/%m/%Y %H:%M")
    except:
        return str(dt_str)

def limpar(valor):
    """Retorna None se valor for vazio, nan ou None"""
    if valor is None:
        return None
    s = str(valor).strip()
    if s.lower() in ('nan', 'none', ''):
        return None
    return s

# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.header("👤 Identificação")
    usuario = st.selectbox("Seu nome", ["Selecione..."] + RESPONSAVEIS)

# ============================
# DADOS
# ============================
df_all = carregar_dados()
total = len(df_all)
concluidas = len(df_all[df_all["status"] == "Concluído"])
atrasadas = len(df_all[df_all["status"] == "Atrasado"])
em_andamento = len(df_all[df_all["status"] == "Em andamento"])
taxa = f"{round(concluidas / total * 100, 1)}%" if total > 0 else "0%"
agora_str = agora_brasilia().strftime("%d/%m/%Y %H:%M")

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
aba_acoes, aba_nova, aba_export = st.tabs(["📋 Ações", "➕ Nova Ação", "📥 Exportar"])

# ============================
# ABA AÇÕES
# ============================
with aba_acoes:
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
            prazo_str = limpar(row.get('prazo')) or '-'
            icon = STATUS_ICONS.get(row['status'], "")
            atualizado_por = limpar(row.get('atualizado_por'))
            atualizado_em = formatar_data(row.get('atualizado_em'))
            comentario_atual = limpar(row.get('comentario'))
            observacao_atual = limpar(row.get('observacao'))

            with st.expander(f"#{row['numero']} — {row['responsavel']} | {icon} {row['status']} | Prazo: {prazo_str}"):
                st.markdown(f"**Problema:**\n{row['problema_identificado']}")
                st.markdown(f"**Plano de Ação:**\n{row['plano_de_acao']}")

                if observacao_atual:
                    st.caption(f"📝 {observacao_atual}")

                if comentario_atual:
                    info_str = f"💬 **Comentário:** {comentario_atual}"
                    if atualizado_por and atualizado_em:
                        info_str += f" · Atualizado por **{atualizado_por}** em {atualizado_em}"
                    st.info(info_str)
                elif atualizado_por and atualizado_em:
                    st.caption(f"🕐 Atualizado por **{atualizado_por}** em {atualizado_em}")

                # Histórico
                hist = carregar_historico(row['id'])
                if not hist.empty:
                    with st.expander("📜 Ver histórico de alterações"):
                        for _, h in hist.iterrows():
                            dt_h = formatar_data(h.get('atualizado_em'))
                            prazo_h = f" | Novo prazo: {h['novo_prazo']}" if limpar(h.get('novo_prazo')) else ""
                            coment_h = f" | Comentário: {h['comentario']}" if limpar(h.get('comentario')) else ""
                            st.markdown(f"- **{dt_h}** — {h.get('atualizado_por','')} mudou de *{h.get('status_anterior','')}* para *{h.get('status_novo','')}*{prazo_h}{coment_h}")

                if usuario != "Selecione...":
                    col_s, col_c = st.columns([1, 2])
                    with col_s:
                        novo_status = st.selectbox(
                            "Novo status", STATUS_OPCOES,
                            index=STATUS_OPCOES.index(row["status"]) if row["status"] in STATUS_OPCOES else 0,
                            key=f"status_{row['id']}"
                        )
                    with col_c:
                        label_coment = "Comentário (obrigatório) *" if novo_status == "Atrasado" else "Comentário (opcional)"
                        comentario = st.text_input(label_coment, value="", key=f"comentario_{row['id']}")

                    # Novo prazo obrigatório se saindo de Atrasado
                    novo_prazo = None
                    mudando_de_atrasado = (row['status'] == "Atrasado" and novo_status != "Atrasado")
                    if mudando_de_atrasado:
                        st.warning("⚠️ Ação estava atrasada — informe o novo prazo.")
                        novo_prazo = st.date_input("Novo prazo *", value=None, key=f"prazo_{row['id']}")

                    if st.button("💾 Salvar", key=f"salvar_{row['id']}"):
                        status_mudou = novo_status != row['status']
                        comentario_mudou = comentario.strip() != ""

                        # Validações
                        if novo_status == "Atrasado" and not comentario.strip():
                            st.error("Comentário obrigatório ao marcar como Atrasado.")
                        elif mudando_de_atrasado and not novo_prazo:
                            st.error("Informe o novo prazo para reabrir a ação.")
                        elif mudando_de_atrasado and not comentario.strip():
                            st.error("Comentário obrigatório ao alterar o prazo.")
                        elif not status_mudou and not comentario_mudou:
                            st.warning("Nenhuma alteração detectada. Mude o status ou adicione um comentário.")
                        else:
                            prazo_salvar = novo_prazo.isoformat() if novo_prazo else None
                            # Só registra histórico se status mudou
                            if status_mudou:
                                salvar_historico(
                                    row['id'], row['numero'],
                                    row['status'], novo_status,
                                    comentario, prazo_salvar, usuario
                                )
                            atualizar_registro(row['id'], novo_status, comentario or None, usuario, prazo_salvar)
                            st.success(f"✅ Salvo em {agora_brasilia().strftime('%d/%m/%Y %H:%M')}")
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
                    "data_entrada": agora_brasilia().strftime("%Y-%m-%d"),
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
                    "atualizado_em": agora_brasilia().isoformat(),
                }
                cadastrar_acao(dados)
                st.success(f"✅ Ação #{proximo_numero} cadastrada!")
                st.rerun()

# ============================
# ABA EXPORTAR
# ============================
with aba_export:
    st.subheader("📥 Exportar dados para Excel")
    st.caption("Exporta todas as ações com status atual.")

    df_export = df_all.copy()
    df_export = df_export.rename(columns={
        "numero": "Número",
        "origem": "Origem",
        "data_entrada": "Data Entrada",
        "problema_identificado": "Problema Identificado",
        "plano_de_acao": "Plano de Ação",
        "responsavel": "Responsável",
        "prazo": "Prazo",
        "data_finalizacao": "Data Finalização",
        "status": "Status",
        "dias_atraso": "Dias Atraso",
        "observacao": "Observação",
        "comentario": "Último Comentário",
        "atualizado_por": "Atualizado Por",
        "atualizado_em": "Atualizado Em",
    })
    df_export = df_export.drop(columns=["id"], errors="ignore")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Plano de Ação")
    buffer.seek(0)

    st.download_button(
        label="⬇️ Baixar Excel",
        data=buffer,
        file_name=f"plano_acao_{agora_brasilia().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
