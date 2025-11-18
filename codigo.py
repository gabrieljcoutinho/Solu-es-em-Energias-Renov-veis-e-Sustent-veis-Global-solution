# analise_simulacao_brasil.py
import pandas as pd
import matplotlib.pyplot as plt
import os

# ---------- Config ----------
RESULTS_CSV = "Resultados_Simulacao_Brasil.csv"   # arquivo que você já gerou
WORLD_CSV = "World Energy Consumption.csv"       # opcional: dataset original (se disponível)
OUTPUT_FOLDER = "output_results"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ---------- Funções utilitárias ----------
def safe_read_csv(path):
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)

# ---------- 1) Carregar CSV de resultados ----------
df_res = safe_read_csv(RESULTS_CSV)
if df_res is None:
    raise FileNotFoundError(f"Arquivo '{RESULTS_CSV}' não encontrado na pasta atual.")

print("Colunas em Results CSV:", df_res.columns.tolist())
print("\nAmostra do arquivo de resultados:")
print(df_res.head())

# Verificar colunas esperadas
expected_cols = ["Ano", "Consumo Atual (TWh)", "Consumo com Renováveis (TWh)", "CO2 Evitado (milhões ton)"]
for c in expected_cols:
    if c not in df_res.columns:
        print(f"AVISO: coluna esperada ausente: {c}")

# ---------- 2) Se faltarem consumos, tentar reconstruir usando o dataset mundial (opcional) ----------
df_world = safe_read_csv(WORLD_CSV)
if df_world is not None:
    print("\nDataset mundial encontrado — usaremos para preencher consumos, se necessário.")
    # suposições sobre colunas no dataset mundial (ajuste se precisar)
    # Ex.: df_world tem country, year, primary_energy_consumption
    if 'country' in df_world.columns and 'year' in df_world.columns and 'primary_energy_consumption' in df_world.columns:
        # criar dicionário ano->consumo (TWh) para o Brasil
        br = df_world[df_world['country'].str.lower() == 'brazil']
        consumo_por_ano = br.set_index('year')['primary_energy_consumption'].to_dict()
    else:
        print("AVISO: o dataset mundial não contém as colunas esperadas para preencher consumo (country, year, primary_energy_consumption).")
        consumo_por_ano = {}
else:
    consumo_por_ano = {}

# Função para preencher uma coluna a partir do world dataset
def preencher_consumo(row):
    ano = int(row['Ano'])
    if pd.notna(row.get('Consumo Atual (TWh)')):
        return row['Consumo Atual (TWh)']
    return consumo_por_ano.get(ano, pd.NA)

# Preencher 'Consumo Atual (TWh)' se possível
if 'Consumo Atual (TWh)' in df_res.columns:
    if df_res['Consumo Atual (TWh)'].isna().any():
        if consumo_por_ano:
            df_res['Consumo Atual (TWh)'] = df_res.apply(preencher_consumo, axis=1)
            print("Preenchimento de 'Consumo Atual (TWh)' concluído (onde possível).")
        else:
            print("Não foi possível preencher 'Consumo Atual (TWh)': dataset mundial ausente ou sem colunas esperadas.")

# Se a coluna 'Consumo com Renováveis (TWh)' estiver ausente ou vazia, e se tivermos 'Consumo Atual' podemos calcular
if 'Consumo com Renováveis (TWh)' not in df_res.columns:
    df_res['Consumo com Renováveis (TWh)'] = pd.NA

if 'Consumo Atual (TWh)' in df_res.columns and df_res['Consumo com Renováveis (TWh)'].isna().all():
    # se todas vazias, tentar reconstruir assumindo percentual (30%)
    percentual_default = 0.30
    if df_res['Consumo Atual (TWh)'].notna().any():
        df_res['Consumo com Renováveis (TWh)'] = df_res['Consumo Atual (TWh)'] * (1 - percentual_default)
        print(f"Coluna 'Consumo com Renováveis (TWh)' preenchida com suposição de {int(percentual_default*100)}% de renováveis (onde aplicável).")
    else:
        print("Não há dados de 'Consumo Atual (TWh)' para derivar 'Consumo com Renováveis (TWh)'.")

# ---------- 3) Cálculos principais ----------
# converter colunas numéricas
def to_numeric_col(df, col):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

to_numeric_col(df_res, 'Consumo Atual (TWh)')
to_numeric_col(df_res, 'Consumo com Renováveis (TWh)')
to_numeric_col(df_res, 'CO2 Evitado (milhões ton)')

# métricas
media_consumo = df_res['Consumo Atual (TWh)'].mean() if 'Consumo Atual (TWh)' in df_res.columns else None
co2_total = df_res['CO2 Evitado (milhões ton)'].sum()

print("\nMétrica calculada:")
print("Média de consumo (TWh):", media_consumo)
print("CO2 evitado total (milhões ton):", co2_total)

# ---------- 4) Gráficos ----------
plt.close('all')
fig, ax = plt.subplots(figsize=(10,6))
if 'Consumo Atual (TWh)' in df_res.columns:
    ax.plot(df_res['Ano'], df_res['Consumo Atual (TWh)'], label='Consumo Atual (TWh)', linewidth=2)
if 'Consumo com Renováveis (TWh)' in df_res.columns:
    ax.plot(df_res['Ano'], df_res['Consumo com Renováveis (TWh)'], linestyle='--', label='Consumo com Renováveis (TWh)', linewidth=2)

ax.set_title('Consumo Atual vs Consumo com Renováveis (Brasil)')
ax.set_xlabel('Ano')
ax.set_ylabel('Energia (TWh)')
ax.legend()
ax.grid(True)
plt.tight_layout()
graph_path = os.path.join(OUTPUT_FOLDER, 'consumo_comparacao.png')
plt.savefig(graph_path)
print(f"Gráfico salvo: {graph_path}")

# Gráfico CO2 evitado por ano
if 'CO2 Evitado (milhões ton)' in df_res.columns:
    plt.figure(figsize=(10,5))
    plt.bar(df_res['Ano'], df_res['CO2 Evitado (milhões ton)'])
    plt.title('CO2 Evitado por Ano (milhões de toneladas)')
    plt.xlabel('Ano')
    plt.ylabel('CO2 Evitado (milhões ton)')
    plt.grid(axis='y')
    co2_path = os.path.join(OUTPUT_FOLDER, 'co2_evitado_por_ano.png')
    plt.tight_layout()
    plt.savefig(co2_path)
    print(f"Gráfico salvo: {co2_path}")

# ---------- 5) Exportar resultados completos ----------
out_csv = os.path.join(OUTPUT_FOLDER, 'Resultados_Simulacao_Brasil_completos.csv')
df_res.to_csv(out_csv, index=False)
print(f"Arquivo de resultados completo salvo em: {out_csv}")

# Exportar resumo em texto
summary_txt = os.path.join(OUTPUT_FOLDER, 'resumo_relatorio.txt')
with open(summary_txt, 'w', encoding='utf-8') as f:
    f.write("Resumo da Análise - Resultados Simulação Brasil\n\n")
    f.write(f"Média de Consumo (TWh): {media_consumo}\n")
    f.write(f"CO2 evitado total (milhões ton): {co2_total}\n\n")
    f.write("Tabela final:\n")
    f.write(df_res.to_string(index=False))
print(f"Resumo em texto salvo em: {summary_txt}")

print("\nProcesso concluído. Verifique a pasta 'output_results' para arquivos gerados (gráficos e CSV).")
