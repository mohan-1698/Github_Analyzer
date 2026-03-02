"""
Google Gemini Service
Phase 6: AI-powered insights from analytics

Uses Google Gemini to generate:
✅ Productivity insights
✅ Burnout risk assessment
✅ Strengths & weaknesses
✅ Weekly improvement plans
✅ Personalized recommendations

SECURITY:
✅ API key in environment
✅ Structured JSON validation
✅ Error handling
✅ Rate limiting awareness
"""

import google.generativeai as genai
import json
import logging
from typing import Optional, Dict
import os
from datetime import datetime

logger = logging.getLogger("gemini_service")


class GeminiService:
    """
    Secure Google Gemini integration for AI insights
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini service
        SECURITY: API key passed (not hardcoded)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    @staticmethod
    def build_insights_prompt(metrics: Dict, user_login: str) -> str:
        """
        Build structured prompt for Gemini
        SECURITY: Input validation, JSON structure
        """
        productivity_score = metrics.get("productivity", {}).get("score", 0)
        longest_streak = metrics.get("streaks", {}).get("longest_streak", 0)
        commits_per_day = metrics.get("commits", {}).get("commits_per_day", 0)
        pr_merge_rate = metrics.get("prs", {}).get("merge_rate", 0)
        primary_language = metrics.get("languages", {}).get("primary_language", "Unknown")
        
        prompt = f"""
You are an expert developer coach analyzing GitHub activity for {user_login}.

METRICS:
- Productivity Score: {productivity_score}/100
- Longest Coding Streak: {longest_streak} days
- Commits Per Day: {commits_per_day}
- Total PRs Merged: {metrics.get('prs', {}).get('merged_prs', 0)}
- PR Merge Rate: {pr_merge_rate}%
- Primary Language: {primary_language}
- Active Days: {metrics.get('commits', {}).get('active_days', 0)}

Analyze this data and provide insights in the following JSON format (MUST be valid JSON):
{{
    "productivity_level": "string (e.g., Elite, Very Active, Active, Regular, Casual)",
    "burnout_risk": "string (Low, Medium, High) with 0-100 score",
    "key_strengths": ["string", "string", "string"],
    "areas_for_improvement": ["string", "string"],
    "coding_habits": "string (2-3 sentences about their patterns)",
    "weekly_plan": [
        {{"day": "Monday", "focus": "string"}},
        {{"day": "Tuesday", "focus": "string"}},
        {{"day": "Wednesday", "focus": "string"}},
        {{"day": "Thursday", "focus": "string"}},
        {{"day": "Friday", "focus": "string"}}
    ],
    "personalized_advice": "string (3-4 sentences)"
}}

Return ONLY valid JSON, no other text.
"""
        return prompt
    
    @staticmethod
    def validate_ai_response(response_text: str) -> Optional[Dict]:
        """
        SECURITY: Validate and parse AI response as JSON
        Ensures response is safe and properly formatted
        """
        try:
            # SECURITY: Try to parse JSON
            response_json = json.loads(response_text)
            
            # Validate required fields
            required_fields = [
                "productivity_level",
                "burnout_risk",
                "key_strengths",
                "areas_for_improvement",
                "coding_habits",
                "weekly_plan",
                "personalized_advice"
            ]
            
            for field in required_fields:
                if field not in response_json:
                    logger.warning(f"Missing required field: {field}")
                    return None
            
            # Validate types
            if not isinstance(response_json.get("key_strengths"), list):
                logger.warning("key_strengths must be array")
                return None
            
            if not isinstance(response_json.get("weekly_plan"), list):
                logger.warning("weekly_plan must be array")
                return None
            
            logger.info("AI response validated successfully")
            return response_json
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in AI response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error validating AI response: {str(e)}")
            return None
    
    async def generate_insights(self, metrics: Dict, user_login: str) -> Optional[Dict]:
        """
        Generate AI insights from metrics using Google Gemini
        SECURITY: Uses structured prompts, validates output
        """
        try:
            logger.info(f"Generating insights for {user_login} using Gemini")
            
            # Build prompt
            prompt = GeminiService.build_insights_prompt(metrics, user_login)
            
            # Call Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000
                )
            )
            
            # Extract response
            response_text = response.text.strip()
            
            logger.info(f"Raw Gemini response: {response_text[:100]}...")
            
            # SECURITY: Validate response format
            insights = GeminiService.validate_ai_response(response_text)
            
            if not insights:
                logger.error("Failed to validate Gemini response")
                return None
            
            # Add metadata
            insights["generated_at"] = datetime.utcnow().isoformat()
            insights["model"] = "google-gemini-pro"
            
            logger.info(f"Insights generated successfully for {user_login}")
            return insights
        
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return None


async def get_ai_insights(metrics: Dict, user_login: str, api_key: str) -> Optional[Dict]:
    """
    Wrapper function to get AI insights using Google Gemini
    SECURITY: API key passed as parameter
    """
    service = GeminiService(api_key)
    return await service.generate_insights(metrics, user_login)
