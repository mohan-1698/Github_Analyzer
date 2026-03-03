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

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

import google.generativeai as genai
import json
import logging
from typing import Optional, Dict
import os
from datetime import datetime
import asyncio
import hashlib

logger = logging.getLogger("gemini_service")

# Gemini timeout (AI takes longer than regular API calls)
GEMINI_TIMEOUT = 10.0
MAX_RETRIES = 1


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
        self.model = genai.GenerativeModel('gemini-3-flash-preview')
    
    @staticmethod
    def build_insights_prompt(metrics: Dict, user_login: str) -> str:
        """Build optimized Gemini prompt with all requirements"""
        
        # Extract key metrics
        repos = metrics.get("repositories", [])
        commits_data = metrics.get("commits", {})
        total_commits = commits_data.get("total_commits", 0)
        commits_per_day = commits_data.get("commits_per_day", 0)
        commits_this_week = commits_data.get("commits_this_week", 0)
        longest_streak = metrics.get("streaks", {}).get("longest_streak", 0)
        merged_prs = metrics.get("prs", {}).get("merged_prs", 0)
        productivity_score = metrics.get("productivity", {}).get("score", 0)
        languages = metrics.get("languages", {})
        
        # Top repos by stars
        top_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:8]
        repo_summary = "\n".join([
            f"- {r['name']}: ⭐{r.get('stargazers_count', 0)}, {r.get('language', 'Unknown')}"
            for r in top_repos
        ])
        
        # Languages distribution
        lang_summary = ", ".join([f"{k}: {v}%" for k, v in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]]) if languages else "N/A"
        
        prompt = f"""Analyze GitHub developer profile: {user_login}

PROFILE METRICS:
- Repositories: {len(repos)}
- Total Commits (365d): {total_commits}
- Commits/Day: {commits_per_day:.1f}
- Productivity Score: {productivity_score}%
- Merged PRs: {merged_prs}
- Longest Streak: {longest_streak}d
- Languages: {lang_summary}

TOP REPOSITORIES:
{repo_summary}

COMMIT ANALYSIS:
- Average commits/month: {total_commits / 12:.1f}
- Commits this week: {commits_this_week}
- Contribution consistency: {"Excellent" if commits_per_day > 1 else "Good" if commits_per_day > 0.5 else "Moderate"}

GENERATE JSON WITH EXACTLY THESE 12 FIELDS (NO ADDITIONAL FIELDS):

{{
    "developer_level": "Beginner/Junior/Mid-level/Senior/Expert. Based: repo count ({len(repos)}), commit frequency ({commits_per_day:.1f}/day), streak ({longest_streak}d), language mastery, project complexity",
    
    "primary_domains": ["List 2-3 main specializations with % breakdown based on: language mix ({lan_summary}), project types, repository diversity"],
    
    "top_repositories_used": ["List 5-8 most important repos with: name, role (architect/owner/core-contributor), key tech, impact on profile"],
    
    "activity_analysis": {{
        "commit_pattern": "Frequency description based on {commits_per_day:.1f}/day and {longest_streak}d streak",
        "most_active_repo": "Name and reasoning from top repos",
        "frequency_score": "0-100 based on {total_commits} total commits and {commits_this_week} this week",
        "consistency_insight": "Daily/weekly/monthly developer or sprint-based?"
    }},
    
    "core_strengths": ["List 5-7 technical strengths from: language expertise, project diversity, code patterns, domains covered"],
    
    "areas_to_improve": ["List 4-5 gaps from: missing languages, untried project types, collaboration patterns, testing practices"],
    
    "coding_discipline_explained": "Code organization assessment: branch discipline, commit message quality, refactoring patterns, documentation. Rate (excellent/good/moderate/needs-work)",
    
    "focus_style_explained": "Developer archetype: Specialist (deep in 1-2 domains) / Generalist (broad skills) / Full-stack / DevOps-focused / Data-focused. Explain concentration",
    
    "growth_opportunities": ["List 5-6 specific opportunities: new tech stacks, frameworks, domains, OSS areas, leadership paths"],
    
    "burnout_risk_assessment": {{
        "risk_level": "Low/Moderate/High based on: {commits_per_day:.1f}/day frequency, {longest_streak}d consistency, inactive periods",
        "indicators": ["Specific patterns: regular/sporadic/declining/intense"],
        "recommendations": ["3-4 sustainable practices"]
    }},
    
    "learning_roadmap": ["5-8 learning goals ranked by priority: technologies, methodologies, frameworks, domains, roles. Include 3/6/12 month timeline"],
    
    "comprehensive_assessment": "2-3 paragraph summary: overall profile strength, unique value proposition, market positioning, 1-2 year trajectory, key differentiators, honest assessment"
}}

CRITICAL:
- Return VALID JSON ONLY - no markdown/code blocks
- ALL 12 fields MUST be present
- Strings are descriptive (50-200 words)
- Data-driven: reference actual metrics
- Honest, constructive, personalized"""
        
        return prompt
    
    @staticmethod
    def get_analytics_hash(metrics: Dict) -> str:
        """
        Create simple hash of key analytics to detect if data changed
        Used for caching - only regenerate insights if hash differs
        """
        hash_data = {
            "commits": metrics.get("commits", {}).get("total_commits"),
            "streak": metrics.get("streaks", {}).get("longest_streak"),
            "prs": metrics.get("prs", {}).get("merged_prs"),
            "repos": len(metrics.get("repositories", []))
        }
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    @staticmethod
    def validate_ai_response(response_text: str) -> Optional[Dict]:
        """
        SECURITY: Validate and parse AI response as JSON with expanded fields
        Lenient validation - accepts partial responses, logs everything
        """
        try:
            # Log the raw response for debugging - show full response
            logger.info(f"Raw Gemini response ({len(response_text)} chars):")
            logger.info(response_text)  # Log FULL response
            
            # SECURITY: Try to parse JSON
            response_json = json.loads(response_text)
            
            logger.info(f"Successfully parsed JSON with {len(response_json)} fields: {list(response_json.keys())}")
            
            # Accept any response that has at least some fields
            if not response_json or not isinstance(response_json, dict):
                logger.warning("Response is not a valid dict")
                return None
            
            # Validate array fields contain strings (if present)
            array_fields = [
                "primary_domains",
                "core_strengths", 
                "technical_weaknesses",
                "recommended_growth_areas",
                "career_next_steps"
            ]
            
            for field in array_fields:
                if field in response_json:
                    if not isinstance(response_json.get(field), list):
                        logger.warning(f"{field} not a list, converting")
                        response_json[field] = []
                    else:
                        # Filter to keep only strings
                        response_json[field] = [
                            str(item) for item in response_json[field] 
                            if isinstance(item, (str, dict))
                        ]
                        logger.info(f"{field}: {len(response_json[field])} items")
            
            # Validate personalized_development_plan structure (if present)
            if "personalized_development_plan" in response_json:
                plan = response_json.get("personalized_development_plan", [])
                if isinstance(plan, list):
                    fixed_plan = []
                    for item in plan:
                        if isinstance(item, dict) and "month" in item and "focus" in item:
                            fixed_plan.append(item)
                    response_json["personalized_development_plan"] = fixed_plan
                    logger.info(f"Development plan: {len(fixed_plan)} months")
                else:
                    response_json["personalized_development_plan"] = []
            
            logger.info("AI response validated successfully")
            logger.info(f"Final response has {len(response_json)} fields")
            return response_json
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Response text: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error validating AI response: {str(e)}")
            logger.error(f"Response text: {response_text}")
            return None
    
    async def generate_insights(self, metrics: Dict, user_login: str, cached_insights: Optional[Dict] = None, previous_hash: Optional[str] = None) -> Optional[Dict]:
        """
        Generate AI insights from metrics with timeout and retry
        SMART CACHING: Reuse cached insights if data hash matches
        SECURITY: Uses structured prompts, validates output, timeout protection
        """
        # Input validation
        if not isinstance(metrics, dict) or not user_login:
            logger.error("Invalid metrics or user_login")
            return None
        
        # Check if data changed
        current_hash = self.get_analytics_hash(metrics)
        if cached_insights and previous_hash and current_hash == previous_hash:
            logger.info(f"Analytics unchanged (hash: {current_hash}). Returning cached insights.")
            return cached_insights
        
        logger.info(f"Generating insights for user: {user_login} (hash: {current_hash})")
        
        # Build prompt
        prompt = GeminiService.build_insights_prompt(metrics, user_login)
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Calling Gemini API (attempt {attempt + 1})...")
                
                # Call Gemini with timeout
                response_text = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._call_gemini,
                        prompt
                    ),
                    timeout=GEMINI_TIMEOUT
                )
                
                logger.info(f"Gemini response received: {len(response_text)} chars")
                
                # SECURITY: Validate response format
                insights = GeminiService.validate_ai_response(response_text)
                
                if insights:
                    insights["generated_at"] = datetime.utcnow().isoformat()
                    insights["model"] = "google-gemini-pro"
                    insights["analytics_hash"] = current_hash  # Store hash for next time
                    logger.info(f"Insights generated successfully for {user_login}")
                    return insights
                elif attempt < MAX_RETRIES:
                    logger.warning(f"Invalid insights response, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(f"Invalid insights response after {attempt + 1} attempts")
                    return None
            
            except asyncio.TimeoutError:
                logger.error(f"Gemini API timeout on attempt {attempt + 1}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception as e:
                logger.error(f"Error calling Gemini: {str(e)}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    def _call_gemini(self, prompt: str) -> str:
        """Helper method to call Gemini (blocks, so wrapped in asyncio.to_thread)"""
        try:
            logger.info("Sending request to Gemini API...")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7
                    # No token limit - let Gemini return full response
                )
            )
            logger.info(f"Gemini API returned: {len(response.text)} chars, first 200: {response.text[:200]}...")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise


async def get_ai_insights(metrics: Dict, user_login: str, api_key: str, cached_insights: Optional[Dict] = None, previous_hash: Optional[str] = None) -> Optional[Dict]:
    """
    Wrapper function to get AI insights using Google Gemini with caching support
    
    Args:
        metrics: Analytics data
        user_login: GitHub username
        api_key: Gemini API key
        cached_insights: Previously cached insights (optional)
        previous_hash: Hash of previous analytics (optional)
    
    Returns:
        Insights dict with analytics_hash field for next cache check
    """
    service = GeminiService(api_key)
    return await service.generate_insights(metrics, user_login, cached_insights, previous_hash)
