from pydantic import BaseModel
from typing import List
from .job_listing import JobListing

class JobSearchResponse(BaseModel):
    relevant_jobs: List[JobListing]

    class Config:
        json_schema_extra = {
            "example": {
                "relevant_jobs": [
                    {
                        "job_title": "Senior Full Stack Developer",
                        "company": "Tech Corp",
                        "experience": "2-3 years",
                        "jobNature": "onsite",
                        "location": "Islamabad, Pakistan",
                        "salary": "80000-120000 PKR",
                        "apply_link": "https://example.com/job/123",
                        "description": "We are looking for a Full Stack Developer...",
                        "source": "LinkedIn",
                        "summary": "A senior full-stack role focusing on web development..."
                    }
                ]
            }
        } 