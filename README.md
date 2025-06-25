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

## API Reference

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

## Usage Examples

### Basic Usage with Error Handling

```python
import asyncio
import aiohttp
from proxy_manager import ProxyManager, StrategyType

async def fetch_with_proxy(url, manager):
    proxy = manager.get_proxy()
    if not proxy:
        print("No proxies available")
        return None
    
    proxy_string = list(proxy.values())[0].replace('http://', '')
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, proxy=proxy['http'], timeout=10) as response:
                if response.status == 200:
                    manager.report_success(proxy_string)
                    return await response.text()
                else:
                    manager.report_failure(proxy_string)
                    return None
        except Exception as e:
            manager.report_failure(proxy_string)
            print(f"Request failed: {e}")
            return None

async def main():
    manager = ProxyManager(
        api_key="your_api_key",
        strategy=StrategyType.SMART,
        fail_count=5
    )
    
    await manager.initialize_proxies()
    
    # Make multiple requests
    for i in range(10):
        result = await fetch_with_proxy("https://httpbin.org/ip", manager)
        if result:
            print(f"Request {i+1} successful")
        
    # Print statistics
    stats = manager.get_stats()
    print(f"\nStats: {stats['good_proxies']}/{stats['total_proxies']} proxies working")
    print(f"Overall success rate: {stats['overall_success_rate']}%")

if __name__ == "__main__":
    asyncio.run(main())
```

### Monitoring Proxy Performance

```python
def monitor_proxies(manager):
    stats = manager.get_stats()
    
    print(f"=== Proxy Statistics ===")
    print(f"Total Proxies: {stats['total_proxies']}")
    print(f"Good Proxies: {stats['good_proxies']}")
    print(f"Bad Proxies: {stats['bad_proxies']}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Overall Success Rate: {stats['overall_success_rate']}%")
    
    print(f"\n=== Top 5 Performing Proxies ===")
    sorted_proxies = sorted(
        stats['proxy_details'].items(),
        key=lambda x: x[1]['success_rate'],
        reverse=True
    )[:5]
    
    for proxy, details in sorted_proxies:
        print(f"{proxy[:20]}... - Success Rate: {details['success_rate']}% "
              f"({details['success']}/{details['total']} requests)")
```

### Different Strategy Comparison

```python
async def compare_strategies():
    strategies = [StrategyType.SMART, StrategyType.RANDOM, StrategyType.SEQUENTIAL]
    
    for strategy in strategies:
        manager = ProxyManager(
            api_key="your_api_key",
            strategy=strategy,
            db=strategies.index(strategy)  # Use different Redis DB for each
        )
        
        await manager.initialize_proxies()
        
        # Perform test requests
        for _ in range(50):
            proxy = manager.get_proxy()
            # Simulate request success/failure
            if random.random() > 0.3:  # 70% success rate
                manager.report_success(list(proxy.values())[0].replace('http://', ''))
            else:
                manager.report_failure(list(proxy.values())[0].replace('http://', ''))
        
        stats = manager.get_stats()
        print(f"{strategy.value}: {stats['overall_success_rate']}% success rate")
```

## Error Handling

The ProxyManager includes several built-in error handling mechanisms:

- **Redis Connection**: Exits gracefully if Redis connection fails
- **API Failures**: Raises exceptions for failed Webshare.io API calls
- **Proxy Validation**: Validates proxy format before use
- **Automatic Cleanup**: Removes failed proxies automatically

## Redis Data Structure

The library uses the following Redis keys:

- `proxy_list`: List of all available proxy strings
- `proxy:{proxy_string}`: Hash containing success/failure counts for each proxy

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the Webshare.io API documentation for proxy-related questions
- Ensure Redis is properly configured and running