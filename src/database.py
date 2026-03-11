import sqlite3
from datetime import datetime

from .config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DATABASE_PATH)


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS geral (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                nome_grupo TEXT,
                cota_grupo REAL,
                nao_atribuida REAL,
                cota_atribuida REAL,
                uso_dados REAL,
                porcentagem REAL
            );

            CREATE TABLE IF NOT EXISTS filial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filial TEXT,
                codigo TEXT,
                telefone TEXT,
                grupo TEXT
            );

            CREATE TABLE IF NOT EXISTS historico_uso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filial_id INTEGER,
                uso_dados REAL,
                porcentagem REAL,
                data_coleta DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(filial_id) REFERENCES filial(id)
            );
        """)


def reset_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM historico_uso")
        cursor.execute("DELETE FROM filial")
        cursor.execute("DELETE FROM geral")
        conn.commit()


def should_reset() -> bool:
    now = datetime.now()
    return now.day == 23 and now.hour == 23


def inserir_dados_geral(
    user: int,
    nome_grupo: str,
    cota_grupo: float,
    nao_atribuida: float,
    cota_atribuida: float,
    uso_dados: float,
    porcentagem: float,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM geral WHERE user = ? AND nome_grupo = ?",
            (user, nome_grupo),
        )
        result = cursor.fetchone()

        if result:
            _update_geral(
                conn, result, cota_grupo, nao_atribuida, cota_atribuida, uso_dados, porcentagem
            )
        else:
            cursor.execute(
                """INSERT INTO geral
                   (user, nome_grupo, cota_grupo, nao_atribuida,
                    cota_atribuida, uso_dados, porcentagem)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    user,
                    nome_grupo,
                    cota_grupo,
                    nao_atribuida,
                    cota_atribuida,
                    uso_dados,
                    porcentagem,
                ),
            )
        conn.commit()


def _update_geral(
    conn: sqlite3.Connection,
    result: tuple,
    cota_grupo: float,
    nao_atribuida: float,
    cota_atribuida: float,
    uso_dados: float,
    porcentagem: float,
) -> None:
    cursor = conn.cursor()
    dados = {
        "cota_grupo": (result[3], cota_grupo),
        "nao_atribuida": (result[4], nao_atribuida),
        "cota_atribuida": (result[3], cota_atribuida),
        "uso_dados": (result[4], uso_dados),
        "porcentagem": (result[5], porcentagem),
    }

    dados_atualizados = {
        campo: valor_novo
        for campo, (valor_antigo, valor_novo) in dados.items()
        if valor_antigo != valor_novo
    }

    if dados_atualizados:
        set_clause = ", ".join([f"{dado} = ?" for dado in dados_atualizados])
        valores = list(dados_atualizados.values()) + [result[0]]
        query = f"UPDATE geral SET {set_clause} WHERE id = ?"
        cursor.execute(query, valores)


def inserir_dados_filiais(
    filial: str,
    codigo: str,
    telefone: str,
    grupo: str,
    uso_dados: float,
    porcentagem: float,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM filial WHERE filial = ? AND codigo = ? AND telefone = ? AND grupo = ?",
            (filial, codigo, telefone, grupo),
        )
        result = cursor.fetchone()

        if result:
            filial_id = result[0]
        else:
            cursor.execute(
                "INSERT INTO filial (filial, codigo, telefone, grupo) VALUES (?, ?, ?, ?)",
                (filial, codigo, telefone, grupo),
            )
            filial_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO historico_uso (filial_id, uso_dados, porcentagem) VALUES (?, ?, ?)",
            (filial_id, uso_dados, porcentagem),
        )
        conn.commit()
