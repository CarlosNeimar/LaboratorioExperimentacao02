import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import numpy as np

def load_and_merge_data(metrics_path='./data/metricas.csv', repos_path='./data/repos.csv'):
    try:
        df_metrics = pd.read_csv(metrics_path)
        df_repos = pd.read_csv(repos_path)
    except FileNotFoundError as e:
        print(f"Erro: Arquivo não encontrado - {e}")
        return None

    df_metrics.rename(columns={'repositorio': 'repo_name'}, inplace=True)
    df_full = pd.merge(df_repos, df_metrics, on='repo_name', how='inner')
    df_full = df_full[df_full['arquivos_java'] > 0].copy()

    # Normaliza as métricas de qualidade pelo número de arquivos
    df_full['cbo_avg'] = df_full['cbo_total'] / df_full['arquivos_java']
    df_full['dit_avg'] = df_full['dit_total'] / df_full['arquivos_java']
    df_full['lcom_avg'] = df_full['lcom_total'] / df_full['arquivos_java']
    
    df_full.rename(columns={
        'stars_count': 'Popularidade (estrelas)',
        'repo_age_years': 'Maturidade (anos)',
        'releases_count': 'Atividade (releases)',
        'loc_total': 'Tamanho (LOC)',
        'comentarios_total': 'Tamanho (Comentários)'
    }, inplace=True)

    print("Dados carregados e processados com sucesso.")
    print(f"Número de repositórios na análise: {len(df_full)}")
    
    return df_full

def generate_descriptive_stats(df, process_cols, quality_cols):

    if df is None:
        return
    
    stats = df[process_cols + quality_cols].describe().transpose()
    stats_view = stats[['mean', '50%', 'std', 'min', 'max']].rename(columns={'50%': 'median'})
    
    print("\n--- Tabela 1: Estatísticas Descritivas ---")
    print(stats_view.to_markdown())

def generate_correlation_heatmap(df, cols_for_corr):

    if df is None:
        return
        
    short_names_map = {
        'Popularidade (estrelas)': 'Popularidade',
        'Maturidade (anos)': 'Maturidade',
        'Atividade (releases)': 'Atividade',
        'Tamanho (LOC)': 'Tamanho (LOC)',
        'Tamanho (Comentários)': 'Comentários',
        'cbo_avg': 'CBO Médio',
        'dit_avg': 'DIT Médio',
        'lcom_avg': 'LCOM Médio'
    }
    df_corr = df[cols_for_corr].rename(columns=short_names_map)
    corr_matrix = df_corr.corr(method='spearman')
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5, annot_kws={"size": 10})
    plt.title('Matriz de Correlação de Spearman', fontsize=18, pad=20)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    plt.tight_layout()
    plt.savefig('heatmap.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("\nHeatmap de correlação salvo como 'heatmap.png'")

def plot_combined_research_questions(df, rq_pairs, filename):

    if df is None:
        return

    num_rows = len(rq_pairs)
    fig, axes = plt.subplots(num_rows, 3, figsize=(20, 6 * num_rows), squeeze=False)
    
    quality_metrics = ['cbo_avg', 'dit_avg', 'lcom_avg']
    y_labels = ['CBO Médio', 'DIT Médio', 'LCOM Médio']

    for row_idx, (rq_title, params) in enumerate(rq_pairs.items()):
        x_var = params['x_var']
        x_scale = params['x_scale']
        
        for col_idx, y_var in enumerate(quality_metrics):
            ax = axes[row_idx, col_idx]
            sns.scatterplot(data=df, x=x_var, y=y_var, ax=ax, alpha=0.6, s=50)
            
            title = f'{rq_title}: {y_labels[col_idx]} vs. {params["x_label"]}'
            ax.set_title(title, fontsize=12)
            ax.set_xlabel(params['x_label'], fontsize=10)
            ax.set_ylabel(y_labels[col_idx], fontsize=10)
            
            if x_scale:
                ax.set_xscale(x_scale, **params.get('x_scale_params', {}))
            
            # Aplica escala logarítmica para LCOM devido à sua alta variância
            if y_var == 'lcom_avg':
                ax.set_yscale('symlog', linthresh=1)

    plt.tight_layout(pad=3.0)
    plt.savefig(filename, dpi=300)
    plt.show()
    print(f"Gráficos combinados salvos como '{filename}'")


if __name__ == '__main__':
    sns.set_theme(style="whitegrid", palette="viridis")

    df_analysis = load_and_merge_data()

    if df_analysis is not None:
        process_cols = ['Popularidade (estrelas)', 'Maturidade (anos)', 'Atividade (releases)', 'Tamanho (LOC)', 'Tamanho (Comentários)']
        quality_cols = ['cbo_avg', 'dit_avg', 'lcom_avg']

        # 1. Gerar estatísticas descritivas
        generate_descriptive_stats(df_analysis, process_cols, quality_cols)

        # 2. Gerar heatmap de correlação
        generate_correlation_heatmap(df_analysis, process_cols + quality_cols)

        # 3. Gerar gráficos para as questões de pesquisa
        
        # Gráficos para QP01 e QP02
        rq1_rq2_pairs = {
            'QP01': {
                'x_var': 'Popularidade (estrelas)', 
                'x_label': 'Popularidade (Estrelas)', 
                'x_scale': 'log'
            },
            'QP02': {
                'x_var': 'Maturidade (anos)', 
                'x_label': 'Maturidade (Anos)', 
                'x_scale': None
            }
        }
        plot_combined_research_questions(df_analysis, rq1_rq2_pairs, 'rq1_rq2_plots.png')

        # Gráficos para QP03 e QP04
        rq3_rq4_pairs = {
            'QP03': {
                'x_var': 'Atividade (releases)', 
                'x_label': 'Atividade (Releases)', 
                'x_scale': 'symlog', 
                'x_scale_params': {'linthresh': 1}
            },
            'QP04': {
                'x_var': 'Tamanho (LOC)', 
                'x_label': 'Tamanho (Linhas de Código)', 
                'x_scale': 'log'
            }
        }
        plot_combined_research_questions(df_analysis, rq3_rq4_pairs, 'rq3_rq4_plots.png')