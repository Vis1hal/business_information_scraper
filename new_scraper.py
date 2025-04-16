import time
import csv
import os
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def search_google_places(driver, query):
    search_url = f"https://www.google.com/search?q={query}&tbm=lcl"
    driver.get(search_url)
    time.sleep(2)

def extract_text(driver, xpath, default="Not Found"):
    try:
        return WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        ).text
    except Exception as e:
        log_error(f"Error in extract_text: {e}")
        alert_error("Error in extracting text.")
        return default

def extract_business_name(driver):
    return extract_text(driver, "//h2[contains(@class, 'qrShPb')]")

def extract_category(driver):
    return extract_text(driver, "//span[contains(@class, 'YhemCb')]")

def extract_website(driver):
    try:
        website_xpath = "//a[contains(@class, 'n1obkb mI8Pwc')]"
        website_element = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, website_xpath))
        )
        return website_element.get_attribute("href")
    except Exception as e:
        log_error(f"Error in extract_website: {e}")
        alert_error("Error in extracting website.")
        return "Website not extracted"

def extract_reviews(driver):
    return extract_text(driver, "//div[contains(@class, 'CJQ04')]")

def extract_address(driver):
    return extract_text(driver, "//span[contains(@class, 'LrzXr')]")

def extract_phone(driver):
    try:
        phone_element = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@aria-label, 'Call phone number')]"))
        )
        return phone_element.text
    except Exception as e:
        log_error(f"Error in extract_phone: {e}")
        alert_error("Error in extracting phone number.")
        return "Phone number not found"

def extract_city_pincode(address):
    city, pincode = "Not Found", "Not Found"
    if address:
        parts = address.split(",")
        if len(parts) > 1:
            city = parts[-2].strip()
        match = re.search(r'\b\d{5,6}\b', address)
        if match:
            pincode = match.group()
    return city, pincode

def extract_business_details(driver):
    business_name = extract_business_name(driver)
    category = extract_category(driver)
    website = extract_website(driver)
    reviews = extract_reviews(driver)
    address = extract_address(driver)
    phone = extract_phone(driver)
    city, pincode = extract_city_pincode(address)
    return [business_name, category, website, reviews, address, phone, city, pincode]

def scroll_google_results(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("No more results loading.")
            break
        last_height = new_height

def scrape_google_results(driver, query):
    search_google_places(driver, query)
    time.sleep(1)
    data = []
    original_url = driver.current_url

    while True:
        scroll_google_results(driver)
        results = driver.find_elements(By.XPATH, "//div[contains(@class, 'cXedhc')]")
        total_results = len(results)

        if total_results == 0:
            print("No business listings found on this page.")
            break

        for i in range(total_results):
            try:
                results = driver.find_elements(By.XPATH, "//div[contains(@class, 'cXedhc')]")
                if i >= len(results):
                    break

                if "YwfREd" in results[i].get_attribute("class") or "visit site" in results[i].text.lower():
                    continue

                WebDriverWait(driver, 1).until(EC.element_to_be_clickable(results[i])).click()
                time.sleep(1)
                if "google.com" not in driver.current_url:
                    driver.get(original_url)
                    time.sleep(1)
                    continue
                details = extract_business_details(driver)
                if details[0] != "Not Found":
                    data.append([query] + details)
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(1)
            except Exception as e:
                log_error(f"Error in scraping results: {e}")
                alert_error("Error in scraping results.")
                continue

        try:
            next_button = driver.find_element(By.ID, "pnnext")
            next_button.click()
            time.sleep(1)
        except:
            break

    return data

def save_to_csv(filename, data, headers=None):
    file_exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        writer.writerows(data)

def log_error(error_message):
    with open("error_log.txt", "a") as error_log:
        error_log.write(f"{time.ctime()}: {error_message}\n")

def alert_error(message):
    print(f"ALERT: {message}")

# ✅ Updated main() with manual input
def main():
    output_file = "google_business_results.csv"
    headers = ["Search Query", "Business Name", "Category", "Website", "Number of Reviews", "Full Address", "Phone Number", "City", "Pincode"]

    print("Enter your search queries (type 'done' when finished):")
    queries = []
    while True:
        query = input("Search query: ").strip()
        if query.lower() == "done":
            break
        if query:
            queries.append(query)

    if not queries:
        print("No queries entered. Exiting.")
        return

    driver = setup_driver()

    for query in queries:
        print(f"Starting Scraping for: {query}")
        results = scrape_google_results(driver, query)
        if results:
            save_to_csv(output_file, results, headers)

    driver.quit()
    print(f"\nScraping Complete! Data saved to {output_file}")

if __name__ == "__main__":
    main()
