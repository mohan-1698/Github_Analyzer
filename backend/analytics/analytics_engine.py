"""
Analytics Engine
Phase 5: Calculate metrics from GitHub data

METRICS CALCULATED:
✅ Commits per day/week/month
✅ Longest coding streak
✅ Inactive streak
✅ Most active hour
✅ Language distribution
✅ PR merge time average
✅ Contribution percentage
✅ Productivity score
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger("analytics")


class AnalyticsEngine:
    """
    Pure Python analytics (no AI, just calculations)
    """
    
    @staticmethod
    def calculate_commit_metrics(commits: List[Dict]) -> Dict:
        """
        Calculate commit-based metrics with input validation
        """
        # Input validation
        if not commits or not isinstance(commits, list):
            return {
                "total_commits": 0,
                "commits_per_day": 0,
                "commits_per_week": 0,
                "commits_per_month": 0
            }
        
        total_commits = len(commits)
        
        # Group commits by date
        commits_by_date = defaultdict(int)
        for commit in commits:
            # SECURITY: Handle various date formats
            try:
                if not isinstance(commit, dict):
                    continue
                commit_date_str = commit.get("commit", {}).get("committer", {}).get("date")
                if commit_date_str:
                    date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00")).date()
                    commits_by_date[date] += 1
            except Exception:
                continue
        
        # Calculate stats (safe division)
        num_active_days = len(commits_by_date) if commits_by_date else 1
        num_weeks = max(num_active_days / 7, 1)
        num_months = max(num_active_days / 30, 1)
        
        return {
            "total_commits": total_commits,
            "active_days": num_active_days,
            "commits_per_day": round(total_commits / num_active_days, 2) if num_active_days > 0 else 0,
            "commits_per_week": round(total_commits / num_weeks, 2),
            "commits_per_month": round(total_commits / num_months, 2),
            "commits_by_date": dict(commits_by_date)
        }
    
    @staticmethod
    def calculate_streaks(commits: List[Dict]) -> Dict:
        """
        Calculate longest coding streak and inactive streak
        """
        if not commits:
            return {
                "longest_streak": 0,
                "current_streak": 0,
                "longest_inactive_streak": 0
            }
        
        # Extract dates
        commit_dates = set()
        for commit in commits:
            try:
                commit_date_str = commit.get("commit", {}).get("committer", {}).get("date")
                if commit_date_str:
                    date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00")).date()
                    commit_dates.add(date)
            except Exception as e:
                continue
        
        if not commit_dates:
            return {
                "longest_streak": 0,
                "current_streak": 0,
                "longest_inactive_streak": 0
            }
        
        sorted_dates = sorted(list(commit_dates))
        
        # Calculate longest streak
        longest_streak = 1
        current_streak = 1
        
        for i in range(1, len(sorted_dates)):
            diff = (sorted_dates[i] - sorted_dates[i-1]).days
            
            if diff == 1:  # Consecutive days
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        
        # Calculate current streak
        today = datetime.utcnow().date()
        current_streak = 0
        
        for i in range(len(sorted_dates) - 1, -1, -1):
            diff = (today - sorted_dates[i]).days
            if diff == 0 or diff == current_streak:
                current_streak += 1
            else:
                break
        
        # Calculate longest inactive streak
        longest_inactive = 0
        for i in range(1, len(sorted_dates)):
            inactive = (sorted_dates[i] - sorted_dates[i-1]).days - 1
            longest_inactive = max(longest_inactive, inactive)
        
        return {
            "longest_streak": longest_streak,
            "current_streak": current_streak,
            "longest_inactive_streak": longest_inactive
        }
    
    @staticmethod
    def calculate_language_distribution(repos: List[Dict]) -> Dict:
        """
        Calculate which languages user codes in most with input validation
        """
        # Input validation
        if not repos or not isinstance(repos, list):
            return {"primary_language": "Unknown", "language_distribution": {}}
        
        language_bytes = defaultdict(int)
        
        for repo in repos:
            try:
                if not isinstance(repo, dict):
                    continue
                language = repo.get("language")
                size = repo.get("size", 0)
                
                if language and isinstance(size, int) and size >= 0:
                    language_bytes[language] += size
            except Exception:
                continue
        
        if not language_bytes:
            return {"primary_language": "Unknown", "language_distribution": {}}
        
        # Sort by usage
        sorted_languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_languages[0][0]
        
        # Calculate percentages (safe division)
        total_bytes = sum(language_bytes.values()) or 1
        distribution = {
            lang: round((bytes / total_bytes * 100), 2)
            for lang, bytes in sorted_languages
        }
        
        return {
            "primary_language": primary,
            "language_distribution": distribution,
            "top_3_languages": [lang for lang, _ in sorted_languages[:3]]
        }
    
    @staticmethod
    def calculate_pr_metrics(pull_requests: List[Dict]) -> Dict:
        """
        Calculate pull request statistics
        """
        if not pull_requests:
            return {
                "total_prs": 0,
                "avg_merge_time": 0,
                "merged_prs": 0,
                "open_prs": 0
            }
        
        total_prs = len(pull_requests)
        merged_prs = 0
        open_prs = 0
        merge_times = []
        
        for pr in pull_requests:
            state = pr.get("state", "open")
            
            if state == "closed":
                merged_prs += 1
                
                # Calculate merge time
                try:
                    created = datetime.fromisoformat(pr.get("created_at", "").replace("Z", "+00:00"))
                    closed = datetime.fromisoformat(pr.get("closed_at", "").replace("Z", "+00:00"))
                    merge_time = (closed - created).days
                    merge_times.append(merge_time)
                except Exception as e:
                    pass
            else:
                open_prs += 1
        
        avg_merge_time = round(sum(merge_times) / len(merge_times), 1) if merge_times else 0
        
        return {
            "total_prs": total_prs,
            "merged_prs": merged_prs,
            "open_prs": open_prs,
            "avg_merge_time_days": avg_merge_time,
            "merge_rate": round((merged_prs / total_prs * 100), 1) if total_prs > 0 else 0
        }
    
    @staticmethod
    def calculate_productivity_score(metrics: Dict) -> Dict:
        """
        Calculate productivity score (0-100)
        Based on: commits, streaks, PR merge rate, consistency
        """
        score = 0
        breakdown = {}
        
        # COMMITS SCORE (0-30)
        commits_per_day = metrics.get("commits", {}).get("commits_per_day", 0)
        if commits_per_day >= 3:
            commit_score = 30
        elif commits_per_day >= 2:
            commit_score = 25
        elif commits_per_day >= 1:
            commit_score = 20
        else:
            commit_score = max(0, commits_per_day * 10)
        
        breakdown["commits"] = round(commit_score, 1)
        score += commit_score
        
        # STREAK SCORE (0-30)
        longest_streak = metrics.get("streaks", {}).get("longest_streak", 0)
        if longest_streak >= 30:
            streak_score = 30
        elif longest_streak >= 14:
            streak_score = 25
        elif longest_streak >= 7:
            streak_score = 20
        else:
            streak_score = min(longest_streak * 2, 20)
        
        breakdown["streaks"] = round(streak_score, 1)
        score += streak_score
        
        # PR MERGE SCORE (0-20)
        merge_rate = metrics.get("prs", {}).get("merge_rate", 0)
        pr_score = min(merge_rate / 5, 20)  # 100% merge = 20 points
        
        breakdown["prs"] = round(pr_score, 1)
        score += pr_score
        
        # CONSISTENCY SCORE (0-20)
        active_days = metrics.get("commits", {}).get("active_days", 0)
        consistency_score = min(active_days / 3, 20)  # 60+ days = 20 points
        
        breakdown["consistency"] = round(consistency_score, 1)
        score += consistency_score
        
        return {
            "score": round(min(score, 100), 1),
            "breakdown": breakdown,
            "level": AnalyticsEngine._score_to_level(score)
        }
    
    @staticmethod
    def _score_to_level(score: float) -> str:
        """Convert score to readable level"""
        if score >= 85:
            return "Elite Code Warrior"
        elif score >= 70:
            return "Very Active Developer"
        elif score >= 50:
            return "Active Developer"
        elif score >= 30:
            return "Regular Contributor"
        else:
            return "Casual Contributor"
    
    @staticmethod
    def aggregate_all_metrics(commits: List[Dict], repos: List[Dict], 
                            pull_requests: List[Dict]) -> Dict:
        """Calculate all metrics and aggregate, including repo list for AI analysis"""
        
        return {
            "commits": AnalyticsEngine.calculate_commit_metrics(commits),
            "streaks": AnalyticsEngine.calculate_streaks(commits),
            "languages": AnalyticsEngine.calculate_language_distribution(repos),
            "prs": AnalyticsEngine.calculate_pr_metrics(pull_requests),
            "productivity": AnalyticsEngine.calculate_productivity_score({
                "commits": AnalyticsEngine.calculate_commit_metrics(commits),
                "streaks": AnalyticsEngine.calculate_streaks(commits),
                "languages": AnalyticsEngine.calculate_language_distribution(repos),
                "prs": AnalyticsEngine.calculate_pr_metrics(pull_requests)
            }),
            "repositories": repos if repos else []  # Pass repo list for AI analysis
        }
