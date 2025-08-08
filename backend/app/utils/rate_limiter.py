"""
Rate limiting utilities for web scraping application.
Implements various rate limiting strategies to prevent spam and respect server resources.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 30
    requests_per_hour: int = 1000
    burst_limit: int = 5
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    backoff_factor: float = 1.5
    max_backoff: float = 60.0
    adaptive_threshold: float = 0.8


class RateLimiter:
    """
    Thread-safe rate limiter with multiple strategies.
    Supports per-domain rate limiting for web scraping.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        self._lock = threading.RLock()
        
        # Storage for different rate limiting strategies
        self._token_buckets: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._sliding_windows: Dict[str, deque] = defaultdict(deque)
        self._fixed_windows: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._request_history: Dict[str, deque] = defaultdict(deque)
        
        # Adaptive rate limiting
        self._response_times: Dict[str, deque] = defaultdict(deque)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._adaptive_rates: Dict[str, float] = defaultdict(
            lambda: self.config.requests_per_second
        )
        
    def can_proceed(self, domain: str) -> tuple[bool, float]:
        """
        Check if a request can proceed for the given domain.
        
        Args:
            domain: Domain to check rate limit for
            
        Returns:
            Tuple of (can_proceed, delay_seconds)
        """
        with self._lock:
            if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._check_token_bucket(domain)
            elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._check_sliding_window(domain)
            elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._check_fixed_window(domain)
            elif self.config.strategy == RateLimitStrategy.ADAPTIVE:
                return self._check_adaptive(domain)
            else:
                return True, 0.0
                
    def record_request(self, domain: str, success: bool = True, 
                      response_time: Optional[float] = None):
        """
        Record a request for rate limiting and adaptive behavior.
        
        Args:
            domain: Domain the request was made to
            success: Whether the request was successful
            response_time: Response time in seconds
        """
        with self._lock:
            now = time.time()
            
            # Record request history
            self._request_history[domain].append(now)
            
            # Clean old history (keep last hour)
            while (self._request_history[domain] and 
                   now - self._request_history[domain][0] > 3600):
                self._request_history[domain].popleft()
                
            # Record response time for adaptive limiting
            if response_time is not None:
                self._response_times[domain].append((now, response_time))
                # Keep last 100 response times
                if len(self._response_times[domain]) > 100:
                    self._response_times[domain].popleft()
                    
            # Track errors
            if not success:
                self._error_counts[domain] += 1
            else:
                # Decay error count on success
                self._error_counts[domain] = max(0, self._error_counts[domain] - 1)
                
            # Update adaptive rate if using adaptive strategy
            if self.config.strategy == RateLimitStrategy.ADAPTIVE:
                self._update_adaptive_rate(domain)
                
    def get_stats(self, domain: str) -> Dict[str, Any]:
        """
        Get rate limiting statistics for a domain.
        
        Args:
            domain: Domain to get stats for
            
        Returns:
            Dictionary of statistics
        """
        with self._lock:
            now = time.time()
            history = self._request_history[domain]
            
            # Calculate requests in different time windows
            recent_requests = [t for t in history if now - t <= 60]  # Last minute
            hourly_requests = [t for t in history if now - t <= 3600]  # Last hour
            
            stats = {
                "domain": domain,
                "strategy": self.config.strategy.value,
                "requests_last_minute": len(recent_requests),
                "requests_last_hour": len(hourly_requests),
                "total_requests": len(history),
                "error_count": self._error_counts[domain],
                "current_rate": self._adaptive_rates.get(domain, self.config.requests_per_second)
            }
            
            # Add response time stats if available
            if domain in self._response_times:
                response_times = [rt for _, rt in self._response_times[domain]]
                if response_times:
                    stats["avg_response_time"] = sum(response_times) / len(response_times)
                    stats["max_response_time"] = max(response_times)
                    
            return stats
            
    def reset_domain(self, domain: str):
        """Reset rate limiting data for a domain."""
        with self._lock:
            self._token_buckets.pop(domain, None)
            self._sliding_windows.pop(domain, None)
            self._fixed_windows.pop(domain, None)
            self._request_history.pop(domain, None)
            self._response_times.pop(domain, None)
            self._error_counts.pop(domain, None)
            self._adaptive_rates.pop(domain, None)
            
    def _check_token_bucket(self, domain: str) -> tuple[bool, float]:
        """Token bucket rate limiting implementation."""
        now = time.time()
        bucket = self._token_buckets[domain]
        
        # Initialize bucket if needed
        if "tokens" not in bucket:
            bucket["tokens"] = self.config.burst_limit
            bucket["last_update"] = now
            
        # Add tokens based on time elapsed
        elapsed = now - bucket["last_update"]
        tokens_to_add = elapsed * self.config.requests_per_second
        bucket["tokens"] = min(
            self.config.burst_limit,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_update"] = now
        
        # Check if we can consume a token
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, 0.0
        else:
            # Calculate delay needed
            delay = (1 - bucket["tokens"]) / self.config.requests_per_second
            return False, delay
            
    def _check_sliding_window(self, domain: str) -> tuple[bool, float]:
        """Sliding window rate limiting implementation."""
        now = time.time()
        window = self._sliding_windows[domain]
        
        # Remove old requests outside the window
        while window and now - window[0] > 60:  # 1 minute window
            window.popleft()
            
        # Check if under limit
        if len(window) < self.config.requests_per_minute:
            window.append(now)
            return True, 0.0
        else:
            # Calculate delay until oldest request expires
            delay = 60 - (now - window[0])
            return False, max(0, delay)
            
    def _check_fixed_window(self, domain: str) -> tuple[bool, float]:
        """Fixed window rate limiting implementation."""
        now = time.time()
        window = self._fixed_windows[domain]
        current_minute = int(now // 60)
        
        # Reset counter if in new window
        if window.get("minute", 0) != current_minute:
            window["minute"] = current_minute
            window["count"] = 0
            
        # Check if under limit
        if window["count"] < self.config.requests_per_minute:
            window["count"] += 1
            return True, 0.0
        else:
            # Calculate delay until next window
            delay = 60 - (now % 60)
            return False, delay
            
    def _check_adaptive(self, domain: str) -> tuple[bool, float]:
        """Adaptive rate limiting based on server response."""
        current_rate = self._adaptive_rates[domain]
        
        # Use token bucket with adaptive rate
        config_backup = self.config.requests_per_second
        self.config.requests_per_second = current_rate
        result = self._check_token_bucket(domain)
        self.config.requests_per_second = config_backup
        
        return result
        
    def _update_adaptive_rate(self, domain: str):
        """Update adaptive rate based on server performance."""
        now = time.time()
        response_times = self._response_times[domain]
        error_count = self._error_counts[domain]
        current_rate = self._adaptive_rates[domain]
        
        # Calculate recent average response time
        recent_times = [rt for ts, rt in response_times if now - ts <= 300]  # Last 5 minutes
        
        if recent_times:
            avg_response_time = sum(recent_times) / len(recent_times)
            
            # Adjust rate based on response time and errors
            if avg_response_time > 2.0 or error_count > 3:
                # Slow down
                new_rate = current_rate / self.config.backoff_factor
            elif avg_response_time < 0.5 and error_count == 0:
                # Speed up
                new_rate = current_rate * 1.1
            else:
                new_rate = current_rate
                
            # Apply limits
            new_rate = max(0.1, min(self.config.requests_per_second * 2, new_rate))
            self._adaptive_rates[domain] = new_rate


class AsyncRateLimiter:
    """Async version of rate limiter for use with asyncio."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.limiter = RateLimiter(config)
        self._lock = asyncio.Lock()
        
    async def wait_if_needed(self, domain: str):
        """Wait if rate limit requires delay."""
        async with self._lock:
            can_proceed, delay = self.limiter.can_proceed(domain)
            if not can_proceed and delay > 0:
                await asyncio.sleep(delay)
                
    async def record_request(self, domain: str, success: bool = True, 
                           response_time: Optional[float] = None):
        """Async version of record_request."""
        async with self._lock:
            self.limiter.record_request(domain, success, response_time)


# Context manager for automatic rate limiting
class RateLimitContext:
    """Context manager that automatically handles rate limiting."""
    
    def __init__(self, limiter: RateLimiter, domain: str):
        self.limiter = limiter
        self.domain = domain
        self.start_time = None
        
    def __enter__(self):
        # Wait for rate limit
        can_proceed, delay = self.limiter.can_proceed(self.domain)
        if not can_proceed and delay > 0:
            time.sleep(delay)
            
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            response_time = time.time() - self.start_time
            success = exc_type is None
            self.limiter.record_request(self.domain, success, response_time)


# Example usage
if __name__ == "__main__":
    # Create rate limiter
    config = RateLimitConfig(
        requests_per_second=2.0,
        requests_per_minute=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    )
    limiter = RateLimiter(config)
    
    # Test rate limiting
    domain = "example.com"
    
    print("Testing rate limiter...")
    for i in range(10):
        can_proceed, delay = limiter.can_proceed(domain)
        print(f"Request {i+1}: Can proceed: {can_proceed}, Delay: {delay:.2f}s")
        
        if not can_proceed and delay > 0:
            print(f"Waiting {delay:.2f} seconds...")
            time.sleep(delay)
            
        # Simulate request
        limiter.record_request(domain, success=True, response_time=0.5)
        time.sleep(0.1)  # Small delay between requests
        
    # Print stats
    stats = limiter.get_stats(domain)
    print(f"\nFinal stats: {stats}")