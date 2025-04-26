# Job Finder API

A FastAPI-based job search API that scrapes job listings from LinkedIn, uses an LLM to rank the jobs based on relevance, and generates a summary for each job.

## Features

- Multi-source job aggregation (LinkedIn, Indeed, Glassdoor)
- LLM-powered job relevance filtering
- Structured job data output
- Async job scraping
- Error handling and logging

## Prerequisites

- Python 3.8+
- Chrome browser installed
- GroqCloud API key
- LinkedIn account (for scraping)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/job-finder-api.git
cd job-finder-api
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. **Important: Environment Setup**
   Create a `.env` file in the root directory with your credentials. This file is required for the application to work properly:

   ```env
   # Required API Keys and Credentials
   GROQ_API_KEY=your_groq_api_key_here
   LINKEDIN_EMAIL=your_linkedin_email
   LINKEDIN_PASSWORD=your_linkedin_password
   
   # Optional Settings
   DEBUG_MODE=true
   ```

   **Note:** 
   - The `.env` file is included in `.gitignore` to protect your credentials
   - Never commit your `.env` file to version control
   - You can get a Groq API key by signing up at [GroqCloud](https://console.groq.com/)
   - Use your LinkedIn account credentials for scraping

## Logging and Reload Issues

**Important:**
- File logging (writing logs to a file) has been disabled in this project to prevent issues with Uvicorn's auto-reload feature.
- Only console logging is enabled by default. All logs will appear in your terminal.
- This prevents infinite reload loops caused by log file changes being detected by the file watcher.
- If you want to enable file logging, ensure the log file is outside your project directory or use Uvicorn's `--reload-exclude` option to ignore it.

## Usage

1. Start the API server:
```bash
uvicorn src.main:app --reload
```

- Logs will appear in your terminal only. No log file will be created or modified by default.

2. The API will be available at `http://localhost:8000`

3. Use the following endpoint to search for jobs:

```bash
POST /search-jobs
```

Request body:
```json
{
    "position": "Full Stack Developer",
    "experience": "2 years",
    "salary": "70000 PKR to 120000 PKR",
    "jobNature": "Remote",
    "location": "Islamabad, Pakistan",
    "skills": "React.js, Node.js, MongoDB, Express.js"
}
```

Response:
```json
{
    "relevant_jobs": [
        {
            "job_title": "Senior Full Stack Developer",
            "company": "Tech Corp",
            "experience": "2-3 years",
            "jobNature": "Remote",
            "location": "Islamabad, Pakistan",
            "salary": "80000-120000 PKR",
            "apply_link": "https://example.com/job/123",
            "description": "We are looking for a Full Stack Developer...",
            "source": "LinkedIn",
            "summary": "A senior full-stack role focusing on web development..."
        }
    ]
}
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
job-finder-api/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── models/
│   │   ├── job_listing.py
│   │   ├── job_search_criteria.py
│   │   ├── job_search_response.py
│   │   └── __init__.py
│   └── services/
│       ├── job_scraper.py   # Main job scraping service
│       ├── linkedin_scraper.py # LinkedIn scraping logic
│       ├── llm_processor.py # LLM-based job filtering and summary
│       ├── groq_service.py  # LLM API integration
│       └── __init__.py
├── cache/                   # Cached job results (JSON)
├── requirements.txt
├── .env
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the amazing web framework
- Meta Llama for the LLM capabilities
- Selenium for web scraping capabilities