from datetime import datetime
import math

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

COR_VERMELHO = RGBColor(192, 0, 0)
COR_VERDE = RGBColor(112, 173, 71)
COR_LARANJA = RGBColor(244, 177, 131)
COR_CINZA = RGBColor(127, 127, 127)
COR_CINZA_CLARO = RGBColor(230, 230, 230)


def gerar_ppt(template_path, df_filtrado, filtros_texto, saida_path):

    prs = Presentation()

    # ==========================
    # CAPA
    # ==========================

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(
        Inches(1),
        Inches(1.5),
        Inches(7),
        Inches(1)
    )

    titulo.text_frame.text = "Plano de Ação\nPortabilidade"

    for p in titulo.text_frame.paragraphs:
        p.alignment = PP_ALIGN.LEFT
        for run in p.runs:
            run.font.size = Pt(28)
            run.font.bold = True
            run.font.name = "AMX"
            run.font.color.rgb = COR_VERMELHO

    sub = slide.shapes.add_textbox(
        Inches(1),
        Inches(3),
        Inches(5),
        Inches(0.5)
    )

    sub.text_frame.text = (
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    # ==========================
    # RESUMO
    # ==========================

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    titulo = slide.shapes.add_textbox(
        Inches(0.5),
        Inches(0.3),
        Inches(4),
        Inches(0.5)
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

    estagnadas = int(
        df_filtrado["estagnada"].sum()
    ) if len(df_filtrado) > 0 else 0

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

    for i, (titulo_card, valor, cor) in enumerate(cards):

        x = 0.4 + (i * 1.6)

        card = slide.shapes.add_textbox(
            Inches(x),
            Inches(1),
            Inches(1.4),
            Inches(0.7)
        )

        card.fill.solid()
        card.fill.fore_color.rgb = cor

        tf = card.text_frame
        tf.text = f"{valor}\n{titulo_card}"

    # ==========================
    # TABELAS POR STATUS
    # ==========================

    status_ordem = [
        "Atrasado",
        "Em andamento",
        "Concluído"
    ]

    linhas_por_slide = 5

    for status in status_ordem:

        df_status = df_filtrado[
            df_filtrado["status_exibicao"] == status
        ]

        if len(df_status) == 0:
            continue

        paginas = math.ceil(
            len(df_status) / linhas_por_slide
        )

        for pagina in range(paginas):

            slide = prs.slides.add_slide(
                prs.slide_layouts[6]
            )

            titulo = slide.shapes.add_textbox(
                Inches(0.3),
                Inches(0.2),
                Inches(6),
                Inches(0.4)
                        titulo.text_frame.text = (
                f"Ações {status} ({pagina+1}/{paginas})"
            )

            for p in titulo.text_frame.paragraphs:
                for run in p.runs:
                    run.font.name = "AMX"
                    run.font.size = Pt(18)
                    run.font.bold = True

            inicio = pagina * linhas_por_slide
            fim = inicio + linhas_por_slide

        
            fim = inicio + linhas_por_slide

            df_pagina = df_status.iloc[inicio:fim]

            tabela = slide.shapes.add_table(
                len(df_pagina) + 1,
                6,
                Inches(0.15),
                Inches(0.8),
                Inches(9.5),
                Inches(4.5)
            ).table

            tabela.columns[0].width = Inches(0.7)
            tabela.columns[1].width = Inches(1.3)
            tabela.columns[2].width = Inches(2.2)
            tabela.columns[3].width = Inches(2.2)
            tabela.columns[4].width = Inches(1.1)
            tabela.columns[5].width = Inches(1.5)

            headers = [
                "Número",
                "Tipo",
                "Problema",
                "Plano de Ação",
                "Status",
                "Última Atualização"
            ]

            for c, h in enumerate(headers):

                cell = tabela.cell(0, c)
                cell.text = h

                cell.fill.solid()
                cell.fill.fore_color.rgb = COR_VERMELHO

                for p in cell.text_frame.paragraphs:

                    p.alignment = PP_ALIGN.CENTER

                    for run in p.runs:
                        run.font.bold = True
                        run.font.size = Pt(10)
                        run.font.name = "AMX"
                        run.font.color.rgb = RGBColor(
                            255,
                            255,
                            255
                        )

            for r, (_, row) in enumerate(
                df_pagina.iterrows(),
                start=1
            ):

                valores = [
                    str(row["numero"]),
                    str(row["tipo"]),
                    str(row["problema_identificado"])[:50],
                    str(row["plano_de_acao"])[:50],
                    str(row["status_exibicao"]),
                    str(row["atualizado_em_fmt"])
                ]

                for c, valor in enumerate(valores):

                    cell = tabela.cell(r, c)

                    cell.text = valor

                    cell.fill.solid()
                    cell.fill.fore_color.rgb = COR_CINZA_CLARO

    prs.save(saida_path)

    return saida_path
