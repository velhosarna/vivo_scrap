import logging
from typing import TypedDict, Union

from bs4 import BeautifulSoup
from playwright.sync_api import Page, expect, sync_playwright

from .config import GRUPOS, LOG_FILE, VIVO_PASSWORD, VIVO_USERNAME
from .database import (
    inserir_dados_filiais,
    inserir_dados_geral,
    reset_db,
    should_reset,
)
from .login import (
    dismiss_modal_if_present,
    handle_login_dialog,
    login,
    navigate_to_consumo_dados,
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GeralDataDict(TypedDict):
    user: int
    nome_grupo: str
    cota_grupo: float
    nao_atribuida: float
    uso_dados: float
    porcentagem: float
    cota_atribuida: float


class FilialDataDict(TypedDict):
    filial: Union[str, None]
    codigo: Union[str, None]
    telefone: Union[str, None]
    uso_dados: Union[float, None]
    porcentagem: Union[float, None]
    tabela: str


def get_browser_config() -> dict:
    return {
        "headless": False,
        "slow_mo": 0,
    }


def scrape_geral(page: Page, user: str) -> None:
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Restaurante")).to_be_visible(timeout=5000)
    html_content = page.inner_html("div.table-responsive")

    scraping_geral(html_content, user)


def scraping_geral(html_content: str, user: str) -> None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("div", class_="table-body panel-group margin-lr-minus-15")
        if table is None:
            return
        rows = table.find_all("div", class_="row table_visible_row padding-lr-35")

        dados: list[GeralDataDict] = []

        for row in rows:
            nome_grupo_elem = row.find("div", style=" float: left; max-width: 80%;")
            if nome_grupo_elem is None:
                continue
            nome_grupo = nome_grupo_elem.get_text(strip=True)
            if nome_grupo in ["Restaurante", "Alarme"]:
                cols = row.find_all("div", class_="col-md-2")
                if len(cols) < 2:
                    continue

                cota_grupo_text = cols[0].get_text(strip=True).replace("GB", "")
                cota_grupo = float(cota_grupo_text)

                nao_atribuida_text = cols[1].get_text(strip=True).replace("GB", "")
                nao_atribuida = float(nao_atribuida_text)

                uso_dados_elem = row.find("div", class_="progress-bar-padding")
                if uso_dados_elem is None:
                    continue
                uso_dados_text = uso_dados_elem.get_text(strip=True).replace("GB", "")
                uso_dados = float(uso_dados_text)

                percent_elem = row.find("p", class_="percent")
                if percent_elem is None:
                    continue
                porcentagem_text = percent_elem.get_text(strip=True).replace("%", "")
                porcentagem = float(porcentagem_text)

                cota_attr_elem = row.find("p", class_="purpura")
                if cota_attr_elem is None:
                    continue
                cota_atribuida_text = cota_attr_elem.get_text(strip=True).replace("GB", "")
                cota_atribuida = float(cota_atribuida_text)

                dados.append(
                    {
                        "user": int(user),
                        "nome_grupo": nome_grupo,
                        "cota_grupo": cota_grupo,
                        "nao_atribuida": nao_atribuida,
                        "uso_dados": uso_dados,
                        "porcentagem": porcentagem,
                        "cota_atribuida": cota_atribuida,
                    }
                )

        for item in dados:
            inserir_dados_geral(
                int(item["user"]),
                str(item["nome_grupo"]),
                float(item["cota_grupo"]),
                float(item["nao_atribuida"]),
                float(item["cota_atribuida"]),
                float(item["uso_dados"]),
                float(item["porcentagem"]),
            )

    except Exception as e:
        logger.error(f"Erro durante o scraping geral: {e}")


def scrape_grupo(page: Page, tabela: str, grupo: str) -> None:
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(f"{tabela}")).to_be_visible()

    # Click + {tabela} link with retry
    expand_link = page.get_by_role("link", name=f"+ {tabela}")
    max_attempts = 3
    for _attempt in range(max_attempts):
        try:
            expand_link.click(delay=500)
            page.wait_for_timeout(2000)
            break
        except Exception as e:
            logger.error(f"Click + {tabela} failed: {e}")
            page.wait_for_timeout(2000)
            expand_link = page.get_by_role("link", name=f"+ {tabela}")

    ver_linhas = page.get_by_role("button", name="Ver Linhas")
    ver_mais = page.get_by_role("button", name="Ver mais linhas")
    ocultar_linhas = page.get_by_role("button", name="Ocultar Linhas")

    if ver_linhas.count() == 0:
        logger.error("Ver Linhas not found, retrying with navigation reset...")
        page.get_by_text("Consumo de Dados", exact=True).click()
        page.wait_for_timeout(1000)
        dismiss_modal_if_present(page)
        expand_link = page.get_by_role("link", name=f"+ {tabela}")
        expand_link.click()
        page.wait_for_timeout(2000)
        ver_linhas = page.get_by_role("button", name="Ver Linhas")
        ver_mais = page.get_by_role("button", name="Ver mais linhas")
        ocultar_linhas = page.get_by_role("button", name="Ocultar Linhas")
        logger.error(f"Ver Linhas count after retry: {ver_linhas.count()}")

    if ver_linhas.count() > 0:
        ver_linhas.first.click()
        page.wait_for_timeout(500)
        dismiss_modal_if_present(page)

    if ver_mais.count() > 0 and ver_mais.first.is_visible():
        while ver_mais.first.is_visible():
            ver_mais.first.click(delay=250)
            if ocultar_linhas.count() > 0:
                ocultar_linhas.first.click(delay=250)
            if ver_linhas.count() > 0:
                ver_linhas.first.click(delay=250)

    page.wait_for_load_state("networkidle")
    html_content = page.inner_html(f"{grupo}")

    scraping_restaurantes(html_content, tabela)


def scraping_restaurantes(html_content: str, tabela: str) -> None:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        table_div = soup.find("div", class_="table nopadding-left-right")
        if table_div is None:
            return
        rows = table_div.find_all("ng-template")

        dados: list[FilialDataDict] = []

        for row in rows:
            col_filial = row.find_all(
                "div", class_="col-md-3", style="word-wrap: break-word;width:16%;"
            )
            primeiro_dado: Union[str, None] = None
            if col_filial:
                p_elem = col_filial[0].find("p")
                if p_elem:
                    primeiro_dado = p_elem.text.strip()

            col_telefone = row.find_all("div", class_="col-md-2 nopadding-right")
            telefone: Union[str, None] = None
            if col_telefone:
                p_elem = col_telefone[0].find("p")
                if p_elem:
                    telefone = p_elem.text.strip()

            col_uso_dados = row.find("div", class_="progress-bar-padding")
            uso_de_dados: Union[float, None] = None
            if col_uso_dados:
                uso_de_dados_text = col_uso_dados.text.strip()
                uso_de_dados = float(uso_de_dados_text.replace("GB", ""))

            porcentagem: Union[float, None] = None
            percent_elem = row.find("p", class_="percent")
            if not percent_elem:
                percent_div = row.find("div", class_="center percentage")
                if percent_div:
                    percent_elem = percent_div.find("p")
            if percent_elem:
                porcentagem_text = percent_elem.get_text(strip=True).replace("%", "")
                if porcentagem_text:
                    porcentagem = float(porcentagem_text)

            if primeiro_dado:
                partes = primeiro_dado.rsplit(" - ", 1)
                filial = partes[0] + "-" + tabela[0]
                codigo = partes[1]
            else:
                filial = None
                codigo = None

            dados.append(
                {
                    "filial": filial,
                    "codigo": codigo,
                    "telefone": telefone,
                    "uso_dados": uso_de_dados,
                    "porcentagem": porcentagem,
                    "tabela": tabela,
                }
            )

        dados = verifica_nome(dados)  # type: ignore[assignment]

        for item in dados:
            if item["filial"] and item["uso_dados"] is not None and item["porcentagem"] is not None:
                inserir_dados_filiais(
                    str(item["filial"]),
                    str(item["codigo"]) if item["codigo"] else "",
                    str(item["telefone"]) if item["telefone"] else "",
                    str(item["tabela"]),
                    float(item["uso_dados"]),
                    float(item["porcentagem"]),
                )
    except Exception as e:
        logger.error(f"Erro durante o scraping: {e}")


def verifica_nome(dados: list[FilialDataDict]) -> list[FilialDataDict]:
    contador_filiais: dict[tuple[str, str], int] = {}
    for item in dados:
        if item["filial"]:
            filial = item["filial"]
            tabela = item["tabela"]
            chave = (filial, tabela)

            if chave in contador_filiais:
                contador_filiais[chave] += 1
                item["filial"] = f"{filial} {contador_filiais[chave]}"
            else:
                contador_filiais[chave] = 1

    return dados


def main() -> None:
    from .database import init_db

    init_db()

    if should_reset():
        logger.info("Resetting database...")
        reset_db()
    else:
        logger.info("Starting scraper...")

        with sync_playwright() as p:
            browser = p.chromium.launch(**get_browser_config())
            page = browser.new_page()

            try:
                login(page, VIVO_USERNAME, VIVO_PASSWORD)
                handle_login_dialog(page)
                navigate_to_consumo_dados(page)

                for item in GRUPOS:
                    scrape_grupo(page, item["tabela"], item["grupo"])

                scrape_geral(page, VIVO_USERNAME)

            except Exception as e:
                logger.error(f"Error during scraping: {e}")
            finally:
                browser.close()

    logger.info("Scraper finished")


if __name__ == "__main__":
    main()
