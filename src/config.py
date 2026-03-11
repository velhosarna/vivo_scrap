import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

VIVO_URL = os.getenv("VIVO_URL", "https://vivogestao.vivoempresas.com.br/Portal/data/login")
VIVO_USERNAME = os.getenv("VIVO_USERNAME", "0443639044")
VIVO_PASSWORD = os.getenv("VIVO_PASSWORD", "M@der0#")

DATABASE_PATH = os.getenv("DATABASE_PATH", "vivo_gestao.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "scraping_vivo.log")

GRUPOS = [
    {"tabela": "Restaurante", "grupo": "#group-28037129-details"},
    {"tabela": "Alarme", "grupo": "#group-28046101-details"},
]

RESET_DAY = 23
RESET_HOUR = 23
