from playwright.sync_api import sync_playwright
import pandas as pd
from tqdm import tqdm
import os

# -------------------------------
# CONFIGURATION
# -------------------------------
TARGET_COMPANIES = 500
OUTPUT_FILE = "output/yc_startups.csv"
BASE_URL = "https://www.ycombinator.com"

# -------------------------------
# BLOCK HEAVY RESOURCES (SAFE)
# -------------------------------
def block_resources(page):
    page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ["image", "font", "media"]
        else route.continue_()
    )

# -------------------------------
# STEP 1: COLLECT COMPANY LINKS
# -------------------------------
def get_company_links(page, target_count):
    print("Collecting company links...")

    page.goto(f"{BASE_URL}/companies", wait_until="networkidle")

    company_links = set()

    while len(company_links) < target_count:
        cards = page.query_selector_all("a[href^='/companies/']")

        for card in cards:
            href = card.get_attribute("href")
            if href:
                company_links.add(BASE_URL + href)

        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        page.wait_for_timeout(400)

        print(f"Collected: {len(company_links)} companies", end="\r")

    print(f"\nTotal company links collected: {len(company_links)}")
    return list(company_links)[:target_count]

# -------------------------------
# STEP 2: SCRAPE A COMPANY PAGE
# -------------------------------
def scrape_company(page, url, retries=1):
    for attempt in range(retries):
        try:
            page.goto(url, wait_until="commit")

            company = {}

            # Company Name
            company["Company Name"] = page.locator("h1").inner_text().strip()

            # Batch
            batch_el = page.locator("span:has-text('S'), span:has-text('W')")
            company["Batch"] = batch_el.first.inner_text().strip() if batch_el.count() else ""

            # Description
            desc_el = page.locator("main p")
            company["Description"] = desc_el.first.inner_text().strip() if desc_el.count() else ""

            # Founders
            founder_names = []
            founder_linkedins = []

            founders_section = page.locator("section:has-text('Founders')")
            if founders_section.count():
                founders = founders_section.locator("a")

                for i in range(founders.count()):
                    founder = founders.nth(i)

                    name_el = founder.locator("h4")
                    if name_el.count():
                        founder_names.append(name_el.inner_text().strip())

                    link = founder.get_attribute("href")
                    if link and "linkedin.com" in link:
                        founder_linkedins.append(link)

            company["Founder Names"] = ", ".join(founder_names)
            company["Founder LinkedIn URLs"] = ", ".join(founder_linkedins)

            return company

        except Exception:
            if attempt == retries - 1:
                print(f"Skipped: {url}")
                return None

# -------------------------------
# MAIN FUNCTION
# -------------------------------
def main():
    os.makedirs("output", exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        block_resources(page)
        page.set_default_timeout(15000)

        company_links = get_company_links(page, TARGET_COMPANIES)

        for link in tqdm(company_links, desc="Scraping companies"):
            data = scrape_company(page, link)
            if data:
                results.append(data)

            if len(results) % 50 == 0:
                pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)

        browser.close()

    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)

    print("\n✅ Scraping completed successfully.")
    print(f"Total companies scraped: {len(results)}")
    print(f"Data saved to: {OUTPUT_FILE}")

# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    main()
