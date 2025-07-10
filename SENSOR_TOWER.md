# Sensor Tower API Integration

This document describes the Sensor Tower API integration for market size analysis in the ASO Agent.

## Overview

The Sensor Tower integration provides market size analysis by fetching revenue data for iOS apps. This enables:

- **Revenue Analysis**: Get last month's revenue for specific apps
- **Market Size Calculation**: Calculate total market size for keywords based on competing apps
- **Performance Metrics**: Compare app performance across different keywords

## Setup

### 1. Get API Key

1. Sign up for Sensor Tower API access at https://sensortower.com/api
2. Obtain your API key from the dashboard

### 2. Configure Environment

```bash
export SENSOR_TOWER_API_KEY="your_api_key_here"
```

Or add to your `.env` file:
```
SENSOR_TOWER_API_KEY=your_api_key_here
```

## Usage

### Direct API Usage

```python
from src.lib.sensor_tower import get_apps_revenue

# Fetch revenue for specific app IDs
app_ids = ["389801252", "448457842"]  # Instagram, Strava
results = await get_apps_revenue(app_ids)

for app_id, result in results.items():
    if isinstance(result, str):
        print(f"Error for {app_id}: {result}")
    else:
        print(f"{result.app_name}: {result.last_month_revenue_string}")
```

### LangGraph Node Usage

```python
# State should contain apps_by_keyword data
state = {
    "apps_by_keyword": {
        "fitness tracker": ["389801252", "448457842"],
        "workout app": ["448457842", "1179624268"]
    }
}

# Run market size analysis
result = await get_keyword_total_market_size(state)

print("Revenue by keyword:", result["revenue_by_keyword"])
print("Revenue by app:", result["revenue_by_app"])
```

## Data Structure

### AppRevenueResult

```python
@dataclass
class AppRevenueResult:
    app_id: str
    app_name: str
    publisher: str
    last_month_revenue_usd: float
    last_month_revenue_string: str  # e.g., "$50,000"
    last_month_downloads: int
    last_month_downloads_string: str  # e.g., "10K"
    bundle_id: str
    version: str
    rating: Optional[float]
    last_updated: str
    source: str  # "api" or "cache"
```

## Caching

- **Automatic Caching**: Results are cached for 24 hours by default
- **Memory Cache**: Uses in-memory storage (SimpleCache class)
- **Cache Stats**: Available via `cache.get_stats()`

## Error Handling

The integration follows strict error handling principles:

- **API Errors**: Network issues, rate limits, invalid keys
- **Data Validation**: Invalid app IDs, missing data
- **No Fallbacks**: Errors are propagated without silent failures

Common error scenarios:
- `ValueError`: Invalid input (empty app list, missing API key)
- `RuntimeError`: API failures, network issues
- App-specific errors: Returned as string messages in results

## Rate Limiting

- **Batch Processing**: Apps processed in batches of 5
- **Delays**: 1-second delay between batches
- **Graceful Handling**: Rate limit errors are caught and reported

## Testing

Run tests with:
```bash
python tests/test_sensor_tower.py
```

Demo with real API:
```bash
# Set your API key first
export SENSOR_TOWER_API_KEY="your_key"
python demo_market_size.py
```

## Integration with ASO Workflow

The market size analysis integrates into the ASO workflow as follows:

1. **Keywords Generated**: From app ideas
2. **Apps Found**: For each keyword (via app search)
3. **Revenue Fetched**: For all unique apps
4. **Market Size Calculated**: Total revenue per keyword
5. **Insights Generated**: Keyword difficulty and opportunity

## API Endpoints Used

- **App Details**: `GET /v1/ios/app/{app_id}/details`
- **Revenue Data**: Included in app details response
- **Rate Limits**: Varies by Sensor Tower plan

## Security Notes

- **API Key Storage**: Store in environment variables, not code
- **Key Rotation**: Regenerate keys periodically
- **Access Control**: Limit API key permissions as needed

## Troubleshooting

### Common Issues

1. **"Invalid API key"** - Check SENSOR_TOWER_API_KEY environment variable
2. **"Rate limit exceeded"** - Reduce batch size or add delays
3. **"App not found"** - Verify app ID is correct iOS App Store ID
4. **Network timeouts** - Check internet connection and API status

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Limitations

- **iOS Only**: Currently supports iOS App Store only
- **Revenue Estimates**: Data is estimated, not exact figures
- **Rate Limits**: Subject to Sensor Tower API limits
- **Cost**: API usage may incur costs based on plan

## Future Enhancements

- Support for Google Play Store apps
- Historical revenue trends
- Competitive analysis features
- Enhanced caching with persistence
- Bulk export capabilities