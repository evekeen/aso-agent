# Apple App Store Traffic Estimation Algorithm

## Overview
This algorithm estimates the search traffic potential for a specific keyword in the Apple App Store. A higher score indicates higher expected traffic. The algorithm analyzes search suggestions, category rankings, install proxies, and keyword characteristics.

## Input Requirements
- **keyword**: String (converted to lowercase)
- **apps**: List of app objects from iTunes search results (top 100 apps)

## Algorithm Components

### 1. Search Suggestion Score
**Function**: `getSuggestScore(keyword)`

Analyzes how the keyword appears in iTunes search suggestions and uses the built-in priority score.

#### Algorithm Steps:
1. Query iTunes search suggestions API with the keyword
2. Find exact keyword match in returned suggestions list
3. Extract priority score from matching suggestion (iTunes provides this directly)
4. If keyword not found in suggestions, use priority = 0
5. Apply z-score normalization with max priority threshold of 8,000
6. Map to 1-10 scale where higher priority = higher traffic potential

### 2. Category Ranking Analysis
**Function**: `getRankedApps(top_10_apps)`

Checks how many of the keyword's top apps appear in category rankings and their average position.

#### Algorithm Steps:
1. For each top 10 app, determine its collection type (free/paid) and category
2. Fetch category ranking lists for all unique collection/category combinations
3. Look up each app's position in its respective category ranking (1-100)
4. Count how many apps appear in category rankings
5. Calculate average rank position for those that do appear
6. Apply composite scoring:
   - Count score: z-score normalization (more ranked apps = higher traffic)
   - Average rank score: inverted score (lower rank position = higher traffic)
   - Weighted combination: count_score × 5 + avg_rank_score × 1
7. If no apps are ranked, return minimum score of 1

### 3. Install Score (Review Count Proxy)
**Function**: `getInstallsScore(top_10_apps)`

Same as difficulty algorithm but with lower weight in final calculation.

#### Algorithm Steps:
1. Extract review count from each of the top 10 apps
2. Calculate average review count across all apps
3. Apply z-score normalization with maximum threshold of 100,000 reviews
4. Map result to 1-10 scale where higher review counts = higher traffic potential
5. Same calculation as difficulty algorithm but with lower weight in final score

### 4. Keyword Length Analysis
**Function**: `getKeywordLength(keyword)`

Analyzes keyword length - assumes shorter keywords get more traffic.

#### Algorithm Steps:
1. Count character length of the keyword
2. Apply inverted scoring with maximum length of 25 characters
3. Shorter keywords receive higher scores (assumption: shorter = more traffic)
4. Map to 1-10 scale where 1 character = score 10, 25 characters = score 1

## Scoring Functions

Uses identical scoring functions as difficulty algorithm:

- **General Score**: Linear interpolation mapping any range to 1-10 scale
- **Z-Score**: Maps 0 to max_value range to 1-10 scale  
- **Inverted Score**: Maps range to 1-10 scale but inverted (higher input = lower score)
- **Aggregate**: Weighted average combination mapped to 1-10 scale
- **Rounding**: All scores rounded to 2 decimal places

## Final Traffic Score Calculation

### Component Weights:
- **Search Suggestions**: Weight = 8 (highest importance - direct traffic indicator)
- **Category Rankings**: Weight = 3 (moderate importance)
- **Installs (Reviews)**: Weight = 2 (lower importance than in difficulty)
- **Keyword Length**: Weight = 1 (lowest importance)

### Final Score Calculation:
1. Ensure top 10 apps have full details (fetch if needed)
2. Calculate all 4 component scores individually
3. Apply weighted aggregation: (8×suggest + 1×length + 2×installs + 3×ranked)
4. Normalize final result to 1-10 scale
5. Return complete analysis object with individual component scores and final traffic score

## iTunes Store API Requirements

### Required API Data Formats:

**Suggestion API Response:**
- List of suggestion objects with 'term' and 'priority' fields
- Priority is numeric score (0-10,000) indicating search popularity

**Category Rankings API Response:**
- Ordered list of apps in specific collection/category
- Apps include appId, title, free status, primaryGenreId
- Results ordered by ranking position (index 0 = rank 1)

**App Detail API Response:**
- Complete app data including description, reviews, rating, update date
- Required for apps that don't have full details from search results

## Collection and Category Types

**iTunes Collections:**
- TOP_FREE_IOS: Free app rankings
- TOP_PAID_IOS: Paid app rankings

**Common Category IDs:**
- 6008: Photo & Video
- 6000: Business
- 6022: Games  
- 6015: Music
- 6021: Productivity

## Collection Query Logic

**App Collection Determination:**
- Check app's 'free' field (default: true)
- Free apps → TOP_FREE_IOS collection
- Paid apps → TOP_PAID_IOS collection

**Category Query Building:**
- Extract primaryGenreId from app data
- Combine with collection type for API query
- Request top 100 apps in that collection/category

## Expected Output Format

The algorithm returns a complete analysis object containing:
- **suggest**: iTunes suggestion priority score and normalized score
- **ranked**: Count of top apps in category rankings, average rank, and composite score
- **installs**: Average review count and normalized score
- **length**: Keyword character length and inverted score
- **score**: Final weighted traffic score (1-10 scale, higher = more traffic potential)

## Implementation Considerations

**Performance Optimizations:**
- Implement API rate limiting and throttling
- Cache category rankings (change infrequently)
- Batch API requests where possible
- Handle API failures with fallback values

**iTunes-Specific Differences:**
- Uses review count proxy instead of install data
- iTunes provides suggestion priority scores directly
- Different category/collection structure than Google Play
- Generally requires fewer API calls due to richer data