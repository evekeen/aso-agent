# Apple App Store Keyword Difficulty Algorithm

## Overview
This algorithm calculates the difficulty of ranking for a specific keyword in the Apple App Store. A higher score indicates higher difficulty (harder to rank). The algorithm analyzes the top 100 search results for a keyword and calculates various metrics.

## Input Requirements
- **keyword**: String (converted to lowercase)
- **apps**: List of app objects from iTunes search results (top 100 apps)

## Algorithm Components

### 1. Title Matching Analysis
**Function**: `getTitleMatches(keyword, top_10_apps)`

Analyzes how well the keyword matches the titles of the top 10 apps.

#### Match Types:
- **exact**: Title contains the complete keyword in exact order
- **broad**: Title contains all keyword words but in different order  
- **partial**: Title contains some keyword words
- **none**: Title contains no keyword words

#### Algorithm Steps:
1. Convert keyword and app title to lowercase
2. Check for exact match (keyword appears as-is in title)
3. If no exact match, split keyword into words and check if all words appear in title (broad match)
4. If not all words match, check if any words appear in title (partial match)
5. If no words match, classify as 'none'
6. Count occurrences of each match type across top 10 apps
7. Calculate weighted score: (10 × exact_count + 5 × broad_count + 2.5 × partial_count) ÷ total_apps

### 2. Competitor Analysis
**Function**: `getCompetitors(keyword, all_100_apps)`

Counts how many apps in the top 100 results actually target the keyword in their content.

#### Algorithm Steps:
1. For each app in top 100 results, extract keywords from title and description using NLP
2. Clean text by removing contractions ('t, 's, 'll, 're, 've)
3. Extract both individual words and phrases (max 3 words)
4. Score keywords by frequency/importance and take top 10
5. Check if target keyword appears in app's top 10 keywords
6. Count total apps that target the keyword
7. Calculate z-score normalized against total app count (0 to 100 apps → 1 to 10 score)

### 3. Install Score (Review Count for iTunes)
**Function**: `getInstallsScore(top_10_apps)`

Since iTunes doesn't expose install counts, uses review count as proxy.

#### Algorithm Steps:
1. Extract review count from each of the top 10 apps
2. Calculate average review count across all apps
3. Apply z-score normalization with maximum threshold of 100,000 reviews
4. Map result to 1-10 scale where higher review counts = higher difficulty

### 4. Rating Analysis
**Function**: `getRating(top_10_apps)`

Calculates average rating of top 10 apps.

#### Algorithm Steps:
1. Extract rating (0-5 scale) from each of the top 10 apps
2. Calculate average rating across all apps
3. Convert to 1-10 difficulty scale by multiplying average by 2
4. Higher average rating = higher difficulty (harder to compete with well-rated apps)

### 5. App Age Analysis
**Function**: `getAge(top_10_apps)`

Measures average days since last update for top 10 apps.

#### Algorithm Steps:
1. Extract last update date from each of the top 10 apps
2. Convert dates to days since update (current date - update date)
3. Calculate average days since update across all apps
4. Apply inverted z-score with 500-day maximum threshold
5. Lower days since update = higher difficulty (fresher apps are harder to compete with)
6. Map to 1-10 scale where recently updated apps increase difficulty

## Scoring Functions

### Core Calculation Functions
- **General Score**: Maps any value between min/max to 1-10 scale using linear interpolation
- **Z-Score**: Maps 0 to max_value range to 1-10 scale (higher input = higher score)
- **Inverted Score**: Maps min/max range to 1-10 scale but inverted (higher input = lower score)
- **Inverted Z-Score**: Maps 0 to max_value range to 1-10 scale inverted
- **Aggregate**: Combines multiple scores using weighted average, then maps to 1-10 scale
- **Rounding**: All scores rounded to 2 decimal places

## Final Difficulty Score Calculation

### Component Weights:
- **Title Matches**: Weight = 4
- **Competitors**: Weight = 3  
- **Installs (Reviews)**: Weight = 5 (highest importance)
- **Rating**: Weight = 2
- **Age**: Weight = 1 (lowest importance)

### Final Score Calculation:
1. Calculate all 5 component scores individually
2. Apply weighted aggregation using component weights
3. Use aggregate function to combine: (4×title + 3×competitors + 5×installs + 2×rating + 1×age)
4. Normalize final result to 1-10 scale
5. Return complete analysis object with individual component scores and final difficulty score

## Keyword Extraction (for Competitor Analysis)

Uses NLP-based keyword extraction similar to retext-keywords library:

### Text Processing Steps:
1. Clean text by removing contractions: 't, 's, 'll, 're, 've
2. Extract individual words and phrases (maximum 3 words per phrase)
3. Score keywords by frequency and linguistic importance
4. Apply phrase score multiplier of 2.5x for multi-word phrases
5. Filter phrases to 3 words or less
6. Remove single-character words
7. Combine title keywords (priority) with description keywords
8. Return top 20 keywords sorted by score
9. For competitor analysis, check if target keyword appears in top 10 extracted keywords

## Data Requirements from iTunes API

Each app object should contain:
- `title`: App title
- `description`: App description  
- `summary`: App summary (if available)
- `score`: App rating (0-5)
- `reviews`: Number of reviews
- `updated`: Last update date (ISO string or timestamp)

## Expected Output Format

The algorithm returns a complete analysis object containing:
- **titleMatches**: Counts and score for exact/broad/partial/none matches
- **competitors**: Count of competing apps and normalized score
- **installs**: Average review count and normalized score
- **rating**: Average rating and converted score
- **age**: Average days since update and inverted score
- **score**: Final weighted difficulty score (1-10 scale, higher = more difficult)