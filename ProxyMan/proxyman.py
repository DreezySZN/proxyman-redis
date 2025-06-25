import redis
import sys
import aiohttp
import enum
import random

class StrategyType(enum.Enum):
    RANDOM = 'random'
    SMART = 'smart'
    SEQUENTIAL = 'sequential'


class ProxyManager:

    def __init__(self, api_key: str = None, amount: int = 100, fail_count: int = 3, strategy=StrategyType.SMART, host='localhost', port=6379, db=0):
        """
        A proxy management class that handles fetching, storing, and managing HTTP proxies
        using Redis for storage and Webshare.io API as the proxy source.
        """

        # redis config
        self.redis_host = host
        self.redis_port = port
        self.redis_db = db

        # proxy config
        self.api_key = api_key
        self.amount = amount
        self.fail_count = fail_count
        self.strategy = strategy

        self._sequential_index = 0

        self.__setup()
    
    def __setup(self):
        """
        Establish Redis connection. Exit if connection fails.
        """
        try:
            self.redis = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db)
            if self.redis.ping():
                if self.redis.llen('proxy_list') == 0:
                    print("No proxies found in Redis. Run initialize_proxies() to load them.")
            else:
                raise redis.ConnectionError("Redis ping failed")

        except redis.ConnectionError:
            print("Redis connection failed.")
            sys.exit(1)
        
    async def initialize_proxies(self):
        """
        Load proxies from Webshare if Redis proxy list is empty.
        """
        if self.redis.llen('proxy_list') == 0:
            await self._load_proxies()
    
    def _format_proxy(self, proxy):
        """
        Format the proxy as a dict for requests.
        """
        if not proxy or not isinstance(proxy, str):
            raise ValueError("Proxy must be a non-empty string")
        
        proxy.strip()
        if not proxy:
            raise ValueError("Proxy cannot be empty or whitespace only")
        
        if proxy.startswith('http://') or proxy.startswith('https://'):
            return {'http': proxy, 'https': proxy}
        else:
            return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}

    async def _load_proxies(self):
        """
        Fetch and store valid proxies from Webshare.io.
        """
        if self.api_key is None:
            raise Exception("API Key is not set. Please set it before calling this method.")
        
        headers = {"Authorization": self.api_key}
        url = f"https://proxy.webshare.io/api/proxy/list/?page=1"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200 and 'json' in resp.headers['Content-Type']:
                    data = await resp.json()
                else:
                    raise Exception(f"Failed to fetch proxies: {resp.status}")
                
                if 'results' in data:
                    results = data['results']
                    for result in results:
                        valid = result['valid']
                        if not valid:
                            continue

                        username = result['username']
                        password = result['password']
                        ip = result['proxy_address']
                        port = result['ports']['http']

                        proxy = f"{username}:{password}@{ip}:{port}"
                        key = f"proxy:{proxy}"

                        if not self.redis.exists(key):
                            self.redis.hset(key, mapping={"success": 0, "failure": 0})
                            self.redis.lpush('proxy_list', proxy)
                    print(f"Loaded {len(results)} proxies from Webshare.io")
                else:
                    raise Exception("No proxy results found in API response")

    def _get_all_proxies(self):
        """Get all proxy strings from Redis list"""
        proxies = self.redis.lrange('proxy_list', 0, -1)
        return [proxy.decode() for proxy in proxies]
    
    def _get_smart_proxy(self):
        """
        Get the proxy with the highest success rate (success / (success + failure + 0.1)).
        Returns None if no proxies found.
        """
        proxies = self._get_all_proxies()
        if not proxies:
            return None

        def score(proxy):
            key = f"proxy:{proxy}"
            stats = self.redis.hgetall(key)
            success = int(stats.get(b'success', 0))
            failure = int(stats.get(b'failure', 0))
            return success / (success + failure + 0.1)

        proxy = max(proxies, key=score)
        return self._format_proxy(proxy)

    def _get_random_proxy(self):
        """
        Get a random proxy from the list.
        """
        proxies = self._get_all_proxies()
        if not proxies:
            return None
        proxy = random.choice(proxies)

        return self._format_proxy(proxy)
    
    def _get_sequential_proxy(self):
        """
        Get proxies sequentially in round-robin order.
        """
        proxies = self._get_all_proxies()
        total = len(proxies)
        if total == 0:
            return None

        proxy = proxies[self._sequential_index % total]
        self._sequential_index = (self._sequential_index + 1) % total

        return self._format_proxy(proxy)
    
    def report_success(self, proxy: str):
        """
        Report a successful request with the proxy
        """
        key = f"proxy:{proxy}"
        self.redis.hincrby(key, "success", 1)

    def report_failure(self, proxy: str):
        """
        Report a failed request with the proxy
        """
        key = f"proxy:{proxy}"
        failure_count = self.redis.hincrby(key, "failure", 1)
        
        # Remove proxy if it exceeds failure threshold
        if failure_count >= self.fail_count:
            self._remove_bad_proxy(proxy)

    def _remove_bad_proxy(self, proxy: str):
        """
        Remove a bad proxy from Redis storage
        """
        key = f"proxy:{proxy}"
        self.redis.delete(key)
        self.redis.lrem('proxy_list', 0, proxy)
        
    async def update_proxies(self):
        """
        Update the proxy list, deleting old proxies and loading new ones.
        """
        # Clear all proxy data
        for key in self.redis.keys("proxy:*"):
            self.redis.delete(key)
        self.redis.delete('proxy_list')
        
        await self._load_proxies()

    def get_proxy(self):
        """
        Get a proxy based on the configured strategy
        """
        if self.strategy == StrategyType.SMART:
            return self._get_smart_proxy()
        elif self.strategy == StrategyType.RANDOM:
            return self._get_random_proxy()
        elif self.strategy == StrategyType.SEQUENTIAL:
            return self._get_sequential_proxy()
        else:
            return self._get_smart_proxy()  # Default fallback
    
    def get_stats(self):
        """
        Get statistics about proxy usage
        
        :return: Dict with proxy statistics
        """
        proxies = self._get_all_proxies()
        proxy_details = {}
        total_success = 0
        total_failure = 0
        bad_proxies = 0
        
        for proxy in proxies:
            key = f"proxy:{proxy}"
            proxy_stats = self.redis.hgetall(key)
            success = int(proxy_stats.get(b'success', 0))
            failure = int(proxy_stats.get(b'failure', 0))
            
            total_success += success
            total_failure += failure
            
            if failure >= self.fail_count:
                bad_proxies += 1
            
            proxy_details[proxy] = {
                'success': success,
                'failure': failure,
                'total': success + failure,
                'success_rate': round((success / (success + failure) * 100) if (success + failure) > 0 else 0, 2)
            }
        
        return {
            'total_proxies': len(proxies),
            'good_proxies': len(proxies) - bad_proxies,
            'bad_proxies': bad_proxies,
            'total_requests': total_success + total_failure,
            'total_success': total_success,
            'total_failure': total_failure,
            'overall_success_rate': round((total_success / (total_success + total_failure) * 100) if (total_success + total_failure) > 0 else 0, 2),
            'proxy_details': proxy_details
        }
        

