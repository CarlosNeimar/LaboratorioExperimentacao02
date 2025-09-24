# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_env_path(var_name: str) -> Path:
    path_str = os.getenv(var_name)
    if not path_str:
        raise ValueError(f"A variável de ambiente '{var_name}' não está definida.")
    return Path(path_str)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("O GITHUB_TOKEN não foi definido no arquivo .env.")
GITHUB_API_URL = "https://api.github.com/graphql"

PATH_REPOSITORIES = get_env_path("PATH_REPOSITORIES")
PATH_OUTPUT_CK = get_env_path("PATH_OUTPUT_CK")
DATA_DIR = Path(__file__).parent / "data"
CHARTS_DIR = Path(__file__).parent / "graficos"
PATH_CK_JAR = get_env_path("PATH_CK_JAR")
JAVA_PATH = get_env_path("JAVA_PATH")
PATH_REPOSITORIES.mkdir(parents=True, exist_ok=True)
PATH_OUTPUT_CK.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)