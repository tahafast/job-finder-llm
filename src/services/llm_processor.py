from typing import List
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from ..models.job_listing import JobListing
import os
from dotenv import load_dotenv
import logging
import json
from pathlib import Path
from ..models.job_search_criteria import JobSearchCriteria
import glob
import asyncio
import time

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

class LLMProcessor:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0.3,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.last_api_call = 0
        self.min_delay_between_calls = 3  # seconds between API calls

    async def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits by adding delays between API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_delay_between_calls:
            delay = self.min_delay_between_calls - time_since_last_call
            await asyncio.sleep(delay)
        
        self.last_api_call = time.time()

    async def generate_job_summary(self, job: JobListing) -> str:
        """Generate a concise summary of the job description"""
        try:
            # If the job already has a valid summary, return it
            if job.summary and job.summary != "Unable to generate summary.":
                return job.summary

            # Check if we're hitting the daily rate limit (if retry time is too long)
            if hasattr(self, 'daily_limit_reached') and self.daily_limit_reached:
                return "Summary generation paused - daily API limit reached. Please try again tomorrow."

            template = """Analyze this job description and provide a concise summary highlighting the key aspects of the role.
Always respond in English, even if the job description is in another language.
Include the main responsibilities, required skills, and any notable benefits or requirements.

Job Details:
Title: {title}
Company: {company}
Experience: {experience}
Location: {location}
Job Type: {job_type}
Salary: {salary}

Description:
{description}

Provide a clear and concise summary in 3-4 sentences."""

            summary_prompt = ChatPromptTemplate.from_template(template)
            summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)

            try:
                # Wait for rate limit before making API call
                await self._wait_for_rate_limit()

                response = await summary_chain.ainvoke({
                    "title": job.job_title,
                    "company": job.company,
                    "experience": job.experience or "Not specified",
                    "location": job.location or "Not specified",
                    "job_type": job.jobNature or "Not specified",
                    "salary": job.salary or "Not specified",
                    "description": job.description or "Not provided"
                })

                if response and 'text' in response:
                    return response['text'].strip()
                return "Unable to generate summary."
            except Exception as e:
                error_str = str(e).lower()
                
                if "rate_limit" in error_str:
                    # Check if retry time is very long (indicating daily limit)
                    try:
                        import re
                        time_match = re.search(r'try again in (\d+)m([\d.]+)s', error_str)
                        if time_match:
                            minutes, seconds = time_match.groups()
                            wait_time = float(minutes) * 60 + float(seconds)
                            if wait_time > 300:  # If wait time is more than 5 minutes
                                self.daily_limit_reached = True
                                logger.warning("Daily API rate limit reached. Please try again tomorrow.")
                                return "Summary generation paused - daily API limit reached. Please try again tomorrow."
                    except:
                        pass
                
                logger.error(f"Error generating summary: {str(e)}")
                return "Unable to generate summary due to API limits. Please try again later."

        except Exception as e:
            logger.error(f"Error generating summary for job {job.job_title}: {str(e)}")
            return "Unable to generate summary."

    def load_cached_jobs(self, query_params: dict) -> List[dict]:
        """Load jobs from cache based on query parameters"""
        try:
            # Create a cache filename based on query parameters
            position = query_params.get('position', '').lower().replace(' ', '_')
            location = query_params.get('location', '').lower().replace(' ', '_').replace(',', '')
            
            # Look for any cache file matching the position and location
            cache_pattern = f"cache/*_{position}_{location}_*.json"
            cache_files = glob.glob(cache_pattern)
            
            if not cache_files:
                return None
                
            # Get the most recent cache file
            latest_cache = max(cache_files, key=os.path.getctime)
            
            with open(latest_cache, 'r', encoding='utf-8') as f:
                return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error loading cached jobs: {str(e)}")
            return None

    def save_processed_jobs(self, jobs: List[JobListing], query_params: JobSearchCriteria):
        """Save processed jobs back to cache"""
        try:
            position = query_params.position.lower().replace(' ', '_')
            location = query_params.location.lower().replace(' ', '_').replace(',', '')
            sources = "_".join(sorted(set(job.source for job in jobs)))
            cache_file = f"cache/{position}_{location}_{sources}_jobs.json"
            
            # Ensure cache directory exists
            Path("cache").mkdir(exist_ok=True)
            
            # Convert JobListing objects to dictionaries
            jobs_data = [job.__dict__ for job in jobs]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving processed jobs: {str(e)}")

    async def process_jobs(self, jobs: List[JobListing], criteria: dict) -> List[JobListing]:
        """Process jobs and generate summaries"""
        try:
            if not jobs:
                logger.warning("No jobs to process")
                return []

            logger.info(f"Processing {len(jobs)} jobs")
            processed_jobs = []
            
            for job in jobs:
                try:
                    # Skip if job already has a valid summary
                    if job.summary and job.summary != "Unable to generate summary.":
                        processed_jobs.append(job)
                        continue

                    # Check if we've hit the daily limit
                    if hasattr(self, 'daily_limit_reached') and self.daily_limit_reached:
                        job.summary = "Summary generation paused - daily API limit reached. Please try again tomorrow."
                        processed_jobs.append(job)
                        continue

                    # Generate job summary
                    summary = await self.generate_job_summary(job)
                    
                    # Create processed job with summary
                    processed_job = JobListing(
                        job_title=job.job_title,
                        company=job.company,
                        experience=job.experience or "",
                        jobNature=job.jobNature or "Not specified",
                        location=job.location or "",
                        salary=job.salary or "Not specified",
                        apply_link=job.apply_link,
                        description=job.description or "",
                        source=job.source or "LinkedIn",
                        summary=summary
                    )
                    processed_jobs.append(processed_job)

                    # If we hit the daily limit, stop processing more jobs
                    if hasattr(self, 'daily_limit_reached') and self.daily_limit_reached:
                        break

                except Exception as e:
                    logger.error(f"Error processing job {job.job_title}: {str(e)}")
                    processed_jobs.append(job)

            # Save processed jobs back to cache
            self.save_processed_jobs(processed_jobs, criteria)
            return processed_jobs

        except Exception as e:
            logger.error(f"Error processing jobs: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            return jobs 