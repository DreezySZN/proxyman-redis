# ProxyMan-Redis 

A Redis-backed proxy manager with smart selection strategies

## Features

- Redis storage for persistence and performance
- Smart, random, and sequential proxy selection
- Automatic bad proxy removal
- Success/failure tracking
- Webshare.io API integration

## Installation

```bash
pip install proxyman-redis
```

## Quick Start

```python
from proxyman import ProxyMan, StrategyType
import asyncio

async def main():
    # Initialize
    pm = ProxyMan(api_key="your_webshare_key", strategy=StrategyType.SMART)
    await pm.initialize_proxies()
    
    # Get proxy for requests
    proxy = pm.get_formatted_proxy()
    
    # Use with requests
    import requests
    response = requests.get("https://httpbin.org/ip", proxies=proxy)

asyncio.run(main())
```

## Configuration

```python
pm = ProxyMan(
    api_key="your_key",     # Webshare.io API key
    amount=100,             # Max proxies to store
    fail_count=3,           # Failures before removal
    strategy=StrategyType.SMART  # Selection strategy
)
```

## Strategies

- **SMART**: Selects best performing proxies
- **RANDOM**: Random selection
- **SEQUENTIAL**: Round-robin rotation

## Reporting Results

```python
# Report success/failure for better proxy selection
pm.report_success("user:pass@ip:port")
pm.report_failure("user:pass@ip:port")
```

## Statistics

```python
stats = pm.get_stats()
# Returns: total_proxies, good_proxies, success_rate, etc.
```

## Requirements

- Python 3.7+
- Redis server running on localhost:6379
- Webshare.io API key (optional)

## License

BSD 3-Clause License