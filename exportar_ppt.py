"""Geração do PPT do Plano de Ação — Portabilidade.

Monta uma apresentação com capa, resumo executivo, tabelas de ações
(paginadas por status) e histórico de alterações.

Regra principal das tabelas: nenhum texto é cortado. A altura de cada
linha (inclusive a do cabeçalho) é calculada a partir do texto que ela
contém e cresce o quanto for preciso; uma linha só entra numa página se
ainda couber no espaço disponível do slide — quando não cabe mais, uma
nova página é aberta automaticamente.
"""

from datetime import datetime
import math

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ── Paleta e fonte ──────────────────────────────────────────────────
FONTE = "AMX"

COR_VERMELHO = RGBColor(192, 0, 0)          # vermelho "marca" (capa, cards e cabeçalhos de tabela)
COR_VERMELHO_HEADER = COR_VERMELHO          # cabeçalhos de tabela: #C00000 (RGB 192,0,0)
COR_PRETO = RGBColor(0, 0, 0)
COR_BRANCO = RGBColor(255, 255, 255)
COR_VERDE = RGBColor(112, 173, 71)
COR_LARANJA = RGBColor(244, 177, 131)
COR_CINZA = RGBColor(127, 127, 127)

# ── Medidas usadas para as tabelas nunca cortarem texto ─────────────
ALTURA_TOPO_TABELA = 0.8     # polegadas: onde a tabela começa (abaixo do título do slide)
ALTURA_MAX_TABELA = 6.3      # polegadas: espaço disponível até a margem inferior do slide (7.5")
MARGEM_VERTICAL_CELULA = 0.07
MARGEM_CELULA = Inches(0.05)
# Estimativa "folgada" de caracteres por polegada para um corpo sans-serif:
# preferimos subestimar os caracteres por linha (e superestimar a altura)
# a arriscar cortar texto.
FATOR_LARGURA_CARACTERE = 0.0095


def _estimar_linhas(texto, largura_pol, tamanho_pt):
    """Estima quantas linhas `texto` vai ocupar ao quebrar em `largura_pol`."""

    texto = "" if texto is None else str(texto)
    if not texto.strip():
        return 1

    largura_media_char = tamanho_pt * FATOR_LARGURA_CARACTERE
    caracteres_por_linha = max(6, int(largura_pol / largura_media_char))

    linhas = 0
    for paragrafo in texto.split("\n"):
        linhas += 1 if paragrafo == "" else math.ceil(len(paragrafo) / caracteres_por_linha)

    return max(1, linhas)


def _altura_linha(n_linhas, tamanho_pt):
    """Altura (em polegadas) necessária para `n_linhas` linhas a `tamanho_pt`."""

    altura_por_linha = (tamanho_pt * 1.25) / 72
    return n_linhas * altura_por_linha + MARGEM_VERTICAL_CELULA


def _altura_cabecalho(colunas, tamanho_pt):
    n_linhas = max(_estimar_linhas(col["titulo"], col["largura"], tamanho_pt) for col in colunas)
    return _altura_linha(n_linhas, tamanho_pt)


def _formatar_fonte(run, tamanho_pt, cor, negrito=False):
    run.font.name = FONTE
    run.font.size = Pt(tamanho_pt)
    run.font.bold = negrito
    run.font.color.rgb = cor


def _aplicar_fonte(text_frame, tamanho_pt, cor, negrito=False, alinhamento=None):
    for paragrafo in text_frame.paragraphs:
        if alinhamento is not None:
            paragrafo.alignment = alinhamento
        for run in paragrafo.runs:
            _formatar_fonte(run, tamanho_pt, cor, negrito)


def _formatar_celula(cell, texto, tamanho_pt, cor_fonte, cor_fundo, negrito=False, alinhamento=None):
    cell.text = "" if texto is None else str(texto)
    cell.text_frame.word_wrap = True
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = MARGEM_CELULA
    cell.margin_right = MARGEM_CELULA
    cell.margin_top = Inches(0.03)
    cell.margin_bottom = Inches(0.03)
    if cor_fundo is None:
        cell.fill.background()  # sem cor de fundo (transparente)
    else:
        cell.fill.solid()
        cell.fill.fore_color.rgb = cor_fundo
    _aplicar_fonte(cell.text_frame, tamanho_pt, cor_fonte, negrito, alinhamento)


# ── Paginação de tabelas sem corte de texto ─────────────────────────

def _dividir_em_paginas(linhas, colunas, tamanho_pt_body=9, tamanho_pt_header=10):
    """Agrupa `linhas` (lista de dicts) em páginas que cabem no slide.

    Retorna uma lista de páginas; cada página é uma lista de tuplas
    (linha, altura_em_polegadas) já prontas para desenhar na tabela.
    """

    altura_disponivel = ALTURA_MAX_TABELA - _altura_cabecalho(colunas, tamanho_pt_header)

    paginas = []
    pagina_atual = []
    altura_pagina_atual = 0.0

    for linha in linhas:
        n_linhas_max = max(
            _estimar_linhas(linha.get(col["chave"]), col["largura"], tamanho_pt_body)
            for col in colunas
        )
        altura = _altura_linha(n_linhas_max, tamanho_pt_body)

        if pagina_atual and (altura_pagina_atual + altura > altura_disponivel):
            paginas.append(pagina_atual)
            pagina_atual = []
            altura_pagina_atual = 0.0

        pagina_atual.append((linha, altura))
        altura_pagina_atual += altura

    if pagina_atual:
        paginas.append(pagina_atual)

    return paginas or [[]]


def _adicionar_slide_tabela(prs, titulo_texto, colunas, linhas_pagina,
                             tamanho_pt_header=10, tamanho_pt_body=9):

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(Inches(0.3), Inches(0.2), Inches(9), Inches(0.4))
    titulo.text_frame.text = titulo_texto
    _aplicar_fonte(titulo.text_frame, 18, COR_PRETO, negrito=True)

    altura_cabecalho = _altura_cabecalho(colunas, tamanho_pt_header)
    altura_corpo = sum(altura for _, altura in linhas_pagina)
    largura_tabela = Inches(sum(col["largura"] for col in colunas))
    left_centralizado = int((prs.slide_width - largura_tabela) / 2)

    tabela = slide.shapes.add_table(
        len(linhas_pagina) + 1,
        len(colunas),
        left_centralizado,
        Inches(ALTURA_TOPO_TABELA),
        largura_tabela,
        Inches(max(altura_cabecalho + altura_corpo, 0.5)),
    ).table

    for c, col in enumerate(colunas):
        tabela.columns[c].width = Inches(col["largura"])

    tabela.rows[0].height = Inches(altura_cabecalho)
    for c, col in enumerate(colunas):
        _formatar_celula(
            tabela.cell(0, c), col["titulo"], tamanho_pt_header,
            COR_BRANCO, COR_VERMELHO_HEADER, negrito=True, alinhamento=PP_ALIGN.CENTER,
        )

    # Linhas de dados sem cor de fundo — só o cabeçalho vermelho funciona como
    # "risco" dividindo o título da tabela do conteúdo; sem fundo cinza nas
    # linhas pra não parecer uma tabela cheia.
    for r, (linha, altura) in enumerate(linhas_pagina, start=1):
        tabela.rows[r].height = Inches(altura)
        for c, col in enumerate(colunas):
            _formatar_celula(
                tabela.cell(r, c), linha.get(col["chave"]), tamanho_pt_body,
                COR_PRETO, None,
            )

    return slide


# ── Capa ─────────────────────────────────────────────────────────────

def _construir_capa(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(7), Inches(1))
    titulo.text_frame.text = "Plano de Ação\nPortabilidade"
    _aplicar_fonte(titulo.text_frame, 28, COR_VERMELHO, negrito=True)

    sub = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(6), Inches(0.5))
    sub.text_frame.text = f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    _aplicar_fonte(sub.text_frame, 14, COR_PRETO)


# ── Resumo executivo ────────────────────────────────────────────────

def _construir_resumo(prs, df_filtrado):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(4), Inches(0.5))
    titulo.text_frame.text = "Resumo Executivo"
    _aplicar_fonte(titulo.text_frame, 20, COR_PRETO, negrito=True)

    total = len(df_filtrado)
    concluidas = len(df_filtrado[df_filtrado["status_exibicao"] == "Concluído"])
    atrasadas = len(df_filtrado[df_filtrado["status_exibicao"] == "Atrasado"])
    andamento = len(df_filtrado[df_filtrado["status_exibicao"] == "Em andamento"])
    estagnadas = int(df_filtrado["estagnada"].sum()) if total > 0 else 0
    taxa = round(concluidas / total * 100, 1) if total > 0 else 0

    cards = [
        ("Total", total, COR_CINZA),
        ("Concluídas", concluidas, COR_VERDE),
        ("Atrasadas", atrasadas, COR_VERMELHO),
        ("Em andamento", andamento, COR_LARANJA),
        ("Estagnadas", estagnadas, COR_VERMELHO),
        ("Taxa", f"{taxa}%", COR_VERMELHO),
    ]

    for i, (titulo_card, valor, cor) in enumerate(cards):
        x = 0.4 + (i * 1.6)
        card = slide.shapes.add_textbox(Inches(x), Inches(1), Inches(1.4), Inches(0.7))
        card.fill.solid()
        card.fill.fore_color.rgb = cor
        card.text_frame.word_wrap = True
        card.text_frame.text = f"{valor}\n{titulo_card}"
        _aplicar_fonte(card.text_frame, 12, COR_BRANCO, negrito=True, alinhamento=PP_ALIGN.CENTER)


# ── Tabelas de ações por status ──────────────────────────────────────

COLUNAS_ACOES = [
    {"titulo": "Número", "chave": "numero", "largura": 0.5},
    {"titulo": "Responsável", "chave": "responsavel", "largura": 1.0},
    {"titulo": "Tipo", "chave": "tipo", "largura": 0.8},
    {"titulo": "Problema", "chave": "problema_identificado", "largura": 1.7},
    {"titulo": "Plano de Ação", "chave": "plano_de_acao", "largura": 1.7},
    {"titulo": "Status", "chave": "status_exibicao", "largura": 0.7},
    {"titulo": "Última Atualização", "chave": "atualizado_em_fmt", "largura": 1.0},
    {"titulo": "Último Comentário", "chave": "comentario", "largura": 2.1},
]


def _construir_tabelas_por_status(prs, df_filtrado):
    status_ordem = ["Atrasado", "Em andamento", "Concluído"]

    for status in status_ordem:
        df_status = df_filtrado[df_filtrado["status_exibicao"] == status]
        if len(df_status) == 0:
            continue

        linhas = df_status.to_dict("records")
        paginas = _dividir_em_paginas(linhas, COLUNAS_ACOES)

        for i, linhas_pagina in enumerate(paginas, start=1):
            titulo_texto = f"Ações {status} ({i}/{len(paginas)})"
            _adicionar_slide_tabela(prs, titulo_texto, COLUNAS_ACOES, linhas_pagina)


# ── Histórico de alterações ──────────────────────────────────────────

COLUNAS_HISTORICO = [
    {"titulo": "Quando", "chave": "_quando", "largura": 1.2},
    {"titulo": "Quem", "chave": "alterado_por", "largura": 1.2},
    {"titulo": "Ação Nº", "chave": "acao_numero", "largura": 0.9},
    {"titulo": "Evento", "chave": "tipo_evento", "largura": 1.8},
    {"titulo": "Comentário", "chave": "comentario", "largura": 4.4},
]


def _construir_tabela_historico(prs, df_historico):
    if df_historico is None or len(df_historico) == 0:
        return

    dfh = df_historico.sort_values("alterado_em", ascending=False)

    linhas = []
    for _, row in dfh.iterrows():
        quando = (
            row["alterado_em"].strftime("%d/%m/%Y %H:%M")
            if row["alterado_em"] is not None else "—"
        )
        linhas.append({
            "_quando": quando,
            "alterado_por": row.get("alterado_por") or "",
            "acao_numero": row.get("acao_numero") or "",
            "tipo_evento": row.get("tipo_evento") or "",
            "comentario": row.get("comentario") or "",
        })

    paginas = _dividir_em_paginas(linhas, COLUNAS_HISTORICO)

    for i, linhas_pagina in enumerate(paginas, start=1):
        titulo_texto = f"Histórico de Alterações ({i}/{len(paginas)})"
        _adicionar_slide_tabela(prs, titulo_texto, COLUNAS_HISTORICO, linhas_pagina)


# ── Ponto de entrada ─────────────────────────────────────────────────

def gerar_ppt(template_path, df_filtrado, filtros_texto, saida_path, df_historico=None):
    prs = Presentation(template_path) if template_path else Presentation()

    _construir_capa(prs)
    _construir_resumo(prs, df_filtrado)
    _construir_tabelas_por_status(prs, df_filtrado)
    _construir_tabela_historico(prs, df_historico)

    prs.save(saida_path)

    return saida_path
