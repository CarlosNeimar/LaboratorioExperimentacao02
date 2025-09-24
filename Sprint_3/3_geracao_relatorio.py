import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import os


Path("graficos").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

def nome_repo(file_path: str) -> str:
    try:
        win_linux = file_path.replace('\\', '/')
        parts = win_linux.split('/')
        repo_index = parts.index('repos')
        return parts[repo_index + 1]
    except (ValueError, IndexError):
        return None

def gera_graficos(df: pd.DataFrame, output_dir: Path):

    print("  Gerando gráficos...")

    for col in ['stars_count', 'ck_loc', 'repo_age_years', 'ck_cbo', 'ck_dit', 'ck_lcom']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    sns.set_theme(style="whitegrid")

    # Gráfico 1: Estrelas vs. Linhas de Código (LOC)
    plt.figure(figsize=(12, 7))
    sns.scatterplot(data=df, x='stars_count', y='ck_loc', alpha=0.6)
    plt.xscale('log')
    plt.yscale('log')
    plt.title('Relação entre Estrelas e Linhas de Código (LOC)')
    plt.xlabel('Número de Estrelas (escala log)')
    plt.ylabel('Linhas de Código (LOC - escala log)')
    plt.grid(True, which="both", ls="--")
    plt.tight_layout()
    plt.savefig(output_dir / "stars_vs_loc.png")
    plt.close()
    print(f"  -> Gráfico 'stars_vs_loc.png' salvo em '{output_dir}'.")

    # Gráfico 2: Idade do Repositório vs. Complexidade CBO
    plt.figure(figsize=(12, 7))
    sns.scatterplot(data=df, x='repo_age_years', y='ck_cbo', alpha=0.6)
    plt.title('Relação entre Idade do Repositório e Complexidade (CBO)')
    plt.xlabel('Idade do Repositório (Anos)')
    plt.ylabel('Acoplamento Total (CBO)')
    plt.grid(True, ls="--")
    plt.tight_layout()
    plt.savefig(output_dir / "repo_age_vs_cbo.png")
    plt.close()
    print(f"  -> Gráfico 'repo_age_vs_cbo.png' salvo em '{output_dir}'.")

    # Gráfico 3: Top 10 Repositórios por LOC
    top_10_loc = df.nlargest(10, 'ck_loc')
    plt.figure(figsize=(12, 8))
    sns.barplot(data=top_10_loc, y="repo_name", x="ck_loc", palette="viridis")
    plt.title('Top 10 Repositórios por Linhas de Código (LOC)')
    plt.xlabel('Linhas de Código (LOC)')
    plt.ylabel('Repositório')
    plt.tight_layout()
    plt.savefig(output_dir / "top_10_by_loc.png")
    plt.close()
    print(f"  -> Gráfico 'top_10_by_loc.png' salvo em '{output_dir}'.")


def main():
    print("\n--- INICIANDO SCRIPT 3: Geração das análises ---")

    arq_class = Path("data/class.csv")
    arq_repo = Path("data/repos.csv")
    
    metricas_ck = Path("data/metricas.csv")
    arq_relatorio_file = Path("data/relatorio.xlsx")
    graficos_path = Path("graficos")

    if not arq_class.exists():
        print(f"ERRO FATAL: Arquivo '{arq_class}' não encontrado.")
        return

    if not arq_repo.exists():
        print(f"ERRO FATAL: Arquivo '{arq_repo}' não encontrado.")
        return

    print(f"\n[PASSO 1/4] Lendo e processando '{arq_class}'...")
    try:
        df_raw = pd.read_csv(arq_class)
        
        df_raw['repo_name'] = df_raw['file'].apply(nome_repo)
        
        df_raw.dropna(subset=['repo_name'], inplace=True)
        
        print(f"  -> Encontrados dados de {df_raw['repo_name'].nunique()} repositórios.")

        print("  -> Calculando métricas agregadas por repositório...")
        agg_functions = {
            'loc': ('loc', 'sum'),
            'cbo': ('cbo', 'sum'),
            'dit': ('dit', 'mean'),
            'lcom': ('lcom', 'mean'),
            'file': ('file', 'count')
        }
        df_ck_metrics = df_raw.groupby('repo_name').agg(**agg_functions).reset_index()

        df_ck_metrics.rename(columns={
            'loc': 'ck_loc',
            'cbo': 'ck_cbo',
            'dit': 'ck_dit',
            'lcom': 'ck_lcom',
            'file': 'java_files_count'
        }, inplace=True)
        
        df_ck_metrics.to_csv(metricas_ck, index=False)
        print(f"  -> Arquivo de métricas '{metricas_ck}' gerado com sucesso.")

    except Exception as e:
        print(f"ERRO FATAL ao processar o arquivo 'class.csv': {e}")
        return

    print(f"\n[PASSO 2/4] Unindo métricas com os dados de '{arq_repo}'...")
    try:
        df_repos_info = pd.read_csv(arq_repo)
        df_final = pd.merge(df_repos_info, df_ck_metrics, on="repo_name", how="inner")
        
        if df_final.empty:
            print("ERRO: Nenhum repositório em comum encontrado entre o arquivo de métricas e o arquivo do GitHub.")
            print("Verifique se os nomes dos repositórios extraídos correspondem aos do arquivo 'repositories.csv'.")
            return
            
        print(f"  -> {len(df_final)} repositórios correspondentes foram unidos.")

    except Exception as e:
        print(f"ERRO FATAL ao unir os dataframes: {e}")
        return

    print(f"\n[PASSO 3/4] Gerando relatório final em Excel...")
    try:
        column_order = [
            'full_name', 'repo_name', 'owner', 'stars_count', 'releases_count', 
            'repo_age_years', 'ck_loc', 'java_files_count', 'ck_cbo', 'ck_dit', 
            'ck_lcom', 'url'
        ]
        existing_columns = [col for col in column_order if col in df_final.columns]
        df_final_ordered = df_final[existing_columns]

        df_final_ordered.to_excel(arq_relatorio_file, index=False, engine='openpyxl')
        print(f"  -> Relatório final '{arq_relatorio_file}' salvo com sucesso.")
    except Exception as e:
        print(f"ERRO FATAL ao salvar o arquivo Excel: {e}")
        return
        
    print(f"\n[PASSO 4/4] Gerando os gráficos...")
    try:
        gera_graficos(df_final, graficos_path)
    except Exception as e:
        print(f"ERRO ao gerar os gráficos: {e}")

    print("\n--- Processo concluído com sucesso. ---")


if __name__ == "__main__":
    main()