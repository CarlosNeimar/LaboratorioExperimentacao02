import os
import csv
from github import Github
from github import RateLimitExceededException
from dotenv import load_dotenv
import time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração ---
# O token agora é lido diretamente do arquivo .env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# Número de repositórios que você deseja buscar.
TOTAL_REPOS_TO_FETCH = 1000
CSV_FILENAME = "Top1000.csv"

# --- Fim da Configuração ---


def search_and_export_top_java_repos():
    """
    Busca os 1000 repositórios Java mais populares no GitHub e exporta para um arquivo CSV.
    """
    if not GITHUB_TOKEN:
        print("Erro: A variável de ambiente GITHUB_TOKEN não foi encontrada.")
        print("Por favor, crie um arquivo .env e adicione seu token nele (ex: GITHUB_TOKEN='seu_token').")
        return

    try:
        print("Conectando à API do GitHub com autenticação...")
        g = Github(GITHUB_TOKEN)
        
        # A query de busca: filtra por linguagem 'java', ordena por estrelas
        query = "language:java sort:stars"
        
        repositories = g.search_repositories(query=query)
        
        print(f"Buscando os {TOTAL_REPOS_TO_FETCH} repositórios Java mais populares...")

        repo_data_list = []
        count = 0
        
        for repo in repositories:
            if count >= TOTAL_REPOS_TO_FETCH:
                break
            
            # Adiciona os dados do repositório a uma lista
            repo_data_list.append({
                'rank': count + 1,
                'full_name': repo.full_name,
                'stars': repo.stargazers_count,
                'url': repo.html_url,
                'description': repo.description,
                'language': repo.language
            })
            
            # Imprime o progresso no terminal
            print(f"Coletado {count + 1}/{TOTAL_REPOS_TO_FETCH}: {repo.full_name}")
            
            count += 1
        
        # Escreve os dados coletados em um arquivo CSV
        print(f"\nBusca concluída. Exportando dados para o arquivo '{CSV_FILENAME}'...")
        
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            # Define os nomes das colunas (cabeçalho)
            fieldnames = ['rank', 'full_name', 'stars', 'url', 'description', 'language']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()  # Escreve o cabeçalho
            writer.writerows(repo_data_list) # Escreve todas as linhas de dados

        print(f"Arquivo '{CSV_FILENAME}' criado com sucesso!")

    except RateLimitExceededException:
        rate_limit = g.get_rate_limit()
        reset_time = rate_limit.core.reset.strftime('%Y-%m-%d %H:%M:%S')
        print("\nErro: Limite de taxa da API do GitHub excedido.")
        print(f"Tente novamente após: {reset_time}")
    except Exception as e:
        print(f"\nOcorreu um erro inesperado: {e}")

if __name__ == "__main__":
    search_and_export_top_java_repos()