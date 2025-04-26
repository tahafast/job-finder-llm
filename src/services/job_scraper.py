from typing import List, Optional
from ..models.job_listing import JobListing
from .linkedin_scraper import LinkedInScraper
import unicodedata
import re
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try to load environment variables
try:
    load_dotenv()
    logger.info("Environment variables loaded successfully")
except Exception as e:
    logger.warning(f"Error loading .env file: {str(e)}")

class JobScraper:
    def __init__(self):
        # Check for required environment variables
        required_vars = [
            'GROQ_API_KEY',
            'LINKEDIN_EMAIL',
            'LINKEDIN_PASSWORD'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        self.linkedin_scraper = LinkedInScraper()
        self.cache_dir = "cache"
        self.cache_duration = timedelta(hours=4)  # Cache results for 4 hours
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text while preserving valid UTF-8 characters."""
        if not text:
            return ""
        try:
            # Normalize unicode characters
            text = unicodedata.normalize('NFKC', text)
            
            # Remove control characters but keep newlines and tabs
            text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\t')
            
            # Replace multiple whitespace with single space
            text = re.sub(r'\s+', ' ', text)
            
            # Strip leading/trailing whitespace
            text = text.strip()
            
            return text
        except Exception as e:
            logger.error(f"Error sanitizing text: {str(e)}")
            # If all else fails, try basic ASCII conversion
            return text.encode('ascii', errors='ignore').decode('ascii')

    def _save_jobs_to_json(self, jobs: List[JobListing], criteria, filename: str = "jobs.json"):
        """Save job listings to a JSON file with search criteria"""
        try:
            # Create data structure with criteria and jobs
            data = {
                "criteria": {
                    "position": criteria.position,
                    "experience": criteria.experience,
                    "salary": criteria.salary,
                    "jobNature": criteria.jobNature,
                    "location": criteria.location,
                    "skills": criteria.skills
                },
                "timestamp": datetime.now().isoformat(),
                "jobs": [job.dict() for job in jobs]
            }
            
            # Create a filename based on search criteria
            search_hash = f"{criteria.position}_{criteria.location}".lower().replace(" ", "_")
            filename = f"{search_hash}_linkedin_{filename}"
            filepath = os.path.join(self.cache_dir, filename)
            
            # Save to JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(jobs)} jobs to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving jobs to JSON: {str(e)}")
            return None

    def _get_cached_json_results(self, criteria) -> Optional[List[JobListing]]:
        """Try to get results from JSON cache based on search criteria"""
        try:
            search_hash = f"{criteria.position}_{criteria.location}".lower().replace(" ", "_")
            cache_pattern = os.path.join(self.cache_dir, f"{search_hash}_*.json")
            
            # Find matching cache files
            import glob
            cache_files = glob.glob(cache_pattern)
            
            if not cache_files:
                return None
                
            # Get the most recent cache file
            latest_cache = max(cache_files, key=os.path.getctime)
            
            # Check if cache is still valid
            file_time = datetime.fromtimestamp(os.path.getmtime(latest_cache))
            if datetime.now() - file_time > self.cache_duration:
                logger.info(f"Cache expired for {latest_cache}")
                return None
                
            # Load and parse the cache
            with open(latest_cache, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Convert dictionary back to JobListing objects
            return [JobListing(**job) for job in data["jobs"]]
            
        except Exception as e:
            logger.error(f"Error reading JSON cache: {str(e)}")
            return None

    async def scrape_jobs(self, criteria) -> List[JobListing]:
        """Scrape jobs with caching and JSON storage"""
        try:
            # First try to get results from JSON cache
            cached_jobs = self._get_cached_json_results(criteria)
            if cached_jobs:
                logger.info("Using cached JSON results")
                return cached_jobs

            # If no cache, scrape new jobs
            sanitized_criteria = type(criteria)(
                position=self._sanitize_text(criteria.position),
                experience=self._sanitize_text(criteria.experience),
                salary=self._sanitize_text(criteria.salary),
                jobNature=self._sanitize_text(criteria.jobNature),
                location=self._sanitize_text(criteria.location),
                skills=self._sanitize_text(criteria.skills)
            )
            
            # Scrape from LinkedIn
            try:
                logger.info("Starting LinkedIn scraping...")
                jobs = await self.linkedin_scraper.scrape(sanitized_criteria)
                if jobs:
                    logger.info(f"Found {len(jobs)} jobs from LinkedIn")
                    # Save results to cache
                    self._save_jobs_to_json(jobs, criteria)
                    logger.info(f"Successfully scraped and saved {len(jobs)} jobs")
                    return jobs
                else:
                    logger.warning("No jobs found from LinkedIn")
                    return []
            except Exception as e:
                error_msg = f"Error scraping LinkedIn: {str(e)}"
                logger.error(error_msg)
                return []
            
        except Exception as e:
            logger.error(f"Error in scrape_jobs: {str(e)}")
            return [] 