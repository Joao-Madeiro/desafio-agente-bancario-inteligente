import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd

from src.config import CLIENTS_CSV_PATH, REQUESTS_CSV_PATH, SCORE_LIMIT_CSV_PATH
from src.models.schemas import Cliente, ScoreLimiteRegra, SolicitacaoAumento

_lock = threading.Lock()

def clean_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", str(cpf))


def normalize_cpf(cpf: str) -> str:
    """Normaliza CPFs numéricos, preservando zeros à esquerda."""
    cleaned = clean_cpf(cpf)
    return cleaned.zfill(11) if len(cleaned) <= 11 else cleaned

def parse_date(date_str: str) -> Optional[str]:
    cleaned = str(date_str).strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d%m%Y", "%Y%m%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

class CSVManager:
    def __init__(
        self,
        clients_path: Path = CLIENTS_CSV_PATH,
        requests_path: Path = REQUESTS_CSV_PATH,
        score_path: Path = SCORE_LIMIT_CSV_PATH,
    ):
        self.clients_path = Path(clients_path)
        self.requests_path = Path(requests_path)
        self.score_path = Path(score_path)
        self._ensure_files()

    def _ensure_files(self) -> None:
        with _lock:
            if not self.clients_path.exists():
                df = pd.DataFrame(
                    columns=[
                        "cpf",
                        "nome",
                        "data_nascimento",
                        "limite_credito",
                        "score_credito",
                        "email",
                        "telefone",
                    ]
                )
                df.to_csv(self.clients_path, index=False)

            if not self.requests_path.exists():
                df = pd.DataFrame(
                    columns=[
                        "cpf_cliente",
                        "data_hora_solicitacao",
                        "limite_atual",
                        "novo_limite_solicitado",
                        "status_pedido",
                    ]
                )
                df.to_csv(self.requests_path, index=False)

            if not self.score_path.exists():
                df = pd.DataFrame(
                    [
                        {
                            "score_min": 0,
                            "score_max": 299,
                            "limite_maximo_permitido": 1000.0,
                            "descricao_faixa": "Faixa Inicial (Risco Alto)",
                        },
                        {
                            "score_min": 300,
                            "score_max": 599,
                            "limite_maximo_permitido": 5000.0,
                            "descricao_faixa": "Faixa Intermediária (Risco Moderado)",
                        },
                        {
                            "score_min": 600,
                            "score_max": 799,
                            "limite_maximo_permitido": 15000.0,
                            "descricao_faixa": "Faixa Positiva (Baixo Risco)",
                        },
                        {
                            "score_min": 800,
                            "score_max": 1000,
                            "limite_maximo_permitido": 50000.0,
                            "descricao_faixa": "Faixa Premium (Risco Mínimo)",
                        },
                    ]
                )
                df.to_csv(self.score_path, index=False)

    def get_clients_df(self) -> pd.DataFrame:
        with _lock:
            return pd.read_csv(self.clients_path, dtype={"cpf": str})

    def get_requests_df(self) -> pd.DataFrame:
        with _lock:
            return pd.read_csv(self.requests_path, dtype={"cpf_cliente": str})

    def get_score_rules_df(self) -> pd.DataFrame:
        with _lock:
            return pd.read_csv(self.score_path)

    def get_all_clients(self) -> List[Cliente]:
        df = self.get_clients_df()
        clients = []
        for _, row in df.iterrows():
            clients.append(
                Cliente(
                    cpf=str(row["cpf"]).zfill(11),
                    nome=str(row["nome"]),
                    data_nascimento=str(row["data_nascimento"]),
                    limite_credito=float(row["limite_credito"]),
                    score_credito=int(row["score_credito"]),
                    email=str(row.get("email", "")) if pd.notna(row.get("email")) else None,
                    telefone=str(row.get("telefone", "")) if pd.notna(row.get("telefone")) else None,
                )
            )
        return clients

    def get_all_requests(self) -> List[SolicitacaoAumento]:
        df = self.get_requests_df()
        requests = []
        for _, row in df.iterrows():
            requests.append(
                SolicitacaoAumento(
                    cpf_cliente=str(row["cpf_cliente"]).zfill(11),
                    data_hora_solicitacao=str(row["data_hora_solicitacao"]),
                    limite_atual=float(row["limite_atual"]),
                    novo_limite_solicitado=float(row["novo_limite_solicitado"]),
                    status_pedido=str(row["status_pedido"]),
                )
            )
        return requests

    def get_all_score_rules(self) -> List[ScoreLimiteRegra]:
        df = self.get_score_rules_df()
        rules = []
        for _, row in df.iterrows():
            rules.append(
                ScoreLimiteRegra(
                    score_min=int(row["score_min"]),
                    score_max=int(row["score_max"]),
                    limite_maximo_permitido=float(row["limite_maximo_permitido"]),
                    descricao_faixa=str(row["descricao_faixa"]),
                )
            )
        return rules

    def find_client_by_cpf(self, cpf: str) -> Optional[Cliente]:
        raw_cpf = normalize_cpf(cpf)
        df = self.get_clients_df()
        df["cpf_clean"] = df["cpf"].astype(str).apply(normalize_cpf)
        matched = df[df["cpf_clean"] == raw_cpf]
        if matched.empty:
            return None
        row = matched.iloc[0]
        return Cliente(
            cpf=str(row["cpf"]).zfill(11),
            nome=str(row["nome"]),
            data_nascimento=str(row["data_nascimento"]),
            limite_credito=float(row["limite_credito"]),
            score_credito=int(row["score_credito"]),
            email=str(row.get("email", "")) if pd.notna(row.get("email")) else None,
            telefone=str(row.get("telefone", "")) if pd.notna(row.get("telefone")) else None,
        )

    def validate_client(self, cpf: str, data_nascimento: str) -> Tuple[bool, Optional[Cliente], Optional[str]]:
        raw_cpf = clean_cpf(cpf)
        if not raw_cpf or len(raw_cpf) != 11:
            return False, None, "CPF com formato inválido. Por favor informe um CPF válido com 11 dígitos."

        parsed_user_dob = parse_date(data_nascimento)
        if not parsed_user_dob:
            return False, None, "Data de nascimento inválida. Por favor informe no formato DD/MM/AAAA."

        client = self.find_client_by_cpf(raw_cpf)
        if not client:
            return False, None, "Cliente não localizado com os dados fornecidos."

        client_dob = parse_date(client.data_nascimento)
        if client_dob != parsed_user_dob:
            return False, None, "Data de nascimento não confere com o cadastro."

        return True, client, None

    def update_client_score(self, cpf: str, new_score: int) -> bool:
        raw_cpf = clean_cpf(cpf)
        with _lock:
            df = pd.read_csv(self.clients_path, dtype={"cpf": str})
            df["cpf_clean"] = df["cpf"].astype(str).apply(clean_cpf)
            idx = df[df["cpf_clean"] == raw_cpf].index
            if idx.empty:
                return False
            df.loc[idx, "score_credito"] = int(new_score)
            df = df.drop(columns=["cpf_clean"])
            df.to_csv(self.clients_path, index=False)
            return True

    def update_client_limit(self, cpf: str, new_limit: float) -> bool:
        raw_cpf = clean_cpf(cpf)
        with _lock:
            df = pd.read_csv(self.clients_path, dtype={"cpf": str})
            df["cpf_clean"] = df["cpf"].astype(str).apply(clean_cpf)
            idx = df[df["cpf_clean"] == raw_cpf].index
            if idx.empty:
                return False
            df.loc[idx, "limite_credito"] = float(new_limit)
            df = df.drop(columns=["cpf_clean"])
            df.to_csv(self.clients_path, index=False)
            return True

    def get_score_rule_for_score(self, score: int) -> Optional[ScoreLimiteRegra]:
        rules = self.get_all_score_rules()
        for rule in rules:
            if rule.score_min <= score <= rule.score_max:
                return rule
        return None

    def record_limit_request(
        self,
        cpf: str,
        limite_atual: float,
        novo_limite_solicitado: float,
        status_pedido: str,
    ) -> SolicitacaoAumento:
        raw_cpf = clean_cpf(cpf)
        record = SolicitacaoAumento(
            cpf_cliente=raw_cpf,
            data_hora_solicitacao=datetime.now(timezone.utc).isoformat(),
            limite_atual=float(limite_atual),
            novo_limite_solicitado=float(novo_limite_solicitado),
            status_pedido=status_pedido,  # type: ignore
        )

        with _lock:
            df = pd.read_csv(self.requests_path, dtype={"cpf_cliente": str})
            new_df = pd.DataFrame([{
                "cpf_cliente": str(record.cpf_cliente),
                "data_hora_solicitacao": str(record.data_hora_solicitacao),
                "limite_atual": float(record.limite_atual),
                "novo_limite_solicitado": float(record.novo_limite_solicitado),
                "status_pedido": str(record.status_pedido),
            }])
            if df.empty:
                df = new_df
            else:
                df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(self.requests_path, index=False)

        return record

    def update_request_status(self, cpf: str, data_hora_solicitacao: str, novo_status: str) -> bool:
        raw_cpf = clean_cpf(cpf)
        with _lock:
            df = pd.read_csv(self.requests_path, dtype={"cpf_cliente": str})
            mask = (
                (df["cpf_cliente"].astype(str).apply(clean_cpf) == raw_cpf)
                & (df["data_hora_solicitacao"].astype(str) == str(data_hora_solicitacao))
            )
            idx = df[mask].index
            if idx.empty:
                return False
            df.loc[idx, "status_pedido"] = str(novo_status)
            df.to_csv(self.requests_path, index=False)
            return True

csv_manager = CSVManager()
