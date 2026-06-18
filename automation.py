from playwright.sync_api import sync_playwright


def open_selected_url(website_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(website_url)

        print("Opened URL successfully.")
        print("Page title:", page.title())

        input("Press Enter to close browser...")

        browser.close()


if __name__ == "__main__":
    open_selected_url("https://www.google.com")