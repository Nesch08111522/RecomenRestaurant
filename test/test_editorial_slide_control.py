from pathlib import Path

from playwright.sync_api import sync_playwright


def test_pause_toggle_preserves_icon_and_updates_accessible_name():
    root = Path(__file__).resolve().parents[1]
    script = (root / "static/js/editorial-slides.js").read_text(encoding="utf-8")
    markup = """
    <div data-editorial-slides='["/static/images/auth/ceviche.webp"]'>
      <img src="/static/images/auth/ceviche.webp" alt="Plato">
      <button type="button" data-slide-pause aria-label="Pausar presentación">
        <i class="fas fa-pause" aria-hidden="true"></i>
        <span>Pausar</span>
      </button>
      <button type="button" data-slide-next aria-label="Mostrar otra imagen">Siguiente</button>
    </div>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.emulate_media(reduced_motion="no-preference")
        page.set_content(markup)
        page.add_script_tag(content=script)

        pause = page.locator("[data-slide-pause]")
        assert pause.locator("i").count() == 1
        assert pause.locator("span").inner_text() == "Pausar"
        assert pause.get_attribute("aria-label") == "Pausar presentación"
        assert pause.get_attribute("aria-pressed") == "false"

        pause.click()
        assert pause.locator("i").count() == 1
        assert pause.locator("span").inner_text() == "Reanudar"
        assert pause.get_attribute("aria-label") == "Reanudar presentación"
        assert pause.get_attribute("aria-pressed") == "true"
        browser.close()
