# Scripts/getTop.py

import os
import csv
from github import Github
from github import RateLimitExceededException
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env que está na mesma pasta (Scripts)
load_dotenv()

# --- Configuração ---
# O token é lido do arquivo .env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# Número de repositórios que você deseja buscar.
TOTAL_REPOS_TO_FETCH = 1000

# --- NOVO: Caminho de saída dinâmico ---
# Constrói o caminho para o arquivo de saída na pasta 'results'
# 1. Pega o diretório do script atual (__file__) -> .../ioExperimentacao02/Scripts/
# 2. Volta um nível ('..') -> .../ioExperimentacao02/
# 3. Entra na pasta 'results' e define o nome do arquivo.
script_dir = os.path.dirname(__file__)
output_file_path = os.path.join(script_dir, '..', 'results', 'Top1000.csv')

# --- Fim da Configuração ---


def search_and_export_top_java_repos():
    """
    Busca os 1000 repositórios Java mais populares no GitHub e exporta para a pasta /results.
    """
    if not GITHUB_TOKEN:
        print("Erro: A variável de ambiente GITHUB_TOKEN não foi encontrada no seu arquivo .env.")
        print("Certifique-se de que o arquivo .env está na pasta 'Scripts'.")
        return

    try:
        print("Conectando à API do GitHub com autenticação...")
        g = Github(GITHUB_TOKEN)
        
        query = "language:java sort:stars"
        repositories = g.search_repositories(query=query)
        
        print(f"Buscando os {TOTAL_REPOS_TO_FETCH} repositórios Java mais populares...")

        repo_data_list = []
        count = 0
        
        for repo in repositories:
            if count >= TOTAL_REPOS_TO_FETCH:
                break
            
            repo_data_list.append({
                'rank': count + 1,
                'full_name': repo.full_name,
                'stars': repo.stargazers_count,
                'url': repo.html_url,
                'description': repo.description,
                'language': repo.language
            })
            
            print(f"Coletado {count + 1}/{TOTAL_REPOS_TO_FETCH}: {repo.full_name}")
            count += 1
        
        # Garante que o diretório de resultados exista antes de salvar
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        print(f"\nBusca concluída. Exportando dados para o arquivo '{output_file_path}'...")
        
        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rank', 'full_name', 'stars', 'url', 'description', 'language']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(repo_data_list)

        print(f"Arquivo salvo com sucesso em '{output_file_path}'!")

    except RateLimitExceededException:
        rate_limit = g.get_rate_limit()
        reset_time = rate_limit.core.reset.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\nErro: Limite de taxa da API do GitHub excedido. Tente novamente após: {reset_time}")
    except Exception as e:
        print(f"\nOcorreu um erro inesperado: {e}")

if __name__ == "__main__":
    search_and_export_top_java_repos()