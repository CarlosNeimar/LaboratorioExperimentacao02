# 1_collect_data.py
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any
import config

NUM_REPOS = 1000
PAGINACAO = 50
QUERY = """
query SearchMostPopularJavaRepos($queryString: String!, $first: Int!, $after: String) {
  search(query: $queryString, type: REPOSITORY, first: $first, after: $after) {
    repositoryCount
    pageInfo {
      endCursor
      hasNextPage
    }
    nodes {
      ... on Repository {
        name
        owner {
          login
        }
        url
        stargazerCount
        createdAt
        releases {
          totalCount
        }
      }
    }
  }
}
"""

def requisicao_graphql(query: str, variables: dict) -> Dict[str, Any]:
    """Executa uma query GraphQL na API do GitHub."""
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        config.GITHUB_API_URL,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise RuntimeError(f"Erro na query GraphQL: {payload['errors']}")
    return payload["data"]

def calcula_idade_repo(created_at_str: str) -> float:
    """Calcula a idade do repositório em anos"""
    created_at_dt = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    idade_dias = (now - created_at_dt).days
    return round(idade_dias / 365.25, 2)

def busca_repos_java(count: int) -> List[Dict[str, Any]]:
    """Busca os repositórios Java mais populares do GitHub."""
    todos_repos = []
    cursor = None
    has_next_page = True

    print(f"Buscando os {count} repositórios Java mais populares...")

    while has_next_page and len(todos_repos) < count:
        remaining_to_fetch = count - len(todos_repos)
        first = min(PAGINACAO, remaining_to_fetch)

        variables = {
            "queryString": "language:java sort:stars-desc",
            "first": first,
            "after": cursor
        }

        data = requisicao_graphql(QUERY, variables)
        search_data = data['search']
        
        for node in search_data['nodes']:
            if not node:
                continue
            
            repo_info = {
                "owner": node['owner']['login'],
                "repo_name": node['name'],
                "full_name": f"{node['owner']['login']}/{node['name']}",
                "url": node['url'],
                "stars_count": node['stargazerCount'],
                "releases_count": node['releases']['totalCount'],
                "repo_age_years": calcula_idade_repo(node['createdAt']),
            }
            todos_repos.append(repo_info)

        page_info = search_data['pageInfo']
        cursor = page_info['endCursor']
        has_next_page = page_info['hasNextPage']
        
        print(f"  {len(todos_repos)} de {count} repositórios coletados...")
        time.sleep(1)

    return todos_repos[:count]

def main():
    print("--- INICIANDO SCRIPT 1: COLETA DE DADOS ---")
    try:
        repos = busca_repos_java(NUM_REPOS)
        
        if not repos:
            print("Nenhum repositório foi encontrado.")
            return

        df = pd.DataFrame(repos)
        
        output_path = config.DATA_DIR / "repos.csv"
        df.to_csv(output_path, index=False)
        
        print(f"\nDados de {len(df)} repositórios salvos com sucesso em: {output_path}")
        print("--- SCRIPT 1: COLETA DE DADOS FINALIZADO ---")

    except Exception as e:
        print(f"\nERRO FATAL durante a coleta de dados: {e}")

if __name__ == "__main__":
    main()