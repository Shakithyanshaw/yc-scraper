from playwright.sync_api import sync_playwright
import pandas as pd
from tqdm import tqdm
import time
import os

# -------------------------------
# CONFIGURATION
# -------------------------------
TARGET_COMPANIES = 500
OUTPUT_FILE = "output/yc_startups.csv"
BASE_URL = "https://www.ycombinator.com"


# -------------------------------
# HELPER FUNCTION
# -------------------------------
def safe_text(page, selector):
    """
    Safely extract text from a selector.
    Returns empty string if not found.
    """
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else ""
    except:
        return ""


# -------------------------------
# STEP 1: COLLECT COMPANY LINKS
# -------------------------------
def get_company_links(page, target_count):
    print("Collecting company links...")

    page.goto(f"{BASE_URL}/companies", timeout=60000)

    company_links = set()

    while len(company_links) < target_count:
        cards = page.query_selector_all("a[href^='/companies/']")

        for card in cards:
            href = card.get_attribute("href")
            if href and href.startswith("/companies/"):
                full_url = BASE_URL + href
                company_links.add(full_url)

        # Scroll down to load more companies
        page.mouse.wheel(0, 6000)
        time.sleep(1)

        print(f"Collected: {len(company_links)} companies", end="\r")

    print(f"\nTotal company links collected: {len(company_links)}")
    return list(company_links)[:target_count]


# -------------------------------
# STEP 2: SCRAPE A COMPANY PAGE
# -------------------------------
def scrape_company(page, url, retries=2):
    for attempt in range(retries):
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            time.sleep(1)

            company = {}

            # 1. Company Name
            company["Company Name"] = page.locator("h1").first.inner_text().strip()

            # 2. Batch (usually next to company name)
            batch_el = page.locator("span:has-text('S') , span:has-text('W')").first
            company["Batch"] = batch_el.inner_text().strip() if batch_el.count() else ""

            # 3. Short Description (first paragraph under header)
            desc_el = page.locator("main p").first
            company["Description"] = desc_el.inner_text().strip() if desc_el.count() else ""

            # 4 & 5. Founders
            founder_names = []
            founder_linkedins = []

            founders_section = page.locator("section:has-text('Founders')")

            if founders_section.count():
                founders = founders_section.locator("a")

                for i in range(founders.count()):
                    founder = founders.nth(i)

                    name = founder.locator("h4").inner_text().strip()
                    founder_names.append(name)

                    linkedin = founder.get_attribute("href")
                    if linkedin and "linkedin.com" in linkedin:
                        founder_linkedins.append(linkedin)

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

        company_links = get_company_links(page, TARGET_COMPANIES)

        for link in tqdm(company_links, desc="Scraping companies"):
            data = scrape_company(page, link)
            if data:
                results.append(data)

            # Save progress every 50 companies (safety + bonus points)
            if len(results) % 50 == 0:
                pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)

        browser.close()

    # Final save
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nScraping completed successfully.")
    print(f"Total companies scraped: {len(df)}")
    print(f"Data saved to: {OUTPUT_FILE}")


# -------------------------------
# SCRIPT ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    main()
