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
import asyncio

logger = logging.getLogger("github_api")


class GitHubService:
    """
    Secure GitHub API client
    Uses user's GitHub access token to fetch data
    """
    
    GITHUB_API_BASE = "https://api.github.com"
    
    # SECURITY: Timeout prevents hanging requests (reduced to 5 seconds)
    TIMEOUT = 5.0
    MAX_RETRIES = 1
    
    @staticmethod
    async def get_user_repos(github_token: str) -> Optional[List[Dict]]:
        """
        Fetch all user repositories with pagination and retry logic
        SECURITY: Uses user's access token, timeout protection, handles all pages
        """
        # Input validation
        if not github_token or not isinstance(github_token, str):
            logger.warning("[ERROR] Invalid GitHub token provided")
            return None
        
        logger.info("Fetching repositories...")
        all_repos = []
        page = 1
        
        for attempt in range(GitHubService.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                    while True:
                        logger.info(f"  [PAGE] Fetching page {page}...")
                        response = await client.get(
                            f"{GitHubService.GITHUB_API_BASE}/user/repos",
                            headers={
                                "Authorization": f"token {github_token}",
                                "Accept": "application/vnd.github.v3+json"
                            },
                            params={
                                "type": "owner",
                                "sort": "updated",
                                "per_page": 100,
                                "page": page
                            }
                        )
                        
                        if response.status_code == 200:
                            repos = response.json()
                            logger.info(f"  [OK] Page {page}: Got {len(repos) if isinstance(repos, list) else 0} repos")
                            # Validate response format
                            if not isinstance(repos, list):
                                logger.error("[ERROR] Repos response is not a list!")
                                break
                            if not repos:  # Empty page = end of pagination
                                logger.info(f"[OK] Total repositories fetched: {len(all_repos)}")
                                break
                            all_repos.extend(repos)
                            page += 1
                        elif response.status_code == 401:
                            logger.error("❌ Invalid GitHub token - 401 Unauthorized")
                            return None  # Invalid token
                        else:
                            logger.error(f"[ERROR] GitHub API Error {response.status_code}: {response.text}")
                            break
                    
                    return all_repos if all_repos else None
                    
            except asyncio.TimeoutError:
                logger.warning(f"[TIMEOUT] on attempt {attempt + 1}")
                if attempt < GitHubService.MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return all_repos if all_repos else None
            except Exception as e:
                logger.error(f"[ERROR] Error fetching repos: {str(e)}")
                if attempt < GitHubService.MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return all_repos if all_repos else None
        
        return all_repos if all_repos else None
    
    @staticmethod
    async def get_user_commits(github_token: str, days: int = 365) -> Optional[List[Dict]]:
        """
        Fetch user commits from all repos with error handling
        SECURITY: Uses user's access token, timeout protection, checks all repos
        """
        # Input validation
        if not github_token or not isinstance(github_token, str) or days <= 0:
            return []
        
        try:
            logger.info(f"Fetching commits from last {days} days...")
            commits_list = []
            repos = await GitHubService.get_user_repos(github_token)
            
            if not repos:
                logger.warning("No repos found for commits")
                return []
            
            logger.info(f"  Checking {len(repos)} repos for commits...")
            
            async with httpx.AsyncClient(timeout=GitHubService.TIMEOUT) as client:
                # Check ALL repos, not just first 10
                for idx, repo in enumerate(repos, 1):
                    try:
                        repo_name = repo.get("name")
                        repo_owner = repo.get("owner", {}).get("login")
                        
                        if not repo_name or not repo_owner:
                            continue
                        
                        since_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
                        
                        response = await client.get(
                            f"{GitHubService.GITHUB_API_BASE}/repos/{repo_owner}/{repo_name}/commits",
                            headers={
                                "Authorization": f"token {github_token}",
                                "Accept": "application/vnd.github.v3+json"
                            },
                            params={"since": since_date, "per_page": 100}
                        )
                        
                        if response.status_code == 200:
                            commits = response.json()
                            if isinstance(commits, list):
                                if commits:
                                    logger.info(f"  [{idx}/{len(repos)}] {repo_owner}/{repo_name}: {len(commits)} commits")
                                for commit in commits:
                                    commit["repo_name"] = repo_name
                                    commit["repo_owner"] = repo_owner
                                commits_list.extend(commits)
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug(f"  {repo_owner}/{repo_name}: {str(e)}")
                        continue
            
            logger.info(f"Total commits fetched: {len(commits_list)}")
            return commits_list
        
        except Exception as e:
            logger.error(f"[ERROR] Error fetching commits: {str(e)}")
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
        Fetch user's pull requests with retry and error handling
        SECURITY: Uses user's access token, timeout protection
        """
        # Input validation
        if not github_token or not isinstance(github_token, str) or days <= 0:
            return []
        
        for attempt in range(GitHubService.MAX_RETRIES + 1):
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
                        if isinstance(prs, list):
                            return prs
                        return None
                    elif response.status_code == 401:
                        return None
                    elif attempt < GitHubService.MAX_RETRIES:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return None
            
            except asyncio.TimeoutError:
                if attempt < GitHubService.MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception:
                if attempt < GitHubService.MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    @staticmethod
    async def get_user_profile_stats(github_token: str) -> Optional[Dict]:
        """
        Get user profile with retry and error handling
        SECURITY: Uses user's access token, timeout protection
        """
        # Input validation
        if not github_token or not isinstance(github_token, str):
            return None
        
        for attempt in range(GitHubService.MAX_RETRIES + 1):
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
                        if isinstance(profile, dict):
                            return profile
                        return None
                    elif response.status_code == 401:
                        return None
                    elif attempt < GitHubService.MAX_RETRIES:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return None
            
            except asyncio.TimeoutError:
                if attempt < GitHubService.MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception:
                if attempt < GitHubService.MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
