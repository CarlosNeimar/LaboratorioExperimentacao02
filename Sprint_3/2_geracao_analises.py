# 2_analyze_repos.py
import os
import shutil
import stat
import subprocess
import pandas as pd
from pathlib import Path
import config

def remove_clone_repo(path_repo: Path):
    """Remove o diretório do repositório clonado para liberar espaço."""
    def rm(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if not path_repo.exists():
        return
    
    print(f"  Removendo {path_repo.name} para liberar espaço...")
    try:
        shutil.rmtree(path_repo, onerror=rm)
    except Exception as e:
        print(f"  AVISO: Não foi possível remover o repositório {path_repo.name}. Erro: {e}")


def clone_repo(repo_url: str, dest_folder: Path) -> Path:
    """Clone com shallow"""

    nome_repo = repo_url.rstrip("/").split("/")[-1]
    path_repo = dest_folder / nome_repo

    if path_repo.exists():
        print(f"  Repositório '{nome_repo}' já existe. Pulando clone.")
        return path_repo

    print(f"  Clonando {nome_repo} (shallow clone)...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(path_repo)],
            check=True, capture_output=True, text=True, timeout=300
        )
        return path_repo
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Falha ao clonar {nome_repo}: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout ao clonar {nome_repo}.")
    

def run_ck_analysis(path_repo: Path) -> bool:
    """Executa a análise do CK em um repositório clonado e captura logs."""
    shutil.rmtree(config.PATH_OUTPUT_CK, ignore_errors=True)
    config.PATH_OUTPUT_CK.mkdir()

    print(f"  Executando CK em {path_repo.name}...")
    java_files = list(path_repo.rglob("*.java"))
    if not java_files:
        print("  AVISO: Nenhum arquivo .java encontrado.")
        return False

    cmd = [
        str(config.JAVA_PATH), "-jar", str(config.PATH_CK_JAR),
        str(path_repo), "true", "0", "true", str(config.PATH_OUTPUT_CK)
    ]

    logs_dir = config.DATA_DIR / "ck_logs"
    logs_dir.mkdir(exist_ok=True)
    log_file_path = logs_dir / f"{path_repo.name}-ck.log"

    try:
        with open(log_file_path, 'w') as log_file:
            result = subprocess.run(
                cmd, check=True, text=True, timeout=600,
                stdout=log_file, stderr=subprocess.STDOUT
            )
        
        class_csv_path = config.PATH_OUTPUT_CK / "class.csv"
        if class_csv_path.exists() and class_csv_path.stat().st_size > 0:
            print(f"  Análise CK concluída com sucesso para {path_repo.name}.")
            return True
        else:
            print(f"  AVISO: Análise CK executada, mas 'class.csv' não foi gerado ou está vazio. Verifique o log em: {log_file_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"  ERRO ao executar o CK em {path_repo.name}. O processo retornou um erro. Verifique o log em: {log_file_path}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ERRO: Timeout ao executar o CK em {path_repo.name}. O projeto pode ser muito grande.")
        with open(log_file_path, 'a') as log_file:
            log_file.write("\n\n--- TIMEOUT ---")
        return False


def process_ck_results(nome_repo: str) -> dict:
    """Processa o arquivo 'class.csv' gerado pelo CK e retorna as métricas agregadas."""
    class_csv_path = config.PATH_OUTPUT_CK / "class.csv"
    try:
        df = pd.read_csv(class_csv_path)
        if df.empty:
            return {}
        
        # Remove colunas não utilizadas
        df = df[["cbo", "dit", "lcom", "loc"]]

        metrics = {
            "nome_repo": nome_repo,
            "ck_cbo": df["cbo"].sum(),
            "ck_dit": df["dit"].mean(),
            "ck_lcom": df["lcom"].mean(),
            "ck_loc": df["loc"].sum(),
            "java_files_count": len(df)
        }
        return metrics
    except FileNotFoundError:
        print(f"  AVISO: 'class.csv' não encontrado para {nome_repo}.")
        return {}
    except Exception as e:
        print(f"  ERRO ao processar resultados do CK para {nome_repo}: {e}")
        return {}


def main():
    print("\n--- INICIANDO SCRIPT 2: ANÁLISE COM CK ---")
    
    arq_repos = config.DATA_DIR / "repos.csv"
    if not arq_repos.exists():
        print(f"ERRO: Arquivo com os repositórios '{arq_repos}' não encontrado.")
        return

    repositorios = pd.read_csv(arq_repos)
    metricas = []
    
    total_repos = len(repositorios)
    for index, repo in repositorios.iterrows():
        nome_repo = repo["nome_repo"]
        repo_url = repo["url"]
        print(f"\n[ Processando {index + 1}/{total_repos} ]: {repo['full_name']} ")
        
        path_repo = None
        try:
            path_repo = clone_repo(repo_url, config.PATH_REPOSITORIES)
            
            if run_ck_analysis(path_repo):
                ck_metrics = process_ck_results(nome_repo)
                if ck_metrics:
                    metricas.append(ck_metrics)
                    print(f"  Métricas de {nome_repo} processadas com sucesso.")
            else:
                print(f"  Análise CK falhou ou não gerou resultados para {nome_repo}.")

        except Exception as e:
            print(f"  ERRO GERAL ao processar o repositório {nome_repo}: {e}")
        finally:
            if path_repo:
                remove_clone_repo(path_repo)
    
    if not metricas:
        print("\nNenhuma métrica do CK foi gerada.")
    else:
        df_metricas_ck = pd.DataFrame(metricas)
        output_path = config.DATA_DIR / "metricas.csv"
        df_metricas_ck.to_csv(output_path, index=False)
        print(f"\n{len(df_metricas_ck)} repositórios analisados com sucesso.")
        print(f"Métricas do CK salvas em: {output_path}")

    print("--- SCRIPT 2: ANÁLISE COM CK FINALIZADO ---")

if __name__ == "__main__":
    main()