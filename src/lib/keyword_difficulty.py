"""iTunes keyword difficulty algorithm implementation."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union
from math import sqrt
from lib.aso_store import get_aso_store, ASONamespaces


@dataclass
class TitleMatchResult:
    exact: int
    broad: int
    partial: int
    none: int
    score: float


@dataclass
class KeywordDifficultyResult:
    keyword: str
    title_matches: TitleMatchResult
    competitors: int
    competitors_score: float
    installs_score: float
    rating_score: float
    age_score: float
    score: float


def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """Extract keywords from text using NLP-based approach."""
    if not text:
        return []
    
    # Clean text by removing contractions
    text = re.sub(r"'t\b|'s\b|'ll\b|'re\b|'ve\b", "", text.lower())
    
    # Extract words (alphanumeric only)
    words = re.findall(r'\b[a-zA-Z0-9]+\b', text)
    
    # Filter out single character words
    words = [w for w in words if len(w) > 1]
    
    # Extract phrases (up to 3 words)
    phrases = []
    for i in range(len(words)):
        for j in range(i + 1, min(i + 4, len(words) + 1)):
            phrase = " ".join(words[i:j])
            if len(phrase.split()) <= 3:
                phrases.append(phrase)
    
    # Combine words and phrases
    keywords = words + phrases
    
    # Count frequency
    keyword_counts = {}
    for keyword in keywords:
        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
    
    # Score keywords (phrases get 2.5x multiplier)
    scored_keywords = []
    for keyword, count in keyword_counts.items():
        score = count
        if " " in keyword:
            score *= 2.5
        scored_keywords.append((keyword, score))
    
    # Sort by score and return top keywords
    scored_keywords.sort(key=lambda x: x[1], reverse=True)
    return [kw[0] for kw, _ in scored_keywords[:max_keywords]]


def get_title_matches(keyword: str, apps: List[Dict]) -> TitleMatchResult:
    """Analyze title matches for keyword in top apps."""
    keyword_lower = keyword.lower()
    keyword_words = set(keyword_lower.split())
    
    exact = 0
    broad = 0
    partial = 0
    none = 0
    
    for app in apps:
        title = app.get("title", "").lower()
        
        # Check for exact match
        if keyword_lower in title:
            exact += 1
        else:
            # Check for broad match (all words present)
            title_words = set(re.findall(r'\b\w+\b', title))
            if keyword_words.issubset(title_words):
                broad += 1
            elif keyword_words & title_words:
                # Partial match (some words present)
                partial += 1
            else:
                none += 1
    
    total_apps = len(apps)
    if total_apps == 0:
        score = 0.0
    else:
        score = (10 * exact + 5 * broad + 2.5 * partial) / total_apps
    
    return TitleMatchResult(
        exact=exact,
        broad=broad,
        partial=partial,
        none=none,
        score=score
    )


def get_competitors(keyword: str, apps: List[Dict]) -> int:
    """Count apps that target the keyword in their content."""
    keyword_lower = keyword.lower()
    competitors = 0
    
    for app in apps:
        # Extract top keywords from app title and description
        title = app.get("title", "")
        description = app.get("description", "")
        text = f"{title} {description}"
        
        app_keywords = extract_keywords(text, max_keywords=10)
        
        # Check if target keyword appears in top 10 keywords
        if keyword_lower in [kw.lower() for kw in app_keywords]:
            competitors += 1
    
    return competitors


def z_score_normalize(value: float, max_value: float, min_score: float = 1.0, max_score: float = 10.0) -> float:
    """Map 0 to max_value range to min_score-max_score scale."""
    if max_value == 0:
        return min_score
    
    normalized = min(value / max_value, 1.0)
    return min_score + normalized * (max_score - min_score)


def inverted_z_score_normalize(value: float, max_value: float, min_score: float = 1.0, max_score: float = 10.0) -> float:
    """Map 0 to max_value range to min_score-max_score scale (inverted)."""
    if max_value == 0:
        return max_score
    
    normalized = min(value / max_value, 1.0)
    return max_score - normalized * (max_score - min_score)


def get_installs_score(apps: List[Dict]) -> float:
    """Calculate installs score using review count as proxy."""
    if not apps:
        return 1.0
    
    review_counts = []
    for app in apps:
        # Extract review count (handle different possible field names)
        reviews = app.get("reviews", app.get("rating_count", app.get("userRatingCount", 0)))
        if reviews is not None:
            review_counts.append(int(reviews))
    
    if not review_counts:
        return 1.0
    
    avg_reviews = sum(review_counts) / len(review_counts)
    return z_score_normalize(avg_reviews, 100000)


def get_rating_score(apps: List[Dict]) -> float:
    """Calculate rating score from app ratings."""
    if not apps:
        return 1.0
    
    ratings = []
    for app in apps:
        # Extract rating (handle different possible field names)
        rating = app.get("rating", app.get("score", app.get("averageUserRating")))
        if rating is not None:
            ratings.append(float(rating))
    
    if not ratings:
        return 1.0
    
    avg_rating = sum(ratings) / len(ratings)
    # Convert 0-5 scale to 1-10 difficulty scale
    return min(avg_rating * 2, 10.0)


def get_age_score(apps: List[Dict]) -> float:
    """Calculate age score based on days since last update."""
    if not apps:
        return 1.0
    
    current_time = datetime.now()
    days_since_updates = []
    
    for app in apps:
        # Extract update date (handle different formats)
        updated = app.get("updated", app.get("lastModifiedDate", app.get("releaseDate")))
        if updated:
            try:
                if isinstance(updated, str):
                    # Handle ISO format
                    if "T" in updated:
                        update_date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    else:
                        update_date = datetime.strptime(updated, "%Y-%m-%d")
                elif isinstance(updated, datetime):
                    update_date = updated
                else:
                    continue
                
                days_since = (current_time - update_date.replace(tzinfo=None)).days
                days_since_updates.append(days_since)
            except (ValueError, TypeError):
                continue
    
    if not days_since_updates:
        return 1.0
    
    avg_days = sum(days_since_updates) / len(days_since_updates)
    # Inverted score: newer apps (lower days) = higher difficulty
    return inverted_z_score_normalize(avg_days, 500)


def calculate_keyword_difficulty(keyword: str, apps: List[Dict]) -> KeywordDifficultyResult:
    """Calculate keyword difficulty score for iTunes App Store."""
    if not apps:
        raise ValueError("No apps provided for analysis")
    
    # Ensure we have enough apps for proper analysis
    top_10_apps = apps[:10] if len(apps) >= 10 else apps
    all_apps = apps[:100] if len(apps) >= 100 else apps
    
    # Calculate component scores
    title_matches = get_title_matches(keyword, top_10_apps)
    competitors = get_competitors(keyword, all_apps)
    competitors_score = z_score_normalize(competitors, 100)
    installs_score = get_installs_score(top_10_apps)
    rating_score = get_rating_score(top_10_apps)
    age_score = get_age_score(top_10_apps)
    
    # Calculate weighted final score
    # Weights: title=4, competitors=3, installs=5, rating=2, age=1
    weighted_sum = (
        4 * title_matches.score +
        3 * competitors_score +
        5 * installs_score +
        2 * rating_score +
        1 * age_score
    )
    total_weight = 4 + 3 + 5 + 2 + 1
    final_score = weighted_sum / total_weight
    
    # Ensure score is in 1-10 range
    final_score = max(1.0, min(10.0, final_score))
    
    return KeywordDifficultyResult(
        keyword=keyword,
        title_matches=title_matches,
        competitors=competitors,
        competitors_score=round(competitors_score, 2),
        installs_score=round(installs_score, 2),
        rating_score=round(rating_score, 2),
        age_score=round(age_score, 2),
        score=round(final_score, 2)
    )


async def analyze_keyword_difficulty_from_appstore_apps(keyword: str, apps) -> KeywordDifficultyResult:
    """Analyze keyword difficulty from AppstoreApp objects with caching."""
    # Get store instance
    store = get_aso_store()
    
    # Check store first
    item = await store.aget(ASONamespaces.keyword_difficulty(), keyword.lower())
    if item:
        # Convert cached data to KeywordDifficultyResult
        cached_data = item.value
        return KeywordDifficultyResult(
            keyword=cached_data["keyword"],
            title_matches=TitleMatchResult(
                exact=0,  # Not stored individually
                broad=0,
                partial=0,
                none=0,
                score=cached_data["title_matches_score"]
            ),
            competitors=cached_data["competitors"],
            competitors_score=cached_data["competitors_score"],
            installs_score=cached_data["installs_score"],
            rating_score=cached_data["rating_score"],
            age_score=cached_data["age_score"],
            score=cached_data["difficulty_score"]
        )
    
    # Convert AppstoreApp objects to dict format expected by algorithm
    app_dicts = []
    for app in apps:
        if hasattr(app, '__dict__'):
            # Convert AppstoreApp to dict
            app_dict = {
                "title": app.title,
                "description": getattr(app, 'description', ''),
                "rating": app.rating,
                "reviews": app.rating_count,
                "updated": app.release_date.isoformat() if app.release_date else None
            }
        else:
            # Already a dict
            app_dict = app
        
        app_dicts.append(app_dict)
    
    # Calculate difficulty
    result = calculate_keyword_difficulty(keyword, app_dicts)
    
    # Cache the result in store
    await store.aput(
        ASONamespaces.keyword_difficulty(),
        keyword.lower(),
        {
            "keyword": result.keyword,
            "difficulty_score": result.score,
            "title_matches_score": result.title_matches.score,
            "competitors": result.competitors,
            "competitors_score": result.competitors_score,
            "installs_score": result.installs_score,
            "rating_score": result.rating_score,
            "age_score": result.age_score
        }
    )
    
    return result