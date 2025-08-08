"""
URL validation utilities for web scraping application.
Provides comprehensive URL validation, normalization, and security checks.
"""

import re
import urllib.parse
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import ipaddress

class URLValidator:
    """Validates and normalizes URLs for web scraping."""
    
    # Common dangerous schemes to block
    BLOCKED_SCHEMES = {
        'javascript', 'data', 'vbscript', 'file', 'ftp'
    }
    
    # Allowed schemes for web scraping
    ALLOWED_SCHEMES = {'http', 'https'}
    
    # Private IP ranges to block (security)
    PRIVATE_IP_PATTERNS = [
        r'^127\.',           # Loopback
        r'^192\.168\.',      # Private Class C
        r'^10\.',            # Private Class A
        r'^172\.(1[6-9]|2[0-9]|3[01])\.',  # Private Class B
        r'^169\.254\.',      # Link-local
        r'^::1$',            # IPv6 loopback
        r'^fe80:',           # IPv6 link-local
        r'^fc00:',           # IPv6 unique local
    ]
    
    def __init__(self, 
                 max_url_length: int = 2048,
                 allow_private_ips: bool = False,
                 custom_blocked_domains: Optional[List[str]] = None):
        """
        Initialize URL validator.
        
        Args:
            max_url_length: Maximum allowed URL length
            allow_private_ips: Whether to allow private IP addresses
            custom_blocked_domains: Additional domains to block
        """
        self.max_url_length = max_url_length
        self.allow_private_ips = allow_private_ips
        self.blocked_domains = set(custom_blocked_domains or [])
        
    def is_valid_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate if URL is safe and properly formatted.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL must be a non-empty string"
            
        # Check URL length
        if len(url) > self.max_url_length:
            return False, f"URL exceeds maximum length of {self.max_url_length}"
            
        # Check for malicious patterns
        if self._contains_malicious_patterns(url):
            return False, "URL contains potentially malicious patterns"
            
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Failed to parse URL: {str(e)}"
            
        # Validate scheme
        if not parsed.scheme:
            return False, "URL missing scheme (http/https)"
            
        if parsed.scheme.lower() in self.BLOCKED_SCHEMES:
            return False, f"Blocked scheme: {parsed.scheme}"
            
        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            return False, f"Only http/https schemes allowed, got: {parsed.scheme}"
            
        # Validate hostname
        if not parsed.netloc:
            return False, "URL missing hostname"
            
        # Check for blocked domains
        hostname = parsed.hostname
        if hostname and hostname.lower() in self.blocked_domains:
            return False, f"Domain is blocked: {hostname}"
            
        # Check for private IPs
        if not self.allow_private_ips and self._is_private_ip(hostname):
            return False, "Private IP addresses are not allowed"
            
        return True, "Valid URL"
        
    def normalize_url(self, url: str, base_url: Optional[str] = None) -> str:
        """
        Normalize URL by resolving relative paths and cleaning up.
        
        Args:
            url: URL to normalize
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Normalized URL
        """
        # Handle relative URLs
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
            
        parsed = urlparse(url)
        
        # Normalize components
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or '/'
        
        # Remove default ports
        if ':80' in netloc and scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and scheme == 'https':
            netloc = netloc.replace(':443', '')
            
        # Rebuild URL
        normalized = urllib.parse.urlunparse((
            scheme, netloc, path, parsed.params, 
            parsed.query, parsed.fragment
        ))
        
        return normalized
        
    def extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain string or None if invalid
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() if parsed.netloc else None
        except:
            return None
            
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """
        Check if two URLs belong to the same domain.
        
        Args:
            url1: First URL
            url2: Second URL
            
        Returns:
            True if same domain, False otherwise
        """
        domain1 = self.extract_domain(url1)
        domain2 = self.extract_domain(url2)
        return domain1 is not None and domain1 == domain2
        
    def _contains_malicious_patterns(self, url: str) -> bool:
        """Check for common malicious URL patterns."""
        malicious_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'<script',
            r'%3Cscript',
            r'onload=',
            r'onerror=',
        ]
        
        url_lower = url.lower()
        return any(re.search(pattern, url_lower) for pattern in malicious_patterns)
        
    def _is_private_ip(self, hostname: str) -> bool:
        """Check if hostname is a private IP address."""
        if not hostname:
            return False
            
        try:
            # Try to parse as IP address
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            # Not an IP address, check if it resolves to private IP
            pass
            
        # Check against private IP patterns
        return any(re.match(pattern, hostname) for pattern in self.PRIVATE_IP_PATTERNS)


def validate_url(url: str, **kwargs) -> Tuple[bool, str]:
    """
    Convenience function to validate a single URL.
    
    Args:
        url: URL to validate
        **kwargs: Additional arguments for URLValidator
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = URLValidator(**kwargs)
    return validator.is_valid_url(url)


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    Convenience function to normalize a URL.
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative resolution
        
    Returns:
        Normalized URL
    """
    validator = URLValidator()
    return validator.normalize_url(url, base_url)


# Example usage
if __name__ == "__main__":
    validator = URLValidator()
    
    test_urls = [
        "https://example.com",
        "http://localhost/test",
        "javascript:alert('xss')",
        "https://192.168.1.1/admin",
        "relative/path",
        "https://example.com/../../../etc/passwd",
    ]
    
    print("URL Validation Tests:")
    for url in test_urls:
        is_valid, message = validator.is_valid_url(url)
        print(f"URL: {url}")
        print(f"Valid: {is_valid}, Message: {message}")
        if is_valid:
            normalized = validator.normalize_url(url, "https://example.com")
            print(f"Normalized: {normalized}")
        print("-" * 50)