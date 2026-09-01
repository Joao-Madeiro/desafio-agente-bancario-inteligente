import sys
import uvicorn
from src.config import SERVER_HOST, SERVER_PORT

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 60)
    print("BANCO AGIL - SISTEMA DE ATENDIMENTO BANCARIO INTELIGENTE")
    print("=" * 60)
    print(f"Servidor rodando em: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Interface Web: http://{SERVER_HOST}:{SERVER_PORT}/")
    print(f"Documentacao Swagger: http://{SERVER_HOST}:{SERVER_PORT}/docs")
    print("=" * 60)
    uvicorn.run("src.api.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
