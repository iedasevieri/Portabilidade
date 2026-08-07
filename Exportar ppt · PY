import copy
import io
from datetime import datetime

import pandas as pd
from pptx import Presentation
from pptx.util import Emu, Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.opc.package import _Relationship, RTM
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

# ── índices dos slides-base no template (0-indexed) ────────────────
IDX_TITULO = 0
IDX_RESUMO_BASE = 5
IDX_TABELA_BASE = 9
IDX_FECHAMENTO = 10
TOTAL_SLIDES_ORIGINAIS = 18
LINHAS_POR_PAGINA = 10

TIPO_ABREV = {
    'Investigação/Acompanhamento': 'Investig./Acomp.',
    'Melhoria de Processo': 'Melhoria Proc.',
}

COR_STATUS = {
    'Em andamento': RGBColor(0xFF, 0x98, 0x00),
    'Atrasado': RGBColor(0xCC, 0x00, 0x00),
    'Concluído': RGBColor(0x4C, 0xAF, 0x50),
}


def remover_logo_uotz(slide):
    """Remove o logo circular da uotz do cabeçalho de um slide, se presente."""
    for shape in list(slide.shapes):
        if shape.shape_type == 13 and shape.name == 'Google Shape;137;p62':
            shape._element.getparent().remove(shape._element)


def duplicate_slide(prs, index):
    source = prs.slides[index]
    layout = source.slide_layout
    new_slide = prs.slides.add_slide(layout)

    rels = new_slide.part.rels
    layout_rid = next(r for r in list(rels) if rels[r].reltype == RT.SLIDE_LAYOUT)
    layout_rel = rels[layout_rid]
    del rels._rels[layout_rid]

    for shape in list(new_slide.shapes):
        shape._element.getparent().remove(shape._element)

    # copia o plano de fundo do slide (p:bg), se houver, já que fica fora da spTree
    from pptx.oxml.ns import qn
    bg_origem = source._element.find(qn('p:cSld')).find(qn('p:bg'))
    if bg_origem is not None:
        cSld_novo = new_slide._element.find(qn('p:cSld'))
        bg_existente = cSld_novo.find(qn('p:bg'))
        if bg_existente is not None:
            cSld_novo.remove(bg_existente)
        cSld_novo.insert(0, copy.deepcopy(bg_origem))

    for shape in source.shapes:
        new_el = copy.deepcopy(shape._element)
        new_slide.shapes._spTree.append(new_el)

    usados = set()
    for rid, rel in source.part.rels.items():
        if rel.reltype in (RT.SLIDE_LAYOUT, RT.NOTES_SLIDE):
            continue
        rels._rels[rid] = _Relationship(
            rels._base_uri, rid, rel.reltype,
            target_mode=(RTM.EXTERNAL if rel.is_external else RTM.INTERNAL),
            target=(rel.target_ref if rel.is_external else rel.target_part),
        )
        usados.add(rid)

    n = 1
    while f"rId{n}" in usados:
        n += 1
    novo_layout_rid = f"rId{n}"
    rels._rels[novo_layout_rid] = _Relationship(
        rels._base_uri, novo_layout_rid, RT.SLIDE_LAYOUT,
        target_mode=RTM.INTERNAL, target=layout_rel.target_part
    )
    return new_slide


def set_text(shape, texto):
    """Substitui o texto de uma forma preservando a formatação do primeiro run."""
    tf = shape.text_frame
    p = tf.paragraphs[0]
    if p.runs:
        p.runs[0].text = texto
        for r in p.runs[1:]:
            r.text = ''
    else:
        p.text = texto


def truncar(txt, n):
    txt = '' if txt is None or (isinstance(txt, float) and pd.isna(txt)) else str(txt)
    return txt if len(txt) <= n else txt[:n - 1].rstrip() + '…'


def gerar_ppt(template_path, df_filtrado, filtros_texto, saida_path):
    prs = Presentation(template_path)

    # ── Capa ──────────────────────────────────────────────────────
    capa = duplicate_slide(prs, IDX_TITULO)
    titulo_shape = next(s for s in capa.shapes if s.has_text_frame and 'Título da Apresentação' in s.text_frame.text)
    set_text(titulo_shape, 'Plano de Ação — Portabilidade')
    sub_shape = next(s for s in capa.shapes if s.has_text_frame and 'Subtítulo' in s.text_frame.text)
    set_text(sub_shape, f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")} · {filtros_texto}')
    lorem_shape = next((s for s in capa.shapes if s.has_text_frame and 'Resumo da apresentação' in s.text_frame.text), None)
    if lorem_shape is not None:
        lorem_shape._element.getparent().remove(lorem_shape._element)
    # remove elementos de marca da uotz (marca-d'água "Z" e logo circular)
    for shape in list(capa.shapes):
        if shape.shape_type == 13 and shape.name in ('Imagem 19', 'Imagem 21'):
            shape._element.getparent().remove(shape._element)
    remover_logo_uotz(capa)

    # ── Resumo ────────────────────────────────────────────────────
    resumo = duplicate_slide(prs, IDX_RESUMO_BASE)
    remover_logo_uotz(resumo)
    titulo_resumo = next(s for s in resumo.shapes if s.name == 'Google Shape;121;p13')
    set_text(titulo_resumo, 'Resumo | Plano de Ação')
    sub_resumo = next((s for s in resumo.shapes if s.has_text_frame and s.text_frame.text.strip() == 'xxxxxxxx'), None)
    if sub_resumo:
        set_text(sub_resumo, filtros_texto)

    total = len(df_filtrado)
    concluidas = int((df_filtrado['status_exibicao'] == 'Concluído').sum())
    atrasadas = int((df_filtrado['status_exibicao'] == 'Atrasado').sum())
    andamento = int((df_filtrado['status_exibicao'] == 'Em andamento').sum())
    estagnadas = int(df_filtrado['estagnada'].sum())
    taxa = round(concluidas / total * 100, 1) if total > 0 else 0

    metricas = [
        ('Total', str(total), RGBColor(0x75, 0x75, 0x75)),
        ('Concluídas', str(concluidas), COR_STATUS['Concluído']),
        ('Atrasadas', str(atrasadas), COR_STATUS['Atrasado']),
        ('Em andamento', str(andamento), COR_STATUS['Em andamento']),
        ('Estagnadas', str(estagnadas), RGBColor(0xB7, 0x1C, 0x1C)),
        ('Conclusão', f'{taxa}%', RGBColor(0xCC, 0x00, 0x00)),
    ]

    box_w, box_h, gap = Emu(1234440), Emu(823536), Emu(137160)
    x0, y0 = Emu(274320), Emu(1005840)
    for i, (label, valor, cor) in enumerate(metricas):
        x = x0 + i * (box_w + gap)
        card = resumo.shapes.add_shape(1, x, y0, box_w, box_h)  # 1 = MSO_SHAPE.RECTANGLE
        card.fill.solid()
        card.fill.fore_color.rgb = cor
        card.line.fill.background()
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Emu(0)
        p0 = tf.paragraphs[0]
        p0.alignment = PP_ALIGN.CENTER
        r0 = p0.add_run()
        r0.text = valor
        r0.font.size = Pt(20)
        r0.font.bold = True
        r0.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p1 = tf.add_paragraph()
        p1.alignment = PP_ALIGN.CENTER
        r1 = p1.add_run()
        r1.text = label
        r1.font.size = Pt(9)
        r1.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # gráfico de pizza (status)
    contagem = df_filtrado['status_exibicao'].value_counts()
    if len(contagem) == 0:
        contagem = pd.Series({'Sem ações no filtro': 1})
    chart_data = CategoryChartData()
    chart_data.categories = list(contagem.index)
    chart_data.add_series('Ações', list(contagem.values))
    gx, gy, gcx, gcy = Emu(274320), Emu(2011680), Emu(3840480), Emu(2560320)
    gframe = resumo.shapes.add_chart(XL_CHART_TYPE.PIE, gx, gy, gcx, gcy, chart_data)
    chart = gframe.chart
    chart.has_legend = True
    chart.legend.position = 2  # BOTTOM
    chart.legend.include_in_layout = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format = '0'
    plot.data_labels.number_format_is_linked = False
    for i, ponto in enumerate(plot.series[0].points):
        nome_status = list(contagem.index)[i]
        if nome_status in COR_STATUS:
            ponto.format.fill.solid()
            ponto.format.fill.fore_color.rgb = COR_STATUS[nome_status]

    # destaques de rastreabilidade à direita
    tx, ty, tcx, tcy = Emu(4342440), Emu(2011680), Emu(3969960), Emu(2560320)
    box = resumo.shapes.add_textbox(tx, ty, tcx, tcy)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = 'Rastreabilidade'
    r.font.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

    linhas_destaque = [
        f'⚠ {estagnadas} ação(ões) em andamento sem atualização há 7+ dias',
        f'🚨 {atrasadas} ação(ões) com status Atrasado',
    ]
    for linha in linhas_destaque:
        pp = tf.add_paragraph()
        pp.space_before = Pt(8)
        rr = pp.add_run()
        rr.text = linha
        rr.font.size = Pt(11)
        rr.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # ── Tabela(s) detalhada(s) ───────────────────────────────────
    colunas_cabecalho = ['Número', 'Responsável', 'Problema', 'Tipo', 'Plano de Ação', 'Status', 'Última Atualização']
    proporcoes = [0.06, 0.12, 0.205, 0.09, 0.205, 0.08, 0.20, 0.04]  # 8 colunas originais do template

    df_ordenado = df_filtrado.sort_values('numero')
    paginas = [df_ordenado.iloc[i:i + LINHAS_POR_PAGINA] for i in range(0, max(len(df_ordenado), 1), LINHAS_POR_PAGINA)]
    if len(df_ordenado) == 0:
        paginas = [df_ordenado]

    for pagina_i, pagina_df in enumerate(paginas):
        tabela_slide = duplicate_slide(prs, IDX_TABELA_BASE)
        remover_logo_uotz(tabela_slide)
        titulo_tab = next(s for s in tabela_slide.shapes if s.name == 'Google Shape;121;p13')
        sufixo = f' ({pagina_i + 1}/{len(paginas)})' if len(paginas) > 1 else ''
        set_text(titulo_tab, f'Plano de Ação — Detalhado{sufixo}')
        sub_tab = next((s for s in tabela_slide.shapes if s.has_text_frame and s.text_frame.text.strip() == 'xxxxxxxx'), None)
        if sub_tab:
            set_text(sub_tab, filtros_texto)

        tbl_shape = next(s for s in tabela_slide.shapes if s.has_table)
        tabela = tbl_shape.table
        n_linhas_dados = max(len(pagina_df), 1)

        rodape = next((s for s in tabela_slide.shapes if s.has_text_frame and 'plano completo' in s.text_frame.text), None)
        if rodape is not None:
            rodape._element.getparent().remove(rodape._element)

        # remove linhas extras que não serão usadas (mantém header + n_linhas_dados)
        while len(tabela.rows) - 1 > n_linhas_dados:
            tabela._tbl.remove(tabela._tbl.tr_lst[-1])

        # redistribui a largura das colunas para caber nosso conteúdo
        largura_total = tbl_shape.width
        for c, col in enumerate(tabela.columns):
            col.width = Emu(int(largura_total * proporcoes[c]))

        # header (linha 0)
        for c, texto in enumerate(colunas_cabecalho):
            set_text(tabela.cell(0, c), texto)
        set_text(tabela.cell(0, 7), '')

        # altura das linhas de dados: distribui o espaço restante uniformemente
        altura_header = tabela.rows[0].height
        altura_disponivel = tbl_shape.height - altura_header
        altura_linha = min(Pt(40), max(Pt(20), Emu(int(altura_disponivel / n_linhas_dados))))
        for r_i in range(1, len(tabela.rows)):
            tabela.rows[r_i].height = int(altura_linha)

        for r_i in range(n_linhas_dados):
            if r_i < len(pagina_df):
                row = pagina_df.iloc[r_i]
                partes_data = row['atualizado_em_fmt'].split(' ')
                data_curta = partes_data[0][:5] + (' ' + partes_data[1] if len(partes_data) > 1 else '')
                rastreio = data_curta
                if row['atualizado_por']:
                    rastreio += f"\n{truncar(row['atualizado_por'], 16)}"
                tipo_txt = TIPO_ABREV.get(row['tipo'], row['tipo'])
                valores = [
                    str(row['numero']),
                    truncar(row['responsavel'], 24),
                    truncar(row['problema_identificado'], 52),
                    truncar(tipo_txt, 22),
                    truncar(row['plano_de_acao'], 52),
                    row['status_exibicao'],
                    rastreio,
                    '',
                ]
            else:
                valores = [''] * 8
            for c, val in enumerate(valores):
                cell = tabela.cell(r_i + 1, c)
                set_text(cell, val)
                cell.text_frame.word_wrap = True
                for p in cell.text_frame.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(8)

    # ── Fechamento ────────────────────────────────────────────────
    # (slide de fechamento do template é 100% marca uotz — não incluído)

    # remove os slides originais de exemplo do template
    xml_slides = prs.slides._sldIdLst
    originais = list(xml_slides)[:TOTAL_SLIDES_ORIGINAIS]
    for sld in originais:
        xml_slides.remove(sld)

    prs.save(saida_path)
    return saida_path
