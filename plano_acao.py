"""
PASSO 2: Migrar dados do Excel para o Supabase
Rode este script na sua máquina local (com pip install supabase pandas openpyxl)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client

# ============================
# CONFIGURAÇÃO
# ============================
SUPABASE_URL = "https://yjvhfhodhlxgprpxelxs.supabase.co"
SUPABASE_KEY = "sb_publishable__9zxgNOmlVufr15sCENQbQ_RhIF35Np"
ARQUIVO_EXCEL = "plano_acao.xlsx"   # coloque o arquivo na mesma pasta

# ============================
# LER EXCEL
# ============================
df = pd.read_excel(ARQUIVO_EXCEL, sheet_name="🗂 Base")
df.columns = ['numero', 'origem', 'data_entrada', 'problema_identificado',
              'plano_de_acao', 'responsavel', 'prazo', 'data_finalizacao',
              'status', 'dias_atraso', 'no_prazo']

def clean_val(v):
    if pd.isna(v) or v is None:
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime('%Y-%m-%d')
    if isinstance(v, (float, np.floating)):
        if np.isnan(v): return None
        return int(v) if v == int(v) else float(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    return str(v).strip()

records = []
for _, row in df.iterrows():
    r = {col: clean_val(row[col]) for col in df.columns}
    r['comentario'] = None
    r['atualizado_por'] = None
    records.append(r)

# ============================
# ENVIAR PARA SUPABASE
# ============================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"Enviando {len(records)} registros para o Supabase...")

# Limpar tabela antes de inserir (evita duplicatas)
supabase.table("plano_acao").delete().neq("id", 0).execute()
print("Tabela limpa. Inserindo dados...")

# Inserir em lotes de 20
batch_size = 20
for i in range(0, len(records), batch_size):
    batch = records[i:i+batch_size]
    result = supabase.table("plano_acao").insert(batch).execute()
    print(f"  Inseridos registros {i+1} a {min(i+batch_size, len(records))}")

print("\n✅ Migração concluída com sucesso!")
print(f"Total: {len(records)} registros no Supabase")
