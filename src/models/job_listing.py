from pydantic import BaseModel
from typing import Optional

class JobListing(BaseModel):
    job_title: str
    company: str
    experience: Optional[str] = ""
    jobNature: Optional[str] = "Not specified"
    location: Optional[str] = ""
    salary: Optional[str] = "Not specified"
    apply_link: str
    description: Optional[str] = None
    source: Optional[str] = "LinkedIn"
    summary: Optional[str] = None 