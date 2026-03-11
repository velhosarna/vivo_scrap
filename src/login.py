import logging

from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


def login(page: Page, username: str, password: str) -> None:
    from .config import VIVO_URL

    logger.info(f"Logging in as user: {username}")
    page.goto(VIVO_URL, timeout=0)
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_text("Otimize o uso de Voz")).to_be_visible()

    page.fill('input[formcontrolname="usuario"]', username)
    page.fill('input[formcontrolname="senha"]', password)

    expect(page.get_by_role("button", name=" Entrar ")).to_be_visible()
    page.get_by_role("button", name=" Entrar ").click(delay=500)

    page.wait_for_timeout(1000)
    dismiss_modal_if_present(page)

    expect(page.get_by_text("Consumo de Dados", exact=True)).to_be_visible(timeout=0)
    logger.info("Login successful")


def handle_login_dialog(page: Page) -> None:
    try:
        page.wait_for_selector("ngb-modal-backdrop.modal-backdrop.fade.in", timeout=3000)
        dialog = page.get_by_text("para efetivar o login")
        if dialog.count() > 0:
            page.get_by_role("button", name="OK").click(delay=500)
            logger.info("Dismissed login dialog")
    except Exception:
        pass


def dismiss_modal_if_present(page: Page) -> None:
    try:
        modal = page.locator("ngb-modal-window")
        if modal.count() > 0 and modal.first.is_visible():
            button = page.locator("ngb-modal-window .modal-body button")
            if button.count() > 0 and button.first.is_visible():
                button.first.click()
                logger.info("Dismissed modal dialog")
                page.wait_for_timeout(500)
    except Exception:
        pass


def navigate_to_consumo_dados(page: Page) -> None:
    expect(page.get_by_text("Consumo de Dados", exact=True)).to_be_visible()
    page.click("#consumeData a.anchor-context")
    page.wait_for_timeout(1000)
    dismiss_modal_if_present(page)
