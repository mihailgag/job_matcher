import math
import re
import time
from typing import Optional
from urllib.parse import urlparse, parse_qs, quote

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from src.scrapers.base import BaseScraper
from src.scrapers.models import ScrapeRequest, RawJobAd


LINKEDIN_PROFILES = {
    "1": {
        "username": "kyrieivanovski@gmail.com",
        "password": "Mihail123*",
    },
    "2": {
        "username": "stephanstephenson123@gmail.com",
        "password": "Cocacola123*",
    },
}
MAX_RESULTS_PER_SEARCH = 25


class LinkedInScraper(BaseScraper):
    def __init__(
        self,
        profile_key: str = "1",
        db_manager: Optional[object] = None,
        headless: bool = False,
    ) -> None:
        super().__init__(db_manager=db_manager)
        self.profile_key = profile_key
        self.headless = headless

    def scrape(self, request: "ScrapeRequest") -> list["RawJobAd"]:
        driver = self._start_driver()
        try:
            self._open_homepage(driver)
            self._sign_in(driver)

            pagination_urls = self._get_total_results_and_generate_pagination_links(
                driver=driver,
                job_titles=request.job_titles,
                geo_ids=request.locations,
            )


            direct_links = self._get_direct_links_from_pagination(
                driver=driver,
                pagination_urls=pagination_urls,
            )

            direct_links = direct_links[:3]

            raw_ads = self._get_raw_job_descriptions(
                driver=driver,
                direct_links=direct_links,
            )

            return raw_ads
        finally:
            driver.quit()

    def _start_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _open_homepage(self, driver: webdriver.Chrome) -> None:
        driver.get("https://www.linkedin.com/?trk=public_profile_nav-header-logo")

    def _sign_in(self, driver: webdriver.Chrome) -> None:
        credentials = LINKEDIN_PROFILES[self.profile_key]

        try:
            dismiss_icon = driver.find_element(
                By.CSS_SELECTOR,
                ".contextual-sign-in-modal__modal-dismiss-icon svg",
            )
            dismiss_icon.click()
        except Exception:
            pass

        sign_in_link = driver.find_element(By.CLASS_NAME, "nav__button-secondary")
        sign_in_link.click()

        username = driver.find_element(By.ID, "username")
        username.send_keys(credentials["username"])

        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(credentials["password"])

        sign_in = driver.find_element(
            By.CSS_SELECTOR,
            "button.btn__primary--large.from__button--floating",
        )
        sign_in.click()

    def _get_total_results_and_generate_pagination_links(
        self,
        driver: webdriver.Chrome,
        job_titles: list[str],
        geo_ids: list[str],
    ) -> list[dict]:
        pagination_links: list[dict] = []

        for title in job_titles:
            encoded_title = quote(title)

            for geo_id in geo_ids:
                try:
                    base_url = (
                        "https://www.linkedin.com/jobs/search/"
                        f"?currentJobId=4101716722"
                        f"&geoId={geo_id}"
                        f"&keywords={encoded_title}"
                        "&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE"
                    )

                    driver.get(base_url)
                    time.sleep(1)

                    wait = WebDriverWait(driver, 10)
                    element = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                ".jobs-search-results-list__title-heading.truncate.jobs-search-results-list__text",
                            )
                        )
                    )

                    text = element.text
                    cleaned_text = (
                        text.split("\n")[1]
                        .replace("results", "")
                        .strip()
                        .replace(",", "")
                    )
                    total_results = int(re.findall(r"\d+", cleaned_text)[0])

                    paginations = self._get_all_paginations(
                        total_results=total_results,
                        base_url=base_url,
                    )
                    pagination_links.extend(paginations)

                except Exception as exc:
                    print(f"Error while getting total results for {geo_id}/{title}: {exc}")

        return pagination_links

    def _get_all_paginations(
        self,
        total_results: int,
        base_url: str,
    ) -> list[dict]:
        total_pages = math.ceil(total_results / 25)
        max_pages = math.ceil(MAX_RESULTS_PER_SEARCH / 25)
        total_pages = min(total_pages, max_pages, 40)

        all_paginations = []
        for page_num in range(1, total_pages + 1):
            skip_ads = (page_num - 1) * 25
            page_link = f"{base_url}&start={skip_ads}"
            all_paginations.append(
                {
                    "base_url": base_url,
                    "pagination_url": page_link,
                    "total_results": total_results,
                }
            )
        return all_paginations

    def _get_direct_links_from_pagination(
        self,
        driver: webdriver.Chrome,
        pagination_urls: list[dict],
    ) -> list[dict]:
        all_direct_links: list[dict] = []

        for index, page_data in enumerate(pagination_urls):
            try:
                print(f"{index + 1}/{len(pagination_urls)}")

                if int(page_data["total_results"]) == 0:
                    print(f"0 results for {page_data['pagination_url']}")
                    continue

                driver.get(page_data["pagination_url"])
                time.sleep(1)

                ads_per_page = self._extract_ad_links_from_page(
                    driver=driver,
                    original_url=page_data["pagination_url"],
                )

                if ads_per_page:
                    all_direct_links.extend(ads_per_page)

            except Exception as exc:
                print(f"Failed on pagination page {page_data['pagination_url']}: {exc}")

        return all_direct_links

    def _extract_ad_links_from_page(
        self,
        driver: webdriver.Chrome,
        original_url: str,
    ) -> list[dict]:
        visible_ads = driver.find_elements(By.CLASS_NAME, "job-card-list__title--link")
        total_visible_ads = len(visible_ads)

        total_scrolls_required = (
            math.ceil(25 / total_visible_ads) + 1 if total_visible_ads > 0 else 1
        )

        for _ in range(total_scrolls_required):
            if not visible_ads:
                break

            driver.execute_script("arguments[0].scrollIntoView(true);", visible_ads[-1])
            time.sleep(1)
            visible_ads = driver.find_elements(By.CLASS_NAME, "job-card-list__title--link")

        return [{
            "origin_url" : original_url,
            "link" : ad.get_attribute("href"),
            "title" : ad.find_element(By.TAG_NAME, 'span').text
            }
            for ad in visible_ads
            if ad.get_attribute("href") is not None
        ]


    def _get_raw_job_descriptions(
        self,
        driver: webdriver.Chrome,
        direct_links: list[dict],
    ) -> list["RawJobAd"]:
        job_descriptions: list[RawJobAd] = []

        for idx, link_dict in enumerate(direct_links):
            print(f"{idx + 1}/{len(direct_links)}")
            direct_url = link_dict["link"]
            title = link_dict["title"]

            try:
                driver.get(direct_url)
                time.sleep(1)

                ad_id = str(self._get_job_id_from_url(driver.current_url))

                job_description_element = driver.find_element(
                    By.CSS_SELECTOR,
                    f'div[componentkey="JobDetails_AboutTheJob_{ad_id}"]',
                )

                about_data = job_description_element.get_attribute("textContent")

                wait = WebDriverWait(driver, 10)
                parent_div = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            'div[data-testid="lazy-column"][data-component-type="LazyColumn"]',
                        )
                    )
                )

                spans = parent_div.find_element(
                    By.XPATH, './div[1]'
                ).find_elements(By.TAG_NAME, "span")

                company_infos = " ".join(
                    [item.text for item in spans if item.text.strip()]
                )

                company_name = parent_div.find_element(By.TAG_NAME, "a").text

                full_ad_description = " ".join([company_infos, about_data])

                job_descriptions.append(
                    RawJobAd(
                        source="linkedin",
                        ad_id=ad_id,
                        title=title,
                        company_name=company_name,
                        company_info=full_ad_description,
                        ad_link=f"https://www.linkedin.com/jobs/view/{ad_id}/",
                        metadata={
                            "origin_url": link_dict["origin_url"],
                        },
                    )
                )

            except Exception as exc:
                print(f"Failed to parse ad {direct_url}: {exc}")

        return job_descriptions

    def _get_job_id_from_url(self, url: str) -> int:
        return int(url.replace("https://www.linkedin.com/jobs/view/", "").split("/")[0])

    def extract_geo_suggestions_from_html(self, html: str) -> list[dict]:
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

            results.append({"geo_id": geoid, "name": name})

        return results

    def get_linkedin_location_geoids(
        self,
        driver: webdriver.Chrome,
        locations: list[str],
        wait_seconds: int = 10,
    ) -> dict[str, list[dict]]:
        wait = WebDriverWait(driver, wait_seconds)
        all_results: dict[str, list[dict]] = {}

        driver.get("https://www.linkedin.com/jobs/")

        for location in locations:
            location_input = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'input[placeholder="City, state, or zip code"]')
                )
            )

            location_input.click()
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
            parsed = self.extract_geo_suggestions_from_html(driver.page_source)
            all_results[location] = parsed

        return all_results