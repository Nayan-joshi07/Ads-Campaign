# Marketing Intelligence API

A FastAPI-based service for managing ad campaigns and computing marketing KPIs with intelligent natural language query capabilities.

## Features

### Core Campaign Management
- **Campaign CRUD**: Manage advertising campaigns across multiple channels
- **KPI Calculations**: Automatic computation of CTR, CVR, CPC, CPA, and other metrics
- **Multi-Channel Support**: Meta, Google, LinkedIn, X (Twitter)
- **Date Range Filtering**: Filter campaign data by custom date ranges
- **Event Ingestion**: Add daily stats to extend campaign datasets

### 🚀 Natural Language Query Engine
- **Intent-Based Queries**: Convert natural language prompts into filtered/sorted results
- **No External AI**: Uses regex/keyword matching for fast, reliable parsing
- **Smart Defaults**: Intelligent limit and sorting behavior
- **Confidence Scoring**: Returns helpful hints for unclear queries

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Client-2

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Start the development server
uvicorn main:app --reload

# The API will be available at:
# http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_intent_parser.py
```

## API Endpoints

### Campaign Management

#### GET `/campaigns`
List campaigns with filters and pagination.

**Query Parameters:**
- `status` - Filter by campaign status (`active`, `paused`)
- `dateFrom` - Filter stats from date (YYYY-MM-DD)
- `dateTo` - Filter stats to date (YYYY-MM-DD) 
- `limit` - Number of results (1-100, default: 10)
- `offset` - Pagination offset (default: 0)

**Example:**
```bash
GET /campaigns?status=active&dateFrom=2025-10-01&limit=5
```

#### GET `/campaigns/{campaign_id}`
Get specific campaign details with KPIs.

#### POST `/events`
Ingest daily stats for a campaign.

```json
{
  "campaign_id": "cmp_123",
  "date": "2025-10-15",
  "impressions": 10000,
  "clicks": 200,
  "conversions": 15,
  "spend": 250.00
}
```

### Metrics & Health

#### GET `/metrics/summary`
Get aggregated metrics across campaigns with best/worst performers.

#### GET `/health`
Service health check with uptime and performance metrics.

### 🎯 Intent Query API

#### POST `/intent/query`
Convert natural language prompts into campaign results.

**Request:**
```json
{
  "prompt": "show top campaigns by ctr last 7 days"
}
```

**Response:**
```json
{
  "data": [...],
  "intent": {
    "sort_by": "ctr",
    "sort_order": "desc",
    "filters": {},
    "date_from": "2025-10-08",
    "date_to": "2025-10-15",
    "limit": 5,
    "confidence": 0.70
  },
  "pagination": {
    "total": 3,
    "limit": 5,
    "offset": 0,
    "has_more": false
  }
}
```

## Natural Language Query Examples

### Sorting Queries
```
"show top campaigns by ctr"           → Sort by CTR desc, limit 5
"best performing campaign"            → Max conversions, limit 1  
"worst 5 campaigns by cpa"           → Sort by CPA asc, limit 5
"highest spend campaigns"            → Sort by spend desc
```

### Filtering Queries
```
"list paused campaigns"              → Filter status=paused
"active google campaigns"            → Filter status=active, channel=google
"meta campaigns"                     → Filter channel=meta
"running linkedin campaigns"         → Filter status=active, channel=linkedin
```

### Date Range Queries
```
"campaigns yesterday"                → Date range: yesterday
"last 7 days"                      → Date range: 7 days ago to today
"this week"                        → Date range: Monday to today
"last 30 days"                     → Date range: 30 days ago to today
"this month"                       → Date range: 1st of month to today
```

### Combined Queries
```
"top 3 active google campaigns by ctr last 7 days"
"worst paused meta campaigns by cpa this week"
"best performing linkedin campaign yesterday"
```

### Supported Metrics
- `ctr` - Click-through rate
- `cvr` - Conversion rate  
- `cpc` - Cost per click
- `cpa` - Cost per acquisition
- `conversions` - Total conversions
- `clicks` - Total clicks
- `impressions` - Total impressions
- `spend` - Total spend

### Error Handling
When queries are unclear (confidence < 0.3), the API returns helpful hints:

```json
{
  "error": "Could not understand the prompt clearly",
  "hints": [
    "Try: 'show top 5 campaigns by ctr'",
    "Try: 'list paused campaigns'",
    "Try: 'best performing campaign last 7 days'"
  ],
  "confidence": 0.1
}
```

## Architecture

### Project Structure
```
Client-2/
├── app/
│   ├── models/
│   │   └── models.py          # Pydantic models
│   ├── routes/
│   │   └── routers.py         # API endpoints
│   └── services/
│       ├── health_services.py # Health monitoring
│       ├── intent_parser.py   # Natural language parser
│       └── kpi_calculator.py  # KPI computation
├── tests/
│   ├── test_intent_api.py     # API endpoint tests
│   └── test_intent_parser.py  # Parser unit tests
├── main.py                    # FastAPI application
├── requirements.txt           # Dependencies
└── pytest.ini               # Test configuration
```

### Key Components

#### IntentParser
The core natural language processing engine that converts prompts into structured queries:

- **Pattern Matchers**: Regex-based detection for sorting, filtering, dates, limits
- **Confidence Scoring**: 0-1 score based on pattern matches
- **Smart Defaults**: Context-aware limit and metric defaults
- **Extensible**: Easy to add new patterns and keywords

#### KPICalculator
Computes marketing metrics from raw campaign stats:

- **Standard Metrics**: CTR, CVR, CPC, CPA
- **Aggregation**: Totals across date ranges
- **Zero Division Handling**: Safe calculations with proper fallbacks

#### Health Monitoring
Tracks service performance and uptime:

- **Request Tracking**: Latency and error rate monitoring
- **P95 Latency**: Performance percentile tracking
- **Uptime**: Service availability monitoring

## Testing

### Test Coverage
- **34 Test Cases**: Comprehensive coverage of all features
- **IntentParser Tests**: 16 tests covering all parsing scenarios
- **API Tests**: 18 tests covering endpoint behavior
- **Edge Cases**: Error conditions, invalid inputs, empty results

### Running Specific Tests
```bash
# Test intent parser only
pytest tests/test_intent_parser.py

# Test API endpoints only  
pytest tests/test_intent_api.py

# Test with verbose output
pytest -v

# Test with coverage report
pytest --cov=app --cov-report=html
```

## Configuration

### Environment Variables
```bash
# Optional configuration
CORS_ORIGINS=*              # CORS allowed origins
LOG_LEVEL=INFO              # Logging level
```

### Custom Settings
Modify campaign data in `app/routes/routers.py`:
```python
campaigns_db: List[Campaign] = [
    # Add your campaign data here
]
```

## Development

### Adding New Intent Patterns
1. Update `KEYWORDS` dictionaries in `IntentParser` class
2. Add pattern matching logic in appropriate `_match_*` methods
3. Add test cases in `tests/test_intent_parser.py`

### Adding New Metrics
1. Add metric calculation in `KPICalculator.calculate_kpis()`
2. Update `METRICS` list in `IntentParser`
3. Add sort key mapping in `/intent/query` endpoint

### Code Quality
```bash
# Format code (if black is installed)
black .

# Lint code (if flake8 is installed)  
flake8 app/

# Type checking (if mypy is installed)
mypy app/
```

## Production Deployment

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Server
```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## License

[Add your license information here]

## Support

For questions or issues:
- Create an issue in the repository
- Check the interactive API docs at `/docs` when running locally
- Review test cases for usage examples