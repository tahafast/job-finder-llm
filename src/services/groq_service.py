from typing import List, Dict, Any
import os
from groq import Groq
from dotenv import load_dotenv
from ..models.job_listing import JobListing
import logging
import traceback
import json

logger = logging.getLogger(__name__)
load_dotenv()

class GroqService:
    def __init__(self):
        """Initialize the Groq client with API key"""
        try:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                raise ValueError("GROQ_API_KEY environment variable not set")
            
            logger.info("Initializing Groq client...")
            self.client = Groq(api_key=api_key)
            self.model = "llama-3.3-70b-versatile"  # Updated to newer model
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Groq client: {str(e)}")
            raise

    async def enhance_job_description(self, description: str) -> Dict[str, str]:
        """
        Enhance job description by extracting key information using Groq API.
        Returns a dictionary with structured information.
        """
        try:
            if not description or description == "Failed to load description":
                logger.warning("Empty or failed description provided to enhance_job_description")
                return {
                    "enhanced_description": description,
                    "status": "error",
                    "error": "Invalid description provided"
                }

            logger.info("Sending description to Groq API for enhancement...")
            prompt = f"""
            Analyze the following job description and extract key information in a structured format.
            Focus on required skills, experience level, job responsibilities, and any unique requirements.

            Job Description:
            {description}

            Please provide the analysis in the following format:
            - Required Skills: (list key technical and soft skills)
            - Experience Level: (entry/mid/senior level and years of experience)
            - Key Responsibilities: (main job duties)
            - Additional Requirements: (any other important requirements)
            """

            chat_completion = await self.client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                model=self.model,
                temperature=0.1,
                max_tokens=1000
            )

            logger.info("Successfully received enhanced description from Groq API")
            return {
                "enhanced_description": chat_completion.choices[0].message.content,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error enhancing job description with Groq: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "enhanced_description": description,
                "status": "error",
                "error": str(e)
            }

    async def generate_job_summary(self, job: JobListing) -> str:
        """Generate a concise summary of a job listing using Groq API."""
        try:
            if not job.description:
                logger.warning("Cannot generate summary - no description provided")
                return "No job description available"

            logger.info(f"Generating summary for job: {job.job_title}")
            
            prompt = (
                "Generate a clear and concise summary of this job posting. "
                "Focus on the most important aspects that a job seeker would want to know.\n\n"
                f"Job Title: {job.job_title}\n"
                f"Company: {job.company}\n"
                f"Location: {job.location}\n"
                f"Job Type: {job.jobNature}\n"
                f"Experience Required: {job.experience}\n"
                f"Salary: {job.salary}\n\n"
                f"Description:\n{job.description[:2000]}...\n\n"  # Limit description length
                "Please provide a summary that includes:\n"
                "1. Key responsibilities (2-3 main points)\n"
                "2. Required skills and qualifications\n"
                "3. Benefits or unique aspects of the role\n"
                "4. Work arrangement (remote/hybrid/onsite)\n\n"
                "Format the summary in clear bullet points."
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional job analyst who creates clear, concise job summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )

            summary = response.choices[0].message.content.strip()
            logger.info("Successfully generated job summary")
            return summary

        except Exception as e:
            logger.error(f"Error generating job summary: {str(e)}")
            return "Failed to generate summary - please check the original job posting"

    async def rank_jobs(self, jobs: List[JobListing], user_preferences: dict) -> List[JobListing]:
        """Rank jobs based on user preferences using Groq's LLM"""
        if not jobs:
            return []
            
        try:
            # Prepare the prompt
            preferences_text = "\n".join([f"{k}: {v}" for k, v in user_preferences.items()])
            job_descriptions = []
            
            for i, job in enumerate(jobs, 1):
                job_text = (
                    f"Job {i}:\n"
                    f"Title: {job.job_title}\n"
                    f"Company: {job.company}\n"
                    f"Location: {job.location}\n"
                    f"Job Nature: {job.jobNature}\n"
                    f"Experience: {job.experience}\n"
                    f"Salary: {job.salary}\n"
                    f"Description: {job.description[:500]}..."  # Truncate description to manage token limit
                )
                job_descriptions.append(job_text)

            prompt = (
                "You are a job matching expert. Please analyze the following jobs and rank them based on the user's preferences.\n\n"
                f"User Preferences:\n{preferences_text}\n\n"
                f"Jobs to analyze:\n{chr(10).join(job_descriptions)}\n\n"
                "Please provide:\n"
                "1. A ranked list of jobs from most relevant to least relevant (just job numbers)\n"
                "2. A brief explanation for each ranking\n\n"
                'Format your response as valid JSON with the following structure:\n'
                '{\n'
                '    "rankings": [1, 2, 3, ...],\n'
                '    "explanations": {\n'
                '        "1": "explanation for job 1",\n'
                '        "2": "explanation for job 2",\n'
                '        "...": "..."\n'
                '    }\n'
                '}'
            )

            # Call Groq API
            logger.info("Sending ranking request to Groq API")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful job matching assistant that provides responses in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more consistent results
                max_tokens=2000
            )
            
            # Parse response
            try:
                result = json.loads(response.choices[0].message.content)
                rankings = result.get("rankings", [])
                
                # Reorder jobs based on rankings
                ranked_jobs = []
                for rank in rankings:
                    if 1 <= rank <= len(jobs):
                        ranked_jobs.append(jobs[rank - 1])
                
                # Add any remaining jobs that weren't ranked
                remaining_jobs = [job for i, job in enumerate(jobs, 1) if i not in rankings]
                ranked_jobs.extend(remaining_jobs)
                
                return ranked_jobs
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Groq response: {str(e)}")
                return jobs
                
        except Exception as e:
            logger.error(f"Error ranking jobs with Groq: {str(e)}")
            return jobs 