# ProxyManager

A robust Python library for managing HTTP proxies with Redis storage and intelligent proxy selection strategies. Built for high-performance applications that require reliable proxy rotation and automatic failure handling.

## Features

- **Multiple Selection Strategies**: Choose from SMART, RANDOM, or SEQUENTIAL proxy selection
- **Automatic Failure Handling**: Bad proxies are automatically removed after configurable failure thresholds
- **Redis Integration**: Fast, persistent storage for proxy data and statistics
- **Success Rate Tracking**: Monitor proxy performance with detailed statistics
- **Webshare.io Integration**: Seamlessly fetch proxies from Webshare.io API
- **Async Support**: Built with asyncio for high-performance applications

## Installation

```bash
pip install redis aiohttp
```

## Requirements

- Python 3.7+
- Redis server
- Webshare.io API key (for proxy fetching)

## Quick Start

```python
import asyncio
from proxy_manager import ProxyManager, StrategyType

async def main():
    # Initialize ProxyManager
    manager = ProxyManager(
        api_key="your_webshare_api_key",
        strategy=StrategyType.SMART,
        fail_count=3
    )
    
    # Load proxies from Webshare.io
    await manager.initialize_proxies()
    
    # Get a proxy for your request
    proxy = manager.get_proxy()
    
    # Use the proxy in your HTTP request
    # (example with requests library)
    import requests
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxy, timeout=10)
        if response.status_code == 200:
            manager.report_success(list(proxy.values())[0])
        else:
            manager.report_failure(list(proxy.values())[0])
    except:
        manager.report_failure(list(proxy.values())[0])

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### ProxyManager Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | None | Webshare.io API key |
| `amount` | int | 100 | Number of proxies to fetch |
| `fail_count` | int | 3 | Failure threshold before removing proxy |
| `strategy` | StrategyType | SMART | Proxy selection strategy |
| `host` | str | 'localhost' | Redis host |
| `port` | int | 6379 | Redis port |
| `db` | int | 0 | Redis database number |

### Strategy Types

- **SMART**: Selects proxy with highest success rate
- **RANDOM**: Randomly selects from available proxies
- **SEQUENTIAL**: Round-robin selection through proxy list

## Usage

### Core Methods

#### `async initialize_proxies()`
Loads proxies from Webshare.io if Redis proxy list is empty.

```python
await manager.initialize_proxies()
```

#### `get_proxy()`
Returns a proxy dictionary formatted for use with HTTP libraries.

```python
proxy = manager.get_proxy()
# Returns: {'http': 'http://user:pass@ip:port', 'https': 'http://user:pass@ip:port'}
```

#### `report_success(proxy: str)`
Records a successful request for the given proxy.

```python
manager.report_success("user:pass@ip:port")
```

#### `report_failure(proxy: str)`
Records a failed request. Proxy is removed if failure count exceeds threshold.

```python
manager.report_failure("user:pass@ip:port")
```

#### `async update_proxies()`
Clears all existing proxies and loads fresh ones from Webshare.io.

```python
await manager.update_proxies()
```

#### `get_stats()`
Returns comprehensive statistics about proxy usage.

```python
stats = manager.get_stats()
print(f"Total proxies: {stats['total_proxies']}")
print(f"Success rate: {stats['overall_success_rate']}%")
```

## Redis Data Structure

The library uses the following Redis keys:

- `proxy_list`: List of all available proxy strings
- `proxy:{proxy_string}`: Hash containing success/failure counts for each proxy