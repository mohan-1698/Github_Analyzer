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
GEMINI_TIMEOUT = 60.0
MAX_RETRIES = 2


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
        
        # Type safety: ensure repos is a list of dicts
        if not isinstance(repos, list):
            repos = []
        else:
            # Filter to keep only dict items (remove non-dict entries)
            repos = [r for r in repos if isinstance(r, dict)]
        
        commits_data = metrics.get("commits", {})
        total_commits = commits_data.get("total_commits", 0)
        commits_per_day = commits_data.get("commits_per_day", 0)
        commits_this_week = commits_data.get("commits_this_week", 0)
        longest_streak = metrics.get("streaks", {}).get("longest_streak", 0)
        merged_prs = metrics.get("prs", {}).get("merged_prs", 0)
        productivity_score = metrics.get("productivity", {}).get("score", 0)
        languages = metrics.get("languages", {})
        # Get the language distribution dict (percentages)
        lang_distribution = languages.get("language_distribution", {}) if isinstance(languages, dict) else {}
        primary_language = languages.get("primary_language", "Unknown") if isinstance(languages, dict) else "Unknown"
        
        # Top repos by stars - with safe sorting
        try:
            top_repos = sorted(
                [r for r in repos if isinstance(r, dict)],
                key=lambda x: int(x.get("stargazers_count", 0)) if isinstance(x.get("stargazers_count"), (int, float)) else 0,
                reverse=True
            )[:8]
        except Exception as sort_error:
            top_repos = []
        
        repo_summary = "\n".join([
            f"- {r.get('name', 'Unknown')}: ⭐{r.get('stargazers_count', 0)}, {r.get('language', 'Unknown')}"
            for r in top_repos
        ])
        
        # Languages distribution - use the extracted distribution dict
        try:
            lang_items = list(lang_distribution.items())
            lang_summary = ", ".join([f"{k}: {v}%" for k, v in sorted(lang_items, key=lambda x: x[1], reverse=True)[:5]]) if lang_items else "N/A"
        except Exception as e:
            lang_summary = "N/A"
        
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

GENERATE JSON WITH EXACTLY THESE FIELDS (MATCH STRUCTURE EXACTLY):

{{
    "developer_level": "Beginner/Junior/Mid-level/Senior/Expert",
    
    "primary_domains": ["Web Development - 60%", "Data Science - 30%", "DevOps - 10%"],
    
    "top_repositories_used": ["repo1: Main project with React, TypeScript", "repo2: Backend API with Python", "repo3: ML experiments"],
    
    "activity_analysis": {{
        "efficiency_rating": "High/Medium/Low - brief explanation",
        "consistency": "Daily coder/Weekly sprinter/Monthly bursts",
        "weekly_output": "~X commits per week on average",
        "pattern": "Regular contributor/Sprint-based/Variable"
    }},
    
    "core_strengths": ["Strong JavaScript/TypeScript skills", "Full-stack development experience", "Good commit discipline"],
    
    "areas_to_improve": {{
        "technical_gaps": ["Need more testing coverage", "Could improve TypeScript usage"],
        "activity_concerns": ["Long inactive periods between sprints"],
        "domain_specific": ["Consider exploring cloud infrastructure", "Add more documentation"]
    }},
    
    "coding_discipline_explained": {{
        "rating": "Excellent/Good/Moderate/Needs Work",
        "meaning": "What this means for code quality",
        "evidence": "Based on commit patterns and repo structure",
        "why_matters": "Impact on team collaboration",
        "improvement": "Specific tip to improve"
    }},
    
    "focus_style_explained": {{
        "style": "Specialist/Generalist/Full-stack/DevOps-focused",
        "meaning": "What this style indicates",
        "evidence": "Based on repo diversity and languages",
        "career_implications": "Career path suggestions",
        "recommendation": "How to leverage this style"
    }},
    
    "growth_opportunities": {{
        "next_skills": ["TypeScript advanced patterns", "GraphQL", "Kubernetes"],
        "project_ideas": ["Build a real-time app", "Contribute to OSS", "Create a CLI tool"]
    }},
    
    "burnout_risk_assessment": {{
        "risk_level": "Low/Medium/High",
        "explanation": "Based on commit frequency and patterns",
        "if_low": "Your pace is sustainable",
        "if_medium": "Monitor your workload",
        "if_high": "Consider taking breaks",
        "recommendation": "Specific advice for sustainability"
    }},
    
    "learning_roadmap": {{
        "current_domain": "Primary specialization area",
        "domain_mastery_level": "Beginner/Intermediate/Advanced/Expert",
        "phase_1_months_1_2": {{
            "domain": "Focus area",
            "goal": "Specific measurable goal",
            "why": "Reason for this focus"
        }},
        "phase_2_months_3_4": {{
            "domain": "Complementary area",
            "goal": "Specific measurable goal",
            "why": "Reason for this focus"
        }},
        "phase_3_months_5_6": {{
            "domain": "Stretch goal area",
            "goal": "Specific measurable goal",
            "why": "Reason for this focus"
        }},
        "implementation": ["Weekly learning hours", "Resources to use", "Practice projects"]
    }},
    
    "comprehensive_assessment": "2-3 paragraph personalized summary covering: current level assessment, unique strengths, growth trajectory, market positioning, and honest constructive feedback. Reference actual metrics like {total_commits} commits, {len(repos)} repos, {longest_streak}d streak."
}}

CRITICAL:
- Return VALID JSON ONLY - no markdown/code blocks/backticks
- Match the EXACT field names and nesting structure above
- Be personalized and data-driven using the actual metrics provided
- Be honest and constructive"""
        
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
        """SECURITY: Validate and parse AI response as JSON"""
        try:
            # Strip markdown code blocks if present
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            response_json = json.loads(clean_text)
            
            # Accept any response that has fields
            if not response_json or not isinstance(response_json, dict):
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
                        response_json[field] = []
                    else:
                        # Filter to keep only strings
                        response_json[field] = [
                            str(item) for item in response_json[field] 
                            if isinstance(item, (str, dict))
                        ]
            
            # Validate personalized_development_plan structure (if present)
            if "personalized_development_plan" in response_json:
                plan = response_json.get("personalized_development_plan", [])
                if isinstance(plan, list):
                    fixed_plan = []
                    for item in plan:
                        if isinstance(item, dict) and "month" in item and "focus" in item:
                            fixed_plan.append(item)
                    response_json["personalized_development_plan"] = fixed_plan
                else:
                    response_json["personalized_development_plan"] = []
            
            return response_json
        
        except json.JSONDecodeError as e:
            return None
        except Exception as e:
            return None
    
    async def generate_insights(self, metrics: Dict, user_login: str, cached_insights: Optional[Dict] = None, previous_hash: Optional[str] = None) -> Optional[Dict]:
        """Generate AI insights from metrics with timeout and retry"""
        # Input validation
        if not isinstance(metrics, dict) or not user_login:
            return None
        
        # Check if data changed
        current_hash = self.get_analytics_hash(metrics)
        if cached_insights and previous_hash and current_hash == previous_hash:
            return cached_insights
        
        # Build prompt
        prompt = GeminiService.build_insights_prompt(metrics, user_login)
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Call Gemini with timeout
                response_text = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._call_gemini,
                        prompt
                    ),
                    timeout=GEMINI_TIMEOUT
                )
                
                # SECURITY: Validate response format
                insights = GeminiService.validate_ai_response(response_text)
                
                if insights:
                    insights["generated_at"] = datetime.utcnow().isoformat()
                    insights["model"] = "google-gemini-pro"
                    insights["analytics_hash"] = current_hash
                    return insights
                elif attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                else:
                    return None
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception as e:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    def _call_gemini(self, prompt: str) -> str:
        """Helper method to call Gemini (blocks, so wrapped in asyncio.to_thread)"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7
                    # No token limit - let Gemini return full response
                )
            )
            return response.text.strip()
        except Exception as e:
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
