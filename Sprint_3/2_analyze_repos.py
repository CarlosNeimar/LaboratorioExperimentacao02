# 2_analyze_repos.py (VERSÃO MELHORADA)
import os
import shutil
import stat
import subprocess
import pandas as pd
from pathlib import Path
from typing import List

# Importa as configurações centralizadas
import config

def safe_remove_repository(repo_path: Path):
    """Remove um diretório de repositório de forma segura, lidando com arquivos somente leitura do Git."""
    def remove_readonly(func, path, _):
        """Muda a permissão e tenta novamente."""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if not repo_path.exists():
        return
    
    print(f"  Removendo {repo_path.name} para liberar espaço...")
    try:
        shutil.rmtree(repo_path, onerror=remove_readonly)
    except Exception as e:
        print(f"  AVISO: Não foi possível remover o repositório {repo_path.name}. Erro: {e}")

def clone_repository(repo_url: str, dest_folder: Path) -> Path:
    """Clona um repositório usando shallow clone (--depth 1) para otimização."""
    repo_name = repo_url.rstrip("/").split("/")[-1]
    repo_path = dest_folder / repo_name

    if repo_path.exists():
        print(f"  Repositório '{repo_name}' já existe. Pulando clone.")
        return repo_path

    print(f"  Clonando {repo_name} (shallow clone)...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
            check=True, capture_output=True, text=True, timeout=300
        )
        return repo_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Falha ao clonar {repo_name}: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout ao clonar {repo_name}.")

def run_ck_analysis_on_path(analysis_path: Path, repo_name: str) -> bool:
    """Função auxiliar para executar CK em um caminho específico e registrar logs."""
    logs_dir = config.DATA_DIR / "ck_logs"
    logs_dir.mkdir(exist_ok=True)
    log_file_name = f"{repo_name}-{analysis_path.name}-ck.log"
    log_file_path = logs_dir / log_file_name

    # O caminho para o ck.jar precisa ser absoluto, pois vamos mudar de diretório
    ck_jar_absolute_path = str(config.PATH_CK_JAR.resolve())
    
    # O diretório de saída também precisa ser absoluto
    output_dir_absolute_path = str(config.PATH_OUTPUT_CK.resolve())
    
    # O comando agora analisa '.', que significa 'este diretório atual'
    cmd = [
        str(config.JAVA_PATH), "-jar", ck_jar_absolute_path,
        ".", "true", "0", "true", output_dir_absolute_path
    ]
    
    try:
        with open(log_file_path, 'w') as log_file:
            # A MUDANÇA CRUCIAL ESTÁ AQUI: cwd=analysis_path
            subprocess.run(
                cmd, check=True, text=True, timeout=600,
                stdout=log_file, stderr=subprocess.STDOUT,
                cwd=analysis_path  # Executa o comando DE DENTRO do diretório de análise
            )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"    -> Falha ao analisar o diretório '{analysis_path.name}'. Veja o log: {log_file_path}")
        return False



def run_ck_analysis(repo_path: Path) -> bool:
    """
    Executa a análise do CK de forma inteligente:
    1. Procura por diretórios 'src/main/java'.
    2. Se encontrados, analisa cada um deles.
    3. Se não, analisa o repositório inteiro como fallback.
    """
    print(f"  Executando CK em {repo_path.name}...")
    
    # Limpa o diretório de saída do CK para a análise atual
    shutil.rmtree(config.PATH_OUTPUT_CK, ignore_errors=True)
    config.PATH_OUTPUT_CK.mkdir()

    # Procura por diretórios de código-fonte padrão (Maven/Gradle)
    source_dirs = list(repo_path.glob("**/src/main/java"))
    
    all_results_df = pd.DataFrame()
    analysis_performed = False

    if source_dirs:
        print(f"  Estrutura Maven/Gradle detectada. Encontrado(s) {len(source_dirs)} diretório(s) de código-fonte.")
        for src_dir in source_dirs:
            print(f"    Analisando módulo: .../{'/'.join(src_dir.parts[-4:])}")
            if run_ck_analysis_on_path(src_dir, repo_path.name):
                analysis_performed = True
                # Consolida os resultados de cada módulo
                class_csv_path = config.PATH_OUTPUT_CK / "class.csv"
                if class_csv_path.exists():
                    try:
                        module_df = pd.read_csv(class_csv_path)
                        all_results_df = pd.concat([all_results_df, module_df], ignore_index=True)
                        class_csv_path.unlink() # Remove para a próxima iteração
                    except pd.errors.EmptyDataError:
                        print(f"    -> 'class.csv' gerado para o módulo, mas está vazio.")
            
    else:
        print("  Estrutura não-padrão detectada. Analisando o repositório inteiro...")
        if run_ck_analysis_on_path(repo_path, repo_path.name):
            analysis_performed = True
            class_csv_path = config.PATH_OUTPUT_CK / "class.csv"
            if class_csv_path.exists():
                try:
                    all_results_df = pd.read_csv(class_csv_path)
                except pd.errors.EmptyDataError:
                    print(f"    -> 'class.csv' gerado para o repositório, mas está vazio.")


    # Se qualquer análise produziu resultados, salva o 'class.csv' consolidado
    if not all_results_df.empty:
        final_csv_path = config.PATH_OUTPUT_CK / "class.csv"
        all_results_df.to_csv(final_csv_path, index=False)
        print(f"  Análise CK concluída. {len(all_results_df)} classes analisadas.")
        return True
    
    if analysis_performed:
        print("  AVISO: Análise CK executada, mas nenhum resultado de métrica foi gerado.")
    
    return False


def process_ck_results(repo_name: str) -> dict:
    """Processa o arquivo 'class.csv' gerado pelo CK e retorna as métricas agregadas."""
    class_csv_path = config.PATH_OUTPUT_CK / "class.csv"
    try:
        df = pd.read_csv(class_csv_path)
        if df.empty:
            return {}
        
        df = df[["cbo", "dit", "lcom", "loc"]]

        metrics = {
            "repo_name": repo_name,
            "ck_cbo": int(df["cbo"].sum()),
            "ck_dit": round(df["dit"].mean(), 2),
            "ck_lcom": round(df["lcom"].mean(), 2),
            "ck_loc": int(df["loc"].sum()),
            "java_files_count": len(df)
        }
        return metrics
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"  ERRO ao processar resultados do CK para {repo_name}: {e}")
        return {}


def main():
    """Função principal para analisar os repositórios."""
    print("\n--- INICIANDO SCRIPT 2: ANÁLISE COM CK (VERSÃO INTELIGENTE) ---")
    
    input_file = config.DATA_DIR / "repositories.csv"
    if not input_file.exists():
        print(f"ERRO: Arquivo de entrada '{input_file}' não encontrado.")
        print("Por favor, execute o script '1_collect_data.py' primeiro.")
        return

    repos_to_analyze = pd.read_csv(input_file).head(20)
    all_metrics = []
    
    total_repos = len(repos_to_analyze)
    for index, repo in repos_to_analyze.iterrows():
        repo_name = repo["repo_name"]
        repo_url = repo["url"]
        print(f"\n[ Processando {index + 1}/{total_repos} ]: {repo['full_name']} ")
        
        repo_path = None
        try:
            repo_path = clone_repository(repo_url, config.PATH_REPOSITORIES)
            
            # Checagem inicial por arquivos .java para evitar rodar CK desnecessariamente
            if not any(repo_path.rglob("*.java")):
                print("  AVISO: Nenhum arquivo .java encontrado neste repositório. Pulando análise.")
                continue

            if run_ck_analysis(repo_path):
                ck_metrics = process_ck_results(repo_name)
                if ck_metrics:
                    all_metrics.append(ck_metrics)
                    print(f"  Métricas de {repo_name} processadas com sucesso.")
            else:
                print(f"  Análise CK falhou ou não gerou resultados para {repo_name}.")

        except Exception as e:
            print(f"  ERRO GERAL ao processar o repositório {repo_name}: {e}")
        finally:
            if repo_path:
                safe_remove_repository(repo_path)
    
    if not all_metrics:
        print("\nNenhuma métrica do CK foi gerada.")
    else:
        df_metrics = pd.DataFrame(all_metrics)
        output_path = config.DATA_DIR / "ck_metrics.csv"
        df_metrics.to_csv(output_path, index=False)
        print(f"\n{len(df_metrics)} repositórios analisados com sucesso.")
        print(f"Métricas do CK salvas em: {output_path}")

    print("--- SCRIPT 2: ANÁLISE COM CK FINALIZADO ---")

if __name__ == "__main__":
    main()