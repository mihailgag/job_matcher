import math
import re
import logging
import time
import random
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Any
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
from src.scrapers.models import ScrapeRequest, RawJobAd, LinkedInScraperConfig, ScrapeRefreshMode, WorkMode, WriteMode
from src.database.repositories.raw_job_ads_repository import RawJobAdsRepository
from src.database.repositories.location_mappings_repository import LocationMappingsRepository

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


class LinkedInScraperSelenium(BaseScraper):
    def __init__(
        self,
        config: LinkedInScraperConfig,
    raw_job_ads_repository: Optional[RawJobAdsRepository] = None,
    location_mappings_repository: Optional[LocationMappingsRepository] = None,
    ) -> None:
        super().__init__(
            raw_job_ads_repository=raw_job_ads_repository,
            location_mappings_repository=location_mappings_repository,
        )
        self.config = config
        self.seen_direct_links: set[str] = set()
        self.profile_key = self.config.profile_key
        self.headless = self.config.headless
        self.max_results_per_search = self.config.max_results_per_search

    @contextmanager
    def _driver_session(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            yield driver
        finally:
            logging.info("Closing driver!")
            driver.quit()

    def scrape(self, request: "ScrapeRequest") -> list["RawJobAd"]:
        # driver = self._start_driver()
        all_ads: list[RawJobAd] = []

        with self._driver_session() as driver:
            logging.info("Opening LinkedIn homepage")
            self._open_homepage(driver)

            logging.info("Signing in to LinkedIn with profile_key=%s", self.profile_key)
            self._sign_in(driver)

            logging.info("Resolving input locations: %s", request.locations)
            resolved_locations = self._resolve_locations(
                driver=driver,
                input_locations=request.locations,
            )

            grouped_locations = self._group_resolved_locations_by_input_location(
                resolved_locations
            )

            for input_location in request.locations:
                location_group = grouped_locations.get(input_location, [])
                if not location_group:
                    logging.warning(
                        "No resolved LinkedIn locations for input '%s'",
                        input_location,
                    )
                    continue

                for job_title in request.job_titles:
                    logging.info(
                        "Starting scrape batch for input_location='%s', job_title='%s'",
                        input_location,
                        job_title,
                    )

                    batch_ads: list[RawJobAd] = []

                    for resolved_location in location_group:
                        ads = self._scrape_single_search(
                            driver=driver,
                            request=request,
                            resolved_location=resolved_location,
                            job_title=job_title,
                        )
                        batch_ads.extend(ads)

                    if batch_ads and self.raw_job_ads_repository is not None:
                        saved = self.raw_job_ads_repository.save_raw_job_ads(
                            jobs=batch_ads,
                            mode=WriteMode.UPSERT,
                        )
                        logging.info(
                            "Saved %s ads for input_location='%s', job_title='%s'",
                            saved,
                            input_location,
                            job_title,
                        )
                    else:
                        logging.info(
                            "No ads found for input_location='%s', job_title='%s'",
                            input_location,
                            job_title,
                        )

                    all_ads.extend(batch_ads)

            logging.info("Finished LinkedIn scraping. Total ads collected: %s", len(all_ads))
            return all_ads

    def _scrape_single_search(
        self,
        driver: webdriver.Chrome,
        request: "ScrapeRequest",
        resolved_location: dict[str, Any],
        job_title: str,
    ) -> list["RawJobAd"]:
    
        logging.info(
            "Building pagination for job_title='%s', resolved_location='%s', geo_id='%s'",
            job_title,
            resolved_location["resolved_location"],
            resolved_location["geo_id"],
        )

        pagination_urls = self._get_pagination_links_for_search(
            driver=driver,
            job_title=job_title,
            resolved_location=resolved_location,
        )

        if not pagination_urls:
            logging.info(
                "No pagination URLs found for job_title='%s', resolved_location='%s'",
                job_title,
                resolved_location["resolved_location"],
            )
            return []

        logging.info(
            "Collecting direct links from %s pagination pages for job_title='%s', resolved_location='%s'",
            len(pagination_urls),
            job_title,
            resolved_location["resolved_location"],
        )
        direct_links = self._get_direct_links_from_pagination(
            driver=driver,
            pagination_urls=pagination_urls,
        )

        filtered_direct_links = self._filter_direct_links_for_scraping(
            direct_links=direct_links,
            execution_ts=request.execution_ts,
        )

        logging.info(
            "Parsing %s direct job links after refresh filtering for job_title='%s', resolved_location='%s'",
            len(filtered_direct_links),
            job_title,
            resolved_location["resolved_location"],
        )
        raw_ads = self._get_raw_job_descriptions(
            driver=driver,
            direct_links=filtered_direct_links, 
            execution_ts=request.execution_ts,
        )

        logging.info(
            "Parsed %s raw ads for job_title='%s', resolved_location='%s'",
            len(raw_ads),
            job_title,
            resolved_location["resolved_location"],
        )
        return raw_ads

    def _group_resolved_locations_by_input_location(
        self,
        resolved_locations: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for item in resolved_locations:
            grouped[item["input_location"]].append(item)

        return dict(grouped)

    def _start_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--renderer-process-limit=2")
      
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _open_homepage(self, driver: webdriver.Chrome) -> None:
        driver.get("https://www.linkedin.com/?trk=public_profile_nav-header-logo")

    def _sign_in(self, driver: webdriver.Chrome) -> None:
        credentials = LINKEDIN_PROFILES[self.profile_key]
        time.sleep(0.5)

        try:
            dismiss_icon = driver.find_element(
                By.CSS_SELECTOR,
                ".contextual-sign-in-modal__modal-dismiss-icon svg",
            )
            dismiss_icon.click()
        except Exception:
            logging.info("No LinkedIn dismiss modal found")

        sign_in_link = driver.find_element(By.CLASS_NAME, "nav__button-secondary")
        sign_in_link.click()

        time.sleep(2)

        username = driver.find_element(By.ID, "username")
        username.send_keys(credentials["username"])

        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(credentials["password"])

        sign_in = driver.find_element(
            By.CSS_SELECTOR,
            "button.btn__primary--large.from__button--floating",
        )
        sign_in.click()

    def _resolve_locations(
        self,
        driver: webdriver.Chrome,
        input_locations: list[str],
    ) -> list[dict[str, Any]]:
        resolved_locations: list[dict[str, Any]] = []

        for input_location in input_locations:
            cached_mappings: list[dict[str, Any]] = []

            if self.location_mappings_repository is not None:
                cached_mappings = self.location_mappings_repository.get_location_mappings(
                    source="linkedin",
                    input_location=input_location,
                )

            if cached_mappings:
                logging.info(
                    "Using %s cached LinkedIn mappings for '%s'",
                    len(cached_mappings),
                    input_location,
                )
                resolved_locations.extend(cached_mappings)
                continue

            logging.info(
                "No cached mappings for '%s'. Resolving location from LinkedIn.",
                input_location,
            )

            fresh_mappings = self.get_linkedin_location_geoids(
                driver=driver,
                location=input_location,
            )

            if self.location_mappings_repository is not None and fresh_mappings:
                self.location_mappings_repository.save_location_mappings(
                    source="linkedin",
                    input_location=input_location,
                    mappings=fresh_mappings,
                )
                logging.info(
                    "Saved %s fresh LinkedIn mappings for '%s'",
                    len(fresh_mappings),
                    input_location,
                )

            resolved_locations.extend(
                [
                    {
                        "source": "linkedin",
                        "input_location": input_location,
                        "resolved_location": item["resolved_location"],
                        "geo_id": item["geo_id"],
                        "country": item.get("country"),
                        "region": item.get("region"),
                    }
                    for item in fresh_mappings
                ]
            )

        return resolved_locations

    def _get_pagination_links_for_search(
        self,
        driver: webdriver.Chrome,
        job_title: str,
        resolved_location: dict[str, Any],
    ) -> list[dict[str, Any]]:
        geo_id = resolved_location["geo_id"]
        encoded_title = quote(job_title.lower())

        try:
            base_url = (
                "https://www.linkedin.com/jobs/search/"
                f"?currentJobId=4101716722"
                f"&geoId={geo_id}"
                f"&keywords={encoded_title}"
                "&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE&refresh=true&sortBy=DD"
            )

            logging.info(
                "Loading LinkedIn search results for job_title='%s', resolved_location='%s'",
                job_title,
                resolved_location["resolved_location"],
            )

            time.sleep(1)
            driver.get(base_url)
            time.sleep(2)

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

            logging.info(
                "Found %s total results for job_title='%s', resolved_location='%s'",
                total_results,
                job_title,
                resolved_location["resolved_location"],
            )

            paginations = self._get_all_paginations(
                total_results=total_results,
                base_url=base_url,
            )

            for page in paginations:
                page["input_location"] = resolved_location["input_location"]
                page["resolved_location"] = resolved_location["resolved_location"]
                page["geo_id"] = resolved_location["geo_id"]
                page["job_title"] = job_title

            return paginations

        except Exception:
            logging.exception(
                "Error while getting pagination links for input_location='%s', geo_id='%s', job_title='%s'",
                resolved_location["input_location"],
                geo_id,
                job_title,
            )
            return []

    def _get_all_paginations(
        self,
        total_results: int,
        base_url: str,
    ) -> list[dict]:
        total_pages = math.ceil(total_results / 25)
        max_pages = math.ceil(self.max_results_per_search / 25)
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

        total_pages = len(pagination_urls)
        last_reported_pct = -1

        logging.info("Starting pagination traversal for %s pages", total_pages)

        for index, page_data in enumerate(pagination_urls, start=1):
            try:
                if total_pages > 0:
                    current_pct = int((index / total_pages) * 100)
                    progress_bucket = (current_pct // 10) * 10

                    if progress_bucket != last_reported_pct and progress_bucket > 0:
                        logging.info(
                            "Pagination traversal %s%% finished (%s/%s)",
                            progress_bucket,
                            index,
                            total_pages,
                        )
                        last_reported_pct = progress_bucket

                if int(page_data["total_results"]) == 0:
                    logging.info("0 results for %s", page_data["pagination_url"])
                    continue

                driver.get(page_data["pagination_url"])
                time.sleep(1)

                ads_per_page = self._extract_ad_links_from_page(
                    driver=driver,
                    original_url=page_data["pagination_url"],
                    page_data=page_data,
                )

                if ads_per_page:
                    all_direct_links.extend(ads_per_page)

            except Exception:
                logging.exception(
                    "Failed on pagination page %s",
                    page_data["pagination_url"],
                )

        logging.info(
            "Finished pagination traversal. Collected %s direct links",
            len(all_direct_links),
        )
        return all_direct_links

    def _parse_direct_link(self, raw_link: str | None) -> str | None:
        if not raw_link:
            return None
        if "?" in raw_link:
            return raw_link.split("?")[0]
        return raw_link

    def _extract_job_id_from_direct_link(self, link: str | None) -> str | None:
        if not link:
            return None

        clean_link = self._parse_direct_link(link)
        if not clean_link:
            return None

        try:
            return str(
                clean_link.replace("https://www.linkedin.com/jobs/view/", "").split("/")[0]
            )
        except Exception:
            return None

    def _should_scrape_ad(
        self,
        existing_row: dict[str, Any] | None,
        execution_ts: datetime,
    ) -> bool:
        policy = self.config.refresh_policy

        if policy.mode == ScrapeRefreshMode.ALL:
            return True

        if existing_row is None:
            return True

        if policy.mode == ScrapeRefreshMode.NEW_ONLY:
            return False

        if policy.mode == ScrapeRefreshMode.STALE_OR_NEW:
            last_scraped_at = existing_row.get("last_scraped_at")
            if last_scraped_at is None:
                return True

            age_days = (execution_ts - last_scraped_at).days
            return age_days >= policy.stale_after_days

        raise ValueError(f"Unsupported refresh policy mode: {policy.mode}")

    def _filter_direct_links_for_scraping(
        self,
        direct_links: list[dict[str, Any]],
        execution_ts: datetime,
    ) -> list[dict[str, Any]]:
        if self.raw_job_ads_repository is None:
            logging.info(
                "No DB manager available. Skipping refresh filtering and scraping all %s links.",
                len(direct_links),
            )
            return direct_links

        ad_id_to_link: dict[str, dict[str, Any]] = {}

        for link_dict in direct_links:
            ad_id = self._extract_job_id_from_direct_link(link_dict.get("link"))
            if not ad_id:
                continue
            link_dict["ad_id"] = ad_id
            ad_id_to_link[ad_id] = link_dict

        total_unique_links = len(ad_id_to_link)

        known_ads = self.raw_job_ads_repository.get_known_ads_by_ids(
            source="linkedin",
            ad_ids=list(ad_id_to_link.keys()),
        )

        links_to_scrape: list[dict[str, Any]] = []
        skipped_known_ids: list[str] = []
        new_ids: list[str] = []
        stale_ids: list[str] = []

        for ad_id, link_dict in ad_id_to_link.items():
            existing_row = known_ads.get(ad_id)

            if existing_row is None:
                new_ids.append(ad_id)
                links_to_scrape.append(link_dict)
                continue

            if self._should_scrape_ad(existing_row, execution_ts):
                stale_ids.append(ad_id)
                links_to_scrape.append(link_dict)
            else:
                skipped_known_ids.append(ad_id)

        if skipped_known_ids:
            self.raw_job_ads_repository.touch_last_seen_at(
                source="linkedin",
                ad_ids=skipped_known_ids,
                seen_at=execution_ts,
            )

        logging.info(
            (
                "Direct link refresh filtering summary: total_input=%s, "
                "unique_links=%s, known_ads=%s, new_ads=%s, stale_ads=%s, "
                "skipped_known_ads=%s, continuing_to_scrape=%s, mode=%s"
            ),
            len(direct_links),
            total_unique_links,
            len(known_ads),
            len(new_ids),
            len(stale_ids),
            len(skipped_known_ids),
            len(links_to_scrape),
            self.config.refresh_policy.mode.value,
        )

        if new_ids:
            logging.info("New ads to scrape: %s", len(new_ids))

        if stale_ids:
            logging.info(
                "Previously known ads selected for refresh: %s",
                len(stale_ids),
            )

        if skipped_known_ids:
            logging.info(
                "Previously known ads ( %s ) skipped due to refresh policy. The refresh policy set to: %s days",
                len(skipped_known_ids),
                self.config.refresh_policy.stale_after_days
            )

        return links_to_scrape

    def _extract_ad_links_from_page(
        self,
        driver: webdriver.Chrome,
        original_url: str,
        page_data: dict,
    ) -> list[dict]:
        ad_links_list = list()

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

            for ad in visible_ads:
                link = self._parse_direct_link(ad.get_attribute("href"))
                if link and link not in self.seen_direct_links:
                    ad_links_list.append(
                        {
                            "origin_url": original_url,
                            "link": link,
                            "title": ad.find_element(By.TAG_NAME, "span").text,
                            "input_location": page_data["input_location"],
                            "resolved_location": page_data["resolved_location"],
                            "geo_id": page_data["geo_id"],
                            "job_title": page_data["job_title"],
                        }
                    )
                self.seen_direct_links.add(link)

        return ad_links_list

    def _get_raw_job_descriptions(
        self,
        driver: webdriver.Chrome,
        direct_links: list[dict[str, Any]],
        execution_ts: datetime,
    ) -> list["RawJobAd"]:
        job_descriptions: list[RawJobAd] = []

        total_links = len(direct_links)
        last_reported_pct = -1

        logging.info("Starting parsing of %s direct job links", total_links)

        for idx, link_dict in enumerate(direct_links, start=1):
            if total_links > 0:
                current_pct = int((idx / total_links) * 100)
                progress_bucket = (current_pct // 10) * 10

                if progress_bucket != last_reported_pct and progress_bucket > 0:
                    logging.info(
                        "Job description parsing %s%% finished (%s/%s)",
                        progress_bucket,
                        idx,
                        total_links,
                    )
                    last_reported_pct = progress_bucket

            direct_url = link_dict["link"]
            title = link_dict["title"]

            try:
                time.sleep(random.randint(1,3))
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
                    By.XPATH, "./div[1]"
                ).find_elements(By.TAG_NAME, "span")

                company_info_parts = [
                    item.text.strip() for item in spans if item.text.strip()
                ]
                company_infos = " ".join(company_info_parts)
                parsed_info = parse_linkedin_company_info(company_info_parts)

                company_name = parent_div.find_element(By.TAG_NAME, "a").text

                posted_date = None
                if parsed_info["posted_days_ago"] is not None:
                    posted_date = (
                        execution_ts.date()
                        - timedelta(days=parsed_info["posted_days_ago"])
                    )

                full_ad_description = " ".join([company_infos, about_data])

                job_descriptions.append(
                    RawJobAd(
                        source="linkedin",
                        ad_id=ad_id,
                        title=title,
                        company_name=company_name,
                        description=full_ad_description,
                        input_location=link_dict["input_location"],
                        job_location=parsed_info["location"],
                        posted_date=posted_date,
                        work_mode=parsed_info["work_mode"],
                        ad_link=f"https://www.linkedin.com/jobs/view/{ad_id}/",
                        first_scraped_at=execution_ts,
                        last_scraped_at=execution_ts,
                        last_seen_at=execution_ts,
                        metadata={
                            "origin_url": link_dict["origin_url"],
                            "input_location": link_dict["input_location"],
                            "resolved_location": parsed_info["location"],
                            "posted_days_ago": parsed_info["posted_days_ago"],
                            "geo_id": link_dict["geo_id"],
                            "work_mode": parsed_info["work_mode"],
                            "job_title": link_dict["job_title"],
                        },
                    )
                )

            except Exception:
                logging.exception("Failed to parse ad %s", direct_url)

        logging.info(
            "Finished parsing direct job links. Parsed %s ads successfully",
            len(job_descriptions),
        )
        return job_descriptions

    def _get_job_id_from_url(self, url: str) -> int:
        return int(
            url.replace("https://www.linkedin.com/jobs/view/", "").split("/")[0]
        )

    def extract_geo_suggestions_from_html(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[dict[str, str]] = []

        container = soup.find(
            "div",
            attrs={"data-testid": "typeahead-results-container"},
        )
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
        location: str,
        wait_seconds: int = 10,
    ) -> list[dict[str, Any]]:
        wait = WebDriverWait(driver, wait_seconds)

        driver.get("https://www.linkedin.com/jobs/")

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
        suggestions = self.extract_geo_suggestions_from_html(driver.page_source)

        filtered_suggestions = [
            item for item in suggestions if location.lower() in item["name"].lower()
        ]
        suggestions_to_use = filtered_suggestions or suggestions

        results: list[dict[str, Any]] = []
        for item in suggestions_to_use:
            resolved_location = item["name"]

            #TODO Temp flag to use only the input location
            if resolved_location != location:
                continue
            geo_id = item["geo_id"]

            parts = [p.strip() for p in resolved_location.split(",")]
            country = parts[-1] if len(parts) >= 2 else None
            region = parts[0] if parts else None

            results.append(
                {
                    "resolved_location": resolved_location,
                    "geo_id": geo_id,
                    "country": country,
                    "region": region,
                }
            )

        return results


def extract_posted_days_ago(value: str | None) -> int | None:
    if not value:
        return None

    text = value.strip().lower()

    if "minute" in text or "hour" in text:
        return 0

    match = re.search(r"(\d+)", text)
    if not match:
        return None

    amount = int(match.group(1))

    if "day" in text:
        return amount
    if "week" in text:
        return amount * 7
    if "month" in text:
        return amount * 30
    if "year" in text:
        return amount * 365

    return None


def extract_work_mode(parts: list[str] | None) -> str | None:
    if not parts:
        return None

    normalized = set()
    for part in parts:
        if part and part.strip():
            text = part.strip().lower()
            text = text.replace("–", "-").replace("—", "-")
            normalized.add(text)

    if WorkMode.HYBRID in normalized:
        return WorkMode.HYBRID
    if WorkMode.REMOTE in normalized:
        return WorkMode.REMOTE
    if "on-site" in normalized or "onsite" in normalized or "on site" in normalized:
        return WorkMode.ON_SITE

    return None


def parse_linkedin_company_info(parts: list[str] | None) -> dict[str, Any]:
    if not parts:
        return {
            "location": None,
            "posted_days_ago": None,
            "work_mode": None,
        }

    cleaned_parts = [part.strip() for part in parts if part and part.strip()]

    return {
        "location": cleaned_parts[0] if cleaned_parts else None,
        "posted_days_ago": extract_posted_days_ago(
            cleaned_parts[1] if len(cleaned_parts) > 1 else None
        ),
        "work_mode": extract_work_mode(cleaned_parts),
    }