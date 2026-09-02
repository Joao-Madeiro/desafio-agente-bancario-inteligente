import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

SOURCE_DATA_DIR = BASE_DIR / "data"
if os.getenv("VERCEL"):
    # O bundle do Vercel é somente leitura. Cada instância recebe uma cópia
    # temporária dos CSVs para que os fluxos de demonstração possam escrever.
    DATA_DIR = Path("/tmp/madeiro-bank-data")
else:
    DATA_DIR = SOURCE_DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

if os.getenv("VERCEL"):
    for filename in ("clientes.csv", "score_limite.csv", "solicitacoes_aumento_limite.csv"):
        source = SOURCE_DATA_DIR / filename
        target = DATA_DIR / filename
        if source.exists() and not target.exists():
            shutil.copy2(source, target)

CLIENTS_CSV_PATH = DATA_DIR / "clientes.csv"
SCORE_LIMIT_CSV_PATH = DATA_DIR / "score_limite.csv"
REQUESTS_CSV_PATH = DATA_DIR / "solicitacoes_aumento_limite.csv"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SERVER_HOST = os.getenv("HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("PORT", "8000"))
