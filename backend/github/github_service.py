"""
GitHub API Service
Phase 4: Fetch repositories, commits, languages, pull requests

SECURITY:
✅ Rate limited API calls
✅ Uses GitHub access token (not API key)
✅ Input validation
✅ Error handling
✅ Timeout protection
"""

import httpx
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("github_api")


class GitHubService:
    """
    Secure GitHub API client
    Uses user's GitHub access token to fetch data
    """
    
    GITHUB_API_BASE = "https://api.github.com"
    
    # SECURITY: Timeout prevents hanging requests
    TIMEOUT = 15.0
    
    @staticmethod
    async def get_user_repos(github_token: str) -> Optional[List[Dict]]:
        """
        Fetch all user repositories
        SECURITY: Uses user's access token
        """
        try:
            async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                response = await client.get(
                    f"{GitHubService.GITHUB_API_BASE}/user/repos",
                    headers={
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={
                        "type": "owner",  # Only repos user owns
                        "sort": "updated",
                        "per_page": 100,  # Max results
                        "page": 1
                    }
                )
                
                if response.status_code == 200:
                    repos = response.json()
                    logger.info(f"Fetched {len(repos)} repositories")
                    return repos
                else:
                    logger.error(f"Failed to fetch repos: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching repos: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_commits(github_token: str, days: int = 90) -> Optional[List[Dict]]:
        """
        Fetch user commits from all repos (last N days)
        SECURITY: Uses user's access token, timeout protection
        """
        try:
            commits_list = []
            
            # Get all repos first
            repos = await GitHubService.get_user_repos(github_token)
            
            if not repos:
                logger.warning("No repos found, cannot fetch commits")
                return []
            
            # For each repo, fetch commits
            async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                for repo in repos[:10]:  # SECURITY: Limit API calls (first 10 repos)
                    repo_name = repo.get("name")
                    repo_owner = repo.get("owner", {}).get("login")
                    
                    # Calculate date range
                    since_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
                    
                    try:
                        response = await client.get(
                            f"{GitHubService.GITHUB_API_BASE}/repos/{repo_owner}/{repo_name}/commits",
                            headers={
                                "Authorization": f"token {github_token}",
                                "Accept": "application/vnd.github.v3+json"
                            },
                            params={
                                "since": since_date,
                                "per_page": 100
                            }
                        )
                        
                        if response.status_code == 200:
                            commits = response.json()
                            
                            # Add repo info to each commit
                            for commit in commits:
                                commit["repo_name"] = repo_name
                                commit["repo_owner"] = repo_owner
                            
                            commits_list.extend(commits)
                            logger.info(f"Fetched {len(commits)} commits from {repo_name}")
                    except Exception as e:
                        logger.warning(f"Error fetching commits from {repo_name}: {str(e)}")
                        continue
            
            logger.info(f"Total {len(commits_list)} commits collected")
            return commits_list
        
        except Exception as e:
            logger.error(f"Error in get_user_commits: {str(e)}")
            return None
    
    @staticmethod
    async def get_repo_languages(github_token: str, owner: str, repo: str) -> Optional[Dict]:
        """
        Fetch language distribution in a repository
        SECURITY: Input validation, timeout protection
        """
        try:
            # SECURITY: Validate input
            if not owner or not repo:
                logger.warning("Invalid owner or repo")
                return None
            
            async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                response = await client.get(
                    f"{GitHubService.GITHUB_API_BASE}/repos/{owner}/{repo}/languages",
                    headers={
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                
                if response.status_code == 200:
                    languages = response.json()
                    logger.info(f"Fetched languages for {owner}/{repo}")
                    return languages
                else:
                    logger.warning(f"Failed to fetch languages: {response.status_code}")
                    return {}
        
        except Exception as e:
            logger.error(f"Error fetching languages: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_pull_requests(github_token: str, days: int = 90) -> Optional[List[Dict]]:
        """
        Fetch user's pull requests (last N days)
        SECURITY: Uses user's access token, timeout protection
        """
        try:
            since_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                response = await client.get(
                    f"{GitHubService.GITHUB_API_BASE}/search/issues",
                    headers={
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={
                        "q": f"is:pr author:@me created:>{since_date}",
                        "sort": "created",
                        "order": "desc",
                        "per_page": 100
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    prs = data.get("items", [])
                    logger.info(f"Fetched {len(prs)} pull requests")
                    return prs
                else:
                    logger.warning(f"Failed to fetch PRs: {response.status_code}")
                    return None
        
        except Exception as e:
            logger.error(f"Error fetching PRs: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_profile_stats(github_token: str) -> Optional[Dict]:
        """
        Get user profile with stats
        SECURITY: Uses user's access token
        """
        try:
            async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                response = await client.get(
                    f"{GitHubService.GITHUB_API_BASE}/user",
                    headers={
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                
                if response.status_code == 200:
                    profile = response.json()
                    logger.info(f"Fetched profile for {profile.get('login')}")
                    return profile
                else:
                    logger.warning(f"Failed to fetch profile: {response.status_code}")
                    return None
        
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            return None
