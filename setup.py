from setuptools import setup, find_packages

setup(
    name="job_finder",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-dotenv==1.0.0",
        "httpx==0.25.1",
        "beautifulsoup4==4.12.2",
        "selenium==4.15.2",
        "langchain==0.0.350",
        "openai==1.3.5",
        "pydantic==2.5.2",
        "python-multipart==0.0.6",
        "requests==2.31.0",
        "webdriver-manager==4.0.1",
        "groq==0.23.0",
        "langchain-groq==0.3.2",
    ],
    python_requires=">=3.8",
) 