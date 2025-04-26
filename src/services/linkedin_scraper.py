# -*- coding: utf-8 -*-
from typing import List
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from ..models.job_listing import JobListing
import re
import logging
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)
load_dotenv()

class LinkedInScraper:
    def __init__(self):
        self.base_url = "https://www.linkedin.com"
        self.login_url = "https://www.linkedin.com/login"
        self.driver = None
        self.max_retries = 3
        self.min_delay = 3  # Increased minimum delay
        self.max_delay = 7  # Increased maximum delay
        self.email = os.getenv("LINKEDIN_EMAIL")
        self.password = os.getenv("LINKEDIN_PASSWORD")
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        # Define selectors for company and location
        self.company_selectors = [
            ".job-card-container__company-name",
            ".job-card-container__primary-description",
            ".job-card-list__company-name",
            ".artdeco-entity-lockup__subtitle",
            ".job-card-container__metadata-wrapper a",
            "[data-control-name='company_link']",
            ".job-card-container__company-link",
            ".result-card__subtitle.job-result-card__subtitle",
            ".base-search-card__subtitle",
            ".job-search-card__company-name"
        ]
        
        self.location_selectors = [
            ".job-card-container__metadata-item",
            ".job-card-container__metadata-wrapper span",
            ".job-search-card__location",
            ".artdeco-entity-lockup__caption",
            ".job-card-list__footer-wrapper span",
            ".job-result-card__location",
            ".base-search-card__metadata span",
            "[data-job-location]"
        ]
        
        if not self.email or not self.password:
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in environment variables")
        logger.info("LinkedIn scraper initialized")

    def _random_delay(self):
        """Add random delay between requests to avoid detection"""
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _init_driver(self):
        try:
            chrome_options = Options()
            if not self.debug_mode:
                chrome_options.add_argument("--headless")
            
            # Essential options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # Add random user agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ]
            chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
            
            # Set Chrome binary location for Render
            chrome_options.binary_location = "/usr/bin/google-chrome"
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            
            # Set window size explicitly after creation
            self.driver.set_window_size(1920, 1080)
            
            # Execute CDP commands to make the browser look more human-like
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })
            
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Chrome driver: {str(e)}")
            raise

    def _login(self):
        """Login to LinkedIn with improved error handling"""
        max_login_attempts = 3
        for attempt in range(max_login_attempts):
            try:
                logger.info(f"Attempting to log in to LinkedIn (attempt {attempt + 1}/{max_login_attempts})...")
                
                # Clear any existing session
                self.driver.delete_all_cookies()
                self._random_delay()
                
                # Load login page
                self.driver.get(self.login_url)
                self._random_delay()
                
                # Check if we're already logged in
                if "feed" in self.driver.current_url:
                    logger.info("Already logged in to LinkedIn")
                    return True
                
                # Wait for login form
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "username"))
                    )
                except TimeoutException:
                    logger.error("Login form not found")
                    continue
                
                # Fill email with human-like typing
                email_field = self.driver.find_element(By.ID, "username")
                email_field.clear()
                for char in self.email:
                    email_field.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.3))
                self._random_delay()
                
                # Fill password with human-like typing
                password_field = self.driver.find_element(By.ID, "password")
                password_field.clear()
                for char in self.password:
                    password_field.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.3))
                self._random_delay()
                
                # Click sign in button
                sign_in_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                sign_in_button.click()
                self._random_delay()
                
                # Verify login success with multiple checks
                verification_methods = [
                    lambda: "feed" in self.driver.current_url,
                    lambda: self.driver.find_elements(By.CSS_SELECTOR, ".global-nav__me") != [],
                    lambda: self.driver.find_elements(By.CSS_SELECTOR, ".feed-identity-module") != [],
                    lambda: self.driver.find_elements(By.CSS_SELECTOR, ".search-global-typeahead__input") != []
                ]
                
                for verify in verification_methods:
                    try:
                        if verify():
                            logger.info("Successfully logged in to LinkedIn")
                            return True
                    except:
                        continue
                
                logger.warning(f"Login verification failed on attempt {attempt + 1}")
                self._random_delay()
                
            except Exception as e:
                logger.error(f"Error during login attempt {attempt + 1}: {str(e)}")
                self._random_delay()
        
        logger.error("All login attempts failed")
        return False

    def _safe_find_element(self, by, value, wait_time=10, parent=None):
        """Safely find an element with retries and explicit wait"""
        for attempt in range(self.max_retries):
            try:
                if parent is None:
                    parent = self.driver
                element = WebDriverWait(parent, wait_time).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except (TimeoutException, StaleElementReferenceException) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to find element {value} after {self.max_retries} attempts")
                    raise
                self._random_delay()
        return None

    async def scrape(self, criteria) -> List[JobListing]:
        jobs = []
        try:
            self._init_driver()
            
            # Login to LinkedIn first
            if not self._login():
                raise Exception("Failed to login to LinkedIn")
            
            # Construct search URL with filters
            search_url = (
                f"{self.base_url}/jobs/search?"
                f"keywords={criteria.position}&"
                f"location={criteria.location}&"
                f"f_WT=2&"  # Remote jobs
                "sortBy=R"  # Sort by relevance
            )
            
            logger.info(f"Searching jobs with URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait longer for initial page load
            time.sleep(5)
            
            # Scroll down to load more jobs
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for scroll to complete
            except Exception as e:
                logger.warning(f"Failed to scroll: {str(e)}")
            
            self._random_delay()

            # Updated job container selectors for 2024 LinkedIn
            job_container_selectors = [
                "div.jobs-search-results-list",
                "ul.jobs-search-results__list",
                "ul.jobs-search__results-list",
                "main.jobs-search-results-list",
                "div.scaffold-layout__list",
                "div.jobs-search__job-details",
                "div.jobs-box"
            ]

            job_list = None
            for selector in job_container_selectors:
                try:
                    logger.debug(f"Trying to find job container with selector: {selector}")
                    # Wait longer for container
                    job_list = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if job_list:
                        logger.info(f"Found job container with selector: {selector}")
                        break
                except TimeoutException:
                    continue

            if not job_list:
                # Try to find any job-related element to debug
                try:
                    debug_selectors = [
                        "div[class*='jobs']",
                        "div[class*='job-']",
                        "ul[class*='jobs']",
                        "main[class*='jobs']"
                    ]
                    for selector in debug_selectors:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            logger.debug(f"Found {len(elements)} elements with debug selector: {selector}")
                except Exception as e:
                    logger.debug(f"Debug selector search failed: {str(e)}")
                    
                logger.error("Could not find job listings container with any selector")
                return []

            # Updated job card selectors for 2024 LinkedIn
            job_card_selectors = [
                "div.job-card-container",
                "li.jobs-search-results__list-item",
                "div.job-card-list__entity",
                "li.artdeco-list__item",
                "div[data-job-id]",
                "div.job-card-square",
                "li[class*='jobs-search-results']"
            ]
            
            job_elements = []
            for selector in job_card_selectors:
                try:
                    elements = job_list.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        job_elements = elements
                        logger.info(f"Found {len(elements)} job cards with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to find job cards with selector {selector}: {str(e)}")
                    continue

            if not job_elements:
                # Try direct search without container
                for selector in job_card_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            job_elements = elements
                            logger.info(f"Found {len(elements)} job cards directly with selector: {selector}")
                            break
                    except Exception:
                        continue

            if not job_elements:
                logger.error("No job cards found with any selector")
                return []

            # Add delay to ensure job cards are fully loaded
            logger.info("Waiting for job cards to fully load...")
            time.sleep(3)
            
            # Scroll to each job card to ensure it's in view and loaded
            for job_element in job_elements[:10]:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", job_element)
                    time.sleep(0.5)  # Short delay after each scroll
                except Exception as e:
                    logger.debug(f"Failed to scroll to job element: {str(e)}")

            for job_element in job_elements[:10]:  # Limit to first 10 jobs
                try:
                    # Updated selectors for job details for 2024 LinkedIn
                    title_selectors = [
                        "h3.job-card-list__title",
                        "h3.base-search-card__title",
                        "h3[class*='job-card']",
                        "a[class*='job-card-list__title']",
                        "a[class*='job-card-container__link']",
                        ".job-card-container__title",
                        ".job-card-list__title",
                        "h3.base-card__title",
                        ".base-card__full-link",
                        ".job-card-list__entity-lockup",
                        "h3.job-search-card__title",
                        # New dynamic selectors
                        "[data-job-title]",
                        "[aria-label*='job']",
                        "[role='heading']",
                        "a[href*='jobs/view']"
                    ]
                    
                    # First try to get job ID and construct title selector
                    try:
                        job_id = job_element.get_attribute('data-job-id')
                        if job_id:
                            logger.debug(f"Found job ID: {job_id}")
                            # Try to find title using job ID
                            id_specific_selectors = [
                                f"[data-job-id='{job_id}'] h3",
                                f"[data-job-id='{job_id}'] a",
                                f"#job-card-{job_id} h3",
                                f"#job-card-{job_id} a"
                            ]
                            title_selectors = id_specific_selectors + title_selectors
                    except Exception as e:
                        logger.debug(f"Could not get job ID: {str(e)}")

                    # Extract job title with multiple methods
                    title = None
                    
                    # Method 1: Direct element search
                    for selector in title_selectors:
                        try:
                            title_elem = job_element.find_element(By.CSS_SELECTOR, selector)
                            if title_elem:
                                # Try multiple ways to get the text
                                title = (title_elem.text.strip() or 
                                       title_elem.get_attribute('title') or 
                                       title_elem.get_attribute('aria-label') or
                                       title_elem.get_attribute('data-job-title'))
                                if title:
                                    logger.debug(f"Found title using selector {selector}: {title}")
                                    break
                        except Exception:
                            continue
                    
                    # Method 2: Try to find any clickable element first
                    if not title:
                        try:
                            clickable = job_element.find_element(By.CSS_SELECTOR, "a")
                            if clickable:
                                title = (clickable.text.strip() or 
                                       clickable.get_attribute('title') or 
                                       clickable.get_attribute('aria-label'))
                                if title:
                                    logger.debug(f"Found title from clickable element: {title}")
                        except Exception:
                            pass
                    
                    # Method 3: Try to find any heading
                    if not title:
                        try:
                            heading = job_element.find_element(By.CSS_SELECTOR, "h3, h2, h4")
                            if heading:
                                title = heading.text.strip()
                                if title:
                                    logger.debug(f"Found title from heading: {title}")
                        except Exception:
                            pass
                    
                    # Method 4: Check for iframes
                    if not title:
                        try:
                            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                            for iframe in iframes:
                                try:
                                    self.driver.switch_to.frame(iframe)
                                    for selector in title_selectors:
                                        try:
                                            title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                                            title = title_elem.text.strip()
                                            if title:
                                                logger.debug(f"Found title in iframe: {title}")
                                                break
                                        except Exception:
                                            continue
                                    self.driver.switch_to.default_content()
                                    if title:
                                        break
                                except Exception:
                                    self.driver.switch_to.default_content()
                                    continue
                        except Exception as e:
                            logger.debug(f"Error checking iframes: {str(e)}")
                    
                    # Method 5: Try to get any text content if still no title
                    if not title:
                        try:
                            # Get all text content from the job card
                            text_content = job_element.text.split('\n')
                            # Try to identify the title (usually the first non-empty line)
                            for line in text_content:
                                if line.strip() and not any(x in line.lower() for x in ['company', 'location', 'salary']):
                                    title = line.strip()
                                    logger.debug(f"Found title from text content: {title}")
                                    break
                        except Exception as e:
                            logger.debug(f"Error getting text content: {str(e)}")
                    
                    if not title:
                        logger.warning("Could not find job title")
                        # Log the HTML content for debugging
                        try:
                            logger.debug(f"Job card HTML: {job_element.get_attribute('outerHTML')}")
                        except Exception:
                            pass
                        continue
                    
                    # Extract company name
                    company = None
                    for selector in self.company_selectors:
                        try:
                            company_elem = job_element.find_element(By.CSS_SELECTOR, selector)
                            if company_elem:
                                company = company_elem.text.strip()
                                if company:
                                    break
                        except Exception:
                            continue
                    
                    # Extract location
                    location = None
                    for selector in self.location_selectors:
                        try:
                            location_elem = job_element.find_element(By.CSS_SELECTOR, selector)
                            if location_elem:
                                location = location_elem.text.strip()
                                if location:
                                    break
                        except Exception:
                            continue
                    
                    # Click on job card to get more details
                    try:
                        # Try multiple click methods
                        try:
                            job_element.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", job_element)
                        
                        self._random_delay()
                    except Exception as e:
                        logger.warning(f"Failed to click job card: {str(e)}")
                        continue
                    
                    # Updated description selectors for 2024 LinkedIn
                    description_selectors = [
                        "div.jobs-description-content__text",
                        "div.jobs-box__html-content",
                        "div[class*='jobs-description']",
                        "div[class*='job-view-layout']",
                        "div.show-more-less-html__markup"
                    ]
                    
                    description = None
                    for selector in description_selectors:
                        try:
                            # Wait longer for description
                            desc_elem = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if desc_elem:
                                description = desc_elem.text.strip()
                                if description:
                                    break
                        except Exception:
                            continue
                    
                    if not description:
                        logger.warning("Could not find job description")
                        continue
                    
                    # Extract salary and experience
                    salary = self._extract_salary(description)
                    experience = self._extract_experience(description)
                    
                    # Get application link
                    apply_link = self.driver.current_url
                    
                    jobs.append(JobListing(
                        job_title=title,
                        company=company,
                        experience=experience,
                        jobNature=criteria.jobNature,
                        location=location,
                        salary=salary,
                        apply_link=apply_link,
                        description=description,
                        source="LinkedIn"
                    ))
                    
                    logger.info(f"Successfully processed job: {title} at {company}")
                    
                except Exception as e:
                    logger.error(f"Error processing LinkedIn job: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Chrome driver closed")
            
        return jobs

    def _extract_salary(self, description: str) -> str:
        """Extract salary information using regex patterns"""
        patterns = [
            r'\$[\d,]+ - \$[\d,]+(?:/year|/hr|/month)?',
            r'\$[\d,]+(?:/year|/hr|/month)',
            r'[\d,]+ - [\d,]+k',
            r'[\d,]+k',
            r'(?:USD|EUR|GBP|PKR) [\d,]+(?:k)?(?:/year|/hr|/month)?',
            r'(?:Rs|RS|rs)\s*\.?\s*[\d,]+(?:k)?(?:/year|/hr|/month)?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return "Not specified"

    def _extract_experience(self, description: str) -> str:
        """Extract experience requirements using regex patterns"""
        patterns = [
            r'(\d+\+?\s*-\s*\d+\+?\s*years?.*experience)',
            r'(\d+\+?\s*years?.*experience)',
            r'(minimum.*\d+\s*years?.*experience)',
            r'(at least.*\d+\s*years?.*experience)',
            r'(senior.*level)',
            r'(mid.*level)',
            r'(entry.*level)',
            r'(fresher)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return "Not specified"

    def _extract_job_title(self, job_element):
        """Extract job title from a job card element using multiple methods."""
        title_selectors = [
            '[data-job-title]',
            '.job-card-list__title',
            '.job-card-container__link',
            '.jobs-unified-top-card__job-title',
            'h2.job-card-list__title',
            'h3.job-card-list__title',
            'a[data-control-name="job_card_title"]',
            '[aria-label*="job"]',
            '.job-card-container__link-wrapper',
            '.job-card-list__entity-lockup',
            '.artdeco-entity-lockup__title',
            '.job-details-jobs-unified-top-card__job-title'
        ]

        # Method 1: Try direct element search with expanded selectors
        for selector in title_selectors:
            try:
                title_element = job_element.find_element(By.CSS_SELECTOR, selector)
                if title := self._get_element_text(title_element):
                    logger.debug(f"Found title using selector {selector}: {title}")
                    return title
            except NoSuchElementException:
                continue

        # Method 2: Try using job ID to construct specific selectors
        try:
            job_id = job_element.get_attribute('data-job-id')
            if job_id:
                specific_selectors = [
                    f'[data-job-id="{job_id}"] h3',
                    f'[data-job-id="{job_id}"] .job-card-list__title',
                    f'[data-job-id="{job_id}"] a'
                ]
                for selector in specific_selectors:
                    try:
                        title_element = job_element.find_element(By.CSS_SELECTOR, selector)
                        if title := self._get_element_text(title_element):
                            logger.debug(f"Found title using job ID selector {selector}: {title}")
                            return title
                    except NoSuchElementException:
                        continue
        except Exception as e:
            logger.debug(f"Error using job ID method: {str(e)}")

        # Method 3: Look for any clickable elements that might contain the title
        try:
            links = job_element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                if title := self._get_element_text(link):
                    if len(title) > 10:  # Basic validation that it looks like a title
                        logger.debug(f"Found title in link: {title}")
                        return title
        except Exception as e:
            logger.debug(f"Error searching links: {str(e)}")

        # Method 4: Look for any heading elements
        for tag in ['h1', 'h2', 'h3', 'h4']:
            try:
                headings = job_element.find_elements(By.TAG_NAME, tag)
                for heading in headings:
                    if title := self._get_element_text(heading):
                        logger.debug(f"Found title in heading {tag}: {title}")
                        return title
            except Exception as e:
                logger.debug(f"Error searching {tag} tags: {str(e)}")

        # Method 5: Check for iframes
        try:
            iframes = job_element.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    for selector in title_selectors:
                        try:
                            title_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if title := self._get_element_text(title_element):
                                logger.debug(f"Found title in iframe: {title}")
                                return title
                        except NoSuchElementException:
                            continue
                finally:
                    self.driver.switch_to.default_content()
        except Exception as e:
            logger.debug(f"Error checking iframes: {str(e)}")

        # Method 6: Last resort - try to extract from the entire card's text
        try:
            card_text = job_element.text
            if card_text:
                # Try to find a reasonable title in the text
                lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                for line in lines:
                    # Look for lines that might be titles (not too short, not too long)
                    if 10 <= len(line) <= 100 and not line.startswith(('Company:', 'Location:', 'Posted:', 'Apply')):
                        logger.debug(f"Found potential title in card text: {line}")
                        return line
        except Exception as e:
            logger.debug(f"Error extracting from card text: {str(e)}")

        # Log the HTML content for debugging
        try:
            html_content = job_element.get_attribute('outerHTML')
            logger.debug(f"Could not find job title. Job card HTML:\n{html_content}")
        except Exception as e:
            logger.debug(f"Error logging HTML content: {str(e)}")

        return None

    def _get_element_text(self, element):
        """Extract text from an element using multiple methods."""
        try:
            # Try different attributes that might contain the title
            for attr in ['textContent', 'innerText', 'title', 'aria-label', 'data-job-title']:
                if text := element.get_attribute(attr):
                    text = text.strip()
                    if text and len(text) > 5:  # Basic validation
                        return text

            # Try direct text
            if text := element.text:
                text = text.strip()
                if text and len(text) > 5:
                    return text

            return None
        except Exception as e:
            logger.debug(f"Error extracting element text: {str(e)}")
            return None 