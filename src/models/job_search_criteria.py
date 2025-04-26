from pydantic import BaseModel

class JobSearchCriteria(BaseModel):
    position: str
    experience: str
    salary: str
    jobNature: str
    location: str
    skills: str

    class Config:
        json_schema_extra = {
            "example": {
                "position": "Full Stack Developer",
                "experience": "2 years",
                "salary": "70000 PKR to 120000 PKR",
                "jobNature": "onsite",
                "location": "Islamabad, Pakistan",
                "skills": "React.js, Node.js, MongoDB, Express.js"
            }
        } 