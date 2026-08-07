from datetime import datetime
import math

import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


COR_VERMELHO = RGBColor(192, 0, 0)
COR_VERDE = RGBColor(76, 175, 80)
COR_LARANJA = RGBColor(255, 152, 0)
COR_CINZA = RGBColor(100, 100, 100)


def gerar_ppt(template_path, df_filtrado, filtros_texto, saida_path):

    prs = Presentation()

    # ==================================================
    # CAPA
    # ==================================================

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(
        Inches(1),
        Inches(1.5),
        Inches(8),
        Inches(1)
    )

    titulo.text_frame.text = "Plano de Ação\nPortabilidade"

    p = titulo.text_frame.paragraphs[0]
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = COR_VERMELHO

    sub = slide.shapes.add_textbox(
        Inches(1),
        Inches(3),
        Inches(6),
        Inches(0.5)
    )

    sub.text_frame.text = (
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    # ==================================================
    # RESUMO
    # ==================================================

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(
        Inches(0.3),
        Inches(0.2),
        Inches(5),
        Inches(0.4)
    )

    titulo.text_frame.text = "Resumo Executivo"

    total = len(df_filtrado)
    concluidas = len(
        df_filtrado[
            df_filtrado["status_exibicao"] == "Concluído"
        ]
    )

    atrasadas = len(
        df_filtrado[
            df_filtrado["status_exibicao"] == "Atrasado"
        ]
    )

    andamento = len(
        df_filtrado[
            df_filtrado["status_exibicao"] == "Em andamento"
        ]
    )

    estagnadas = int(df_filtrado["estagnada"].sum())

    taxa = (
        round(concluidas / total * 100, 1)
        if total > 0 else 0
    )

    cards = [
        ("Total", total, COR_CINZA),
        ("Concluídas", concluidas, COR_VERDE),
        ("Atrasadas", atrasadas, COR_VERMELHO),
        ("Em andamento", andamento, COR_LARANJA),
        ("Estagnadas", estagnadas, COR_VERMELHO),
        ("Taxa", f"{taxa}%", COR_VERMELHO),
    ]

    inicio_x = 0.3
    largura = 1.4

    for i, (titulo_card, valor, cor) in enumerate(cards):

        card = slide.shapes.add_textbox(
            Inches(inicio_x + (i * 1.5)),
            Inches(1),
            Inches(largura),
            Inches(0.8)
        )

        card.fill.solid()
        card.fill.fore_color.rgb = cor

        tf = card.text_frame
        tf.text = f"{valor}\n{titulo_card}"

    # ==================================================
    # TABELAS
    # ==================================================

    linhas_por_slide = 10

    paginas = math.ceil(
        max(len(df_filtrado), 1) / linhas_por_slide
    )

    for pagina in range(paginas):

        slide = prs.slides.add_slide(
            prs.slide_layouts[6]
        )

        titulo = slide.shapes.add_textbox(
            Inches(0.3),
            Inches(0.2),
            Inches(5),
            Inches(0.4)
        )

        titulo.text_frame.text = (
            f"Plano de Ação - Detalhado "
            f"({pagina+1}/{paginas})"
        )

        inicio = pagina * linhas_por_slide
        fim = inicio + linhas_por_slide

        df_pagina = df_filtrado.iloc[inicio:fim]

        rows = len(df_pagina) + 1
        cols = 6

        tabela = slide.shapes.add_table(
            rows,
            cols,
            Inches(0.2),
            Inches(1),
            Inches(9),
            Inches(4)
        ).table

        headers = [
            "Número",
            "Tipo",
            "Problema",
            "Plano de Ação",
            "Status",
            "Última Atualização"
        ]

        for c, h in enumerate(headers):
            tabela.cell(0, c).text = h

        for r, (_, row) in enumerate(
            df_pagina.iterrows(),
            start=1
        ):

            tabela.cell(r, 0).text = str(
                row["numero"]
            )

            tabela.cell(r, 1).text = str(
                row["tipo"]
            )

            tabela.cell(r, 2).text = str(
                row["problema_identificado"]
            )[:100]

            tabela.cell(r, 3).text = str(
                row["plano_de_acao"]
            )[:100]

            tabela.cell(r, 4).text = str(
                row["status_exibicao"]
            )

            tabela.cell(r, 5).text = str(
                row["atualizado_em_fmt"]
            )

    prs.save(saida_path)

    return saida_path
