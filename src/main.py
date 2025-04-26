# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import json
import traceback
import sys
import logging
from logging.handlers import RotatingFileHandler
import os
import glob
from datetime import datetime, timedelta

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.models.job_search_criteria import JobSearchCriteria
from src.models.job_search_response import JobSearchResponse
from src.services.job_scraper import JobScraper
from src.services.llm_processor import LLMProcessor
from src.models.job_listing import JobListing

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log the Python path and current directory for debugging
logger.debug(f"Python path: {sys.path}")
logger.debug(f"Current directory: {os.getcwd()}")

app = FastAPI(
    title="Job Search API",
    description="API for searching jobs across multiple platforms",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
job_scraper = JobScraper()
llm_processor = LLMProcessor()

def get_cached_jobs(criteria: JobSearchCriteria, cache_duration: timedelta = timedelta(hours=4)) -> Optional[List[JobListing]]:
    """Get jobs from cached JSON files"""
    try:
        # Create search pattern based on criteria
        search_hash = f"{criteria.position}_{criteria.location}".lower().replace(" ", "_")
        cache_dir = "cache"
        cache_pattern = os.path.join(cache_dir, f"{search_hash}_*.json")
        
        # Find matching cache files
        cache_files = glob.glob(cache_pattern)
        
        if not cache_files:
            return None
            
        # Get the most recent cache file
        latest_cache = max(cache_files, key=os.path.getctime)
        
        # Check if cache is still valid
        file_time = datetime.fromtimestamp(os.path.getmtime(latest_cache))
        if datetime.now() - file_time > cache_duration:
            logger.info(f"Cache expired for {latest_cache}")
            return None
            
        # Load and parse the cache
        with open(latest_cache, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Convert dictionary to JobListing objects
        jobs = [JobListing(**job) for job in data["jobs"]]
        logger.info(f"Found {len(jobs)} jobs in cache")
        return jobs
        
    except Exception as e:
        logger.error(f"Error reading cache: {str(e)}")
        return None

@app.get("/")
async def root():
    return {"message": "Welcome to the Job Search API"}

@app.post(
    "/search-jobs",
    response_model=JobSearchResponse,
    responses={
        200: {"model": JobSearchResponse},
        400: {"model": dict},
        500: {"model": dict}
    }
)
async def search_jobs(criteria: JobSearchCriteria):
    try:
        # First try to get jobs from cache
        cached_jobs = get_cached_jobs(criteria)
        
        if cached_jobs:
            logger.info("Using cached jobs")
            # Process cached jobs through LLM
            processed_jobs = await llm_processor.process_jobs(cached_jobs, criteria)
            return JobSearchResponse(relevant_jobs=processed_jobs)
        
        # If no cache, scrape new jobs
        logger.info("No cache found, scraping new jobs")
        jobs = await job_scraper.scrape_jobs(criteria)
        
        if not jobs:
            return JobSearchResponse(relevant_jobs=[])
        
        # Process and rank jobs using LLM
        processed_jobs = await llm_processor.process_jobs(jobs, criteria)
        
        return JobSearchResponse(relevant_jobs=processed_jobs)
        
    except Exception as e:
        logger.error(f"Error in search_jobs: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check if the API is running."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 