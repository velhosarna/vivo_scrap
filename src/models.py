from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GeralData:
    user: int
    nome_grupo: str
    cota_grupo: float
    nao_atribuida: float
    cota_atribuida: float
    uso_dados: float
    porcentagem: float


@dataclass
class FilialData:
    filial: str
    codigo: str
    telefone: str
    grupo: str
    uso_dados: float
    porcentagem: float


@dataclass
class HistoricoUsoData:
    filial_id: int
    uso_dados: float
    porcentagem: float
    data_coleta: Optional[datetime] = None
