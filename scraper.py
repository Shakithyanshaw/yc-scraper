from playwright.sync_api import sync_playwright
import pandas as pd
from tqdm import tqdm
import time
import os

# -------------------------------
# CONFIG
# -------------------------------
TARGET_COMPANIES = 500
OUTPUT_FILE = "output/yc_startups.csv"


# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def safe_text(page, selector):
    """
    Safely extract text from a selector
    """
    try:
        element = page.query_selector(selector)
        return element.inner_text().strip() if element else ""
    except:
        return ""


# -------------------------------
# STEP 1: COLLECT COMPANY LINKS
# -------------------------------
def get_company_links(page, target_count):
    print("Collecting company links...")

    page.goto("https://www.ycombinator.com/companies", timeout=60000)

    company_links = set()

    while len(company_links) < target_count:
        cards = page.query_selector_all("a[href^='/companies/']")

        for card in cards:
            href = card.get_attribute("href")
            if href and href.startswith("/companies/"):
                full_url = "https://www.ycombinator.com" + href
                company_links.add(full_url)

        # Scroll to load more companies
        page.mouse.wheel(0, 6000)
        time.sleep(1)

        print(f"Collected: {len(company_links)} companies", end="\r")

    print(f"\nTotal company links collected: {len(company_links)}")
    return list(company_links)[:target_count]


# -------------------------------
# STEP 2: SCRAPE COMPANY DETAILS
# -------------------------------
def scrape_company(page, url):
    page.goto(url, timeout=60000)
    time.sleep(1)

    company_data = {}

    company_data["Company Name"] = safe_text(page, "h1")
    company_data["Batch"] = safe_text(page, "span[class*='tag']")
    company_data["Description"] = safe_text(page, "div[class*='description']")

    founders = page.query_selector_all("div[class*='founder']")

    founder_names = []
    founder_linkedins = []

    for founder in founders:
        try:
            name_el = founder.query_selector("div[class*='name']")
            linkedin_el = founder.query_selector("a[href*='linkedin.com']")

            if name_el:
                founder_names.append(name_el.inner_text().strip())
            if linkedin_el:
                founder_linkedins.append(linkedin_el.get_attribute("href"))
        except:
            continue

    company_data["Founder Names"] = ", ".join(founder_names)
    company_data["Founder LinkedIn URLs"] = ", ".join(founder_linkedins)

    return company_data


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
            try:
                data = scrape_company(page, link)
                results.append(data)
            except Exception as e:
                print(f"Failed to scrape {link}: {e}")

        browser.close()

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nScraping completed. Data saved to {OUTPUT_FILE}")


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    main()
