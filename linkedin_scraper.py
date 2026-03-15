
import math
import re
from urllib.parse import urlparse, parse_qs
import math
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote, unquote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ECN
from selenium.webdriver.common.keys import Keys
import re

MAX_RESULTS_PER_SEARCH = 100

JOB_TITLES = [
    "Data Engineer"
]

CITIES = ["106693272"]

LINKEDIN_PROFILES = {"1": {"username": "kyrieivanovski@gmail.com",
                        "password" : "Mihail123*"},
                        "2" :{"username": "stephanstephenson123@gmail.com",
                        "password" : "Cocacola123*"}}

GEO_ID_TO_CITY = {
    "106693272": 'Switzerland',
}

def extract_geo_suggestions_from_html(html: str) -> list[dict]:
    """
    Parse LinkedIn location autocomplete suggestions from page HTML.

    Returns a list like:
    [
        {"geo_id": "103035651", "name": "Berlin, Germany"},
        ...
    ]
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    container = soup.find("div", attrs={"data-testid": "typeahead-results-container"})
    if not container:
        return results

    seen = set()

    for a_tag in container.select('a[href*="geoId="]'):
        href = a_tag.get("href", "")
        p_tag = a_tag.find("p")

        if not href or not p_tag:
            continue

        geoid = parse_qs(urlparse(href).query).get("geoId", [None])[0]
        name = p_tag.get_text(strip=True)

        if not geoid or not name:
            continue

        key = (geoid, name)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "geo_id": geoid,
                "name": name,
            }
        )

    return results


def get_linkedin_location_geoids(driver, locations: list[str], wait_seconds: int = 10) -> dict[str, list[dict]]:
    wait = WebDriverWait(driver, wait_seconds)
    all_results: dict[str, list[dict]] = {}

    driver.get("https://www.linkedin.com/jobs/")

    for location in locations:
        location_input = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'input[placeholder="City, state, or zip code"]')
            )
        )

        location_input.clear()
        location_input.send_keys(Keys.COMMAND, "a") 
        time.sleep(0.2)
        location_input.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)
        location_input.send_keys(location)
        
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="typeahead-results-container"]')
            )
        )

        time.sleep(1)

        parsed = extract_geo_suggestions_from_html(driver.page_source)
        all_results[location] = parsed

    return all_results

def extract_geoId(url):
    query_params = parse_qs(urlparse(url).query) 
    return query_params.get('geoId', [''])[0]

def filter_urls(data):
    filtered_data = []
    for item in data:
        url = item['pagination_url']
        query_params = parse_qs(urlparse(url).query)
        start = int(query_params.get('start', [0])[0])
        if start <= MAX_RESULTS_PER_SEARCH:
            filtered_data.append(item)
    return filtered_data

def linkedin_sign_in(driver, email, password):
    try:
        dismiss_icon = driver.find_element(By.CSS_SELECTOR, ".contextual-sign-in-modal__modal-dismiss-icon svg")
        dismiss_icon.click()
    except:
        print("didnt get popup, contnue...")
    sign_in_link = driver.find_element(By.CLASS_NAME, "nav__button-secondary")
    sign_in_link.click()

    username = driver.find_element(By.ID, "username")
    username.send_keys(email)

    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(password)

    sign_in = driver.find_element(By.CSS_SELECTOR, "button.btn__primary--large.from__button--floating")
    sign_in.click()


def get_all_paginations(total_results, base_url):
    total_pages = math.ceil(total_results / 25)
    if total_pages > 40:
        total_pages = 40

    all_paginations = []
    for page_num in range(1, total_pages + 1):
        data_dict = {}
        skip_ads = (page_num - 1) * 25
        page_link = f"{base_url}&start={skip_ads}"
        data_dict["base_url"] = base_url
        data_dict["pagination_url"] = page_link
        data_dict["total_results"] = total_results
        all_paginations.append(data_dict)

    return all_paginations

import time

def get_total_results_and_generate_pagination_links(driver):
    pagination_links = []
    for title in JOB_TITLES:
        encoded_title = quote(title)
        for city in CITIES:
            try:
                base_url = f"https://www.linkedin.com/jobs/search/?currentJobId=4101716722&geoId={city}&keywords={encoded_title}&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE"
                driver.get(base_url)
                time.sleep(1)
                wait = WebDriverWait(driver, 10)
                element = wait.until(
                EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".jobs-search-results-list__title-heading.truncate.jobs-search-results-list__text")
                        )
                    )
                text = element.text

                cleaned_text = text.split("\n")[1].replace("results", "").strip().replace(",", "")
                total_results = int(re.findall(r"\d+", cleaned_text)[0])

                paginations = get_all_paginations(total_results, base_url)
                pagination_links.extend(paginations)
            except:
                print(f"Error while getting total results on page: {base_url}")

    return pagination_links

def suffixes_per_page(driver, original_url, expected_results):

    visable_ads = driver.find_elements(By.CLASS_NAME, "job-card-list__title--link")  
    total_visable_ads = len(visable_ads)

    total_scrolls_required = math.ceil(25 / total_visable_ads) + 1 if total_visable_ads > 0 else 1

    for _ in range(total_scrolls_required):
        if visable_ads:
            driver.execute_script("arguments[0].scrollIntoView(true);", visable_ads[-1])
            time.sleep(1)
            visable_ads = driver.find_elements(By.CLASS_NAME, "job-card-list__title--link")
        else:
            break

    # Extract the 'href' attribute from each link element
    link_suffixes = [ad.get_attribute("href") for ad in visable_ads if ad.get_attribute("href") is not None]
    if link_suffixes:
        list_of_dicts = [{"origin_url": original_url, "link": suffix} for suffix in link_suffixes]
        list_of_dicts = list_of_dicts[:expected_results]
    else:
        list_of_dicts = None
        print("Didnt get any links here!")
   
    return list_of_dicts

def start_chrome_with_login_page():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.get("https://www.linkedin.com/?trk=public_profile_nav-header-logo")
    return driver

def get_direct_links_from_pagination(driver, pagination_urls):
    all_direct_links = []
    for indx, page_data in enumerate(pagination_urls):
        try:
            print(f"{indx + 1}/{len(pagination_urls)}")
            if int(page_data["total_results"]) != 0:
                driver.get(page_data["pagination_url"])
                time.sleep(1)
                ads_per_page = suffixes_per_page(driver, page_data["pagination_url"], page_data["total_results"])
                all_direct_links.extend(ads_per_page)
                print("done")
            else:           
                print(f"total results 0 found for link: {page_data['pagination_url']}")
        except Exception as e:
            print(f"Check manually. Error: {e}")

    return all_direct_links

def get_job_ids_from_url(url: str) -> str:
    return int(url.replace("https://www.linkedin.com/jobs/view/", "").split("/")[0])


def get_raw_job_description(driver, direct_links):
    job_descriptions = []
    for idx, link_dict in enumerate(direct_links):
        data_dict = dict()
        print(f"{idx+1}/{len(direct_links)}")
        direct_url = link_dict["link"]
        pagination_url = link_dict["origin_url"]
        driver.get(direct_url)
        time.sleep(1)
        ad_id = get_job_ids_from_url(driver.current_url)
        job_description_element = driver.find_element(
            By.CSS_SELECTOR,
            f'div[componentkey="JobDetails_AboutTheJob_{ad_id}"]'
            )
        
        about_data = job_description_element.get_attribute("textContent")
        wait = WebDriverWait(driver, 10)
        parent_div = wait.until(
        EC.presence_of_element_located(
        (
            By.CSS_SELECTOR,
            'div[data-testid="lazy-column"][data-component-type="LazyColumn"]'
        )
        )
        )   
        spans = parent_div.find_element(By.XPATH, './div[1]').find_elements(By.TAG_NAME, "span")

        company_infos = " ".join([item.text for item in spans if item.text.strip()])

        company_name = parent_div.find_element(By.TAG_NAME, "a").text

        data_dict["ad_id"] = ad_id
        data_dict["about_data"] = about_data
        data_dict["company_infos"] = company_infos
        data_dict["company_name"] = company_name
        data_dict["ad_link"] = f"https://www.linkedin.com/jobs/view/{ad_id}/"
        job_descriptions.append(data_dict)

    return job_descriptions

def main():

    profile_to_use = "2"

    driver = start_chrome_with_login_page()   

    linkedin_sign_in(driver, LINKEDIN_PROFILES[profile_to_use]["username"],
                            LINKEDIN_PROFILES[profile_to_use]["password"])

    geo_ids = get_linkedin_location_geoids(driver, locations=["Berlin", "Geneva", "Germany"])
    pagination_data = get_total_results_and_generate_pagination_links(driver)

    pagination_data = pagination_data[:1]

    all_direct_links = get_direct_links_from_pagination(driver, pagination_urls=pagination_data)

    final_data = get_raw_job_description(driver, all_direct_links)

    print("STOP")

main()