import asyncio
import ssl
import socket
import aiohttp
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import json
import re

# Browser manager for getting browser instances
from utils.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class SecurityAnalyzer:
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.timeout = 30  # Maximum time for security checks
        # Security scoring weights
        self.scoring_weights = {
            "ssl_score": 0.30,        # SSL certificate and configuration
            "headers_score": 0.25,    # Security headers
            "https_score": 0.20,      # HTTPS implementation
            "cookie_score": 0.15,     # Cookie security
            "content_score": 0.10     # Content security policies
        }
        self.security_headers = {
            "strict-transport-security": {
                "name": "HTTP Strict Transport Security (HSTS)",
                "importance": "critical",
                "description": "Forces browsers to use HTTPS connections"
            },
            "content-security-policy": {
                "name": "Content Security Policy (CSP)",
                "importance": "high",
                "description": "Prevents XSS and injection attacks"
            },
            "x-frame-options": {
                "name": "X-Frame-Options",
                "importance": "high", 
                "description": "Prevents clickjacking attacks"
            },
            "x-content-type-options": {
                "name": "X-Content-Type-Options",
                "importance": "medium",
                "description": "Prevents MIME type sniffing attacks"
            },
            "x-xss-protection": {
                "name": "X-XSS-Protection",
                "importance": "medium",
                "description": "Enables browser XSS filtering"
            },
            "referrer-policy": {
                "name": "Referrer Policy",
                "importance": "medium",
                "description": "Controls referrer information sharing"
            },
            "permissions-policy": {
                "name": "Permissions Policy",
                "importance": "low",
                "description": "Controls browser feature access"
            }
        }
        
        logger.info("SecurityAnalyzer initialized")
    
    async def _test_basic_connectivity(self, url: str) -> Dict[str, Any]:
        """Test basic connectivity to the domain"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    return {
                        "connected": True,
                        "status_code": response.status,
                        "can_fetch_content": response.status < 500
                    }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "can_fetch_content": False
            }
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        logger.info(f"Starting security analysis for: {url}")
        start_time = time.time()
        
        try:
            # Parse URL for analysis
            parsed_url = urlparse(url)
            domain = parsed_url.netloc or parsed_url.path
            
            # Test basic connectivity first
            connectivity = await self._test_basic_connectivity(url)
            
            # Run all analyses concurrently with proper error handling
            ssl_analysis, headers_analysis, https_analysis, cookie_analysis = await asyncio.gather(
                self._analyze_ssl_certificate(domain, url),
                self._analyze_security_headers(url),
                self._analyze_https_implementation(url),
                self._analyze_cookie_security(url),
                return_exceptions=True
            )
            
            # Handle exceptions in concurrent operations
            ssl_analysis = ssl_analysis if not isinstance(ssl_analysis, Exception) else self._create_failed_ssl_analysis(str(ssl_analysis))
            headers_analysis = headers_analysis if not isinstance(headers_analysis, Exception) else self._create_failed_headers_analysis(str(headers_analysis))
            https_analysis = https_analysis if not isinstance(https_analysis, Exception) else self._create_failed_https_analysis(str(https_analysis))
            cookie_analysis = cookie_analysis if not isinstance(cookie_analysis, Exception) else self._create_failed_cookie_analysis(str(cookie_analysis))
            
            # **CRITICAL FIX**: Check for SSL connection issues and cascade failures
            ssl_connection_failed = self._is_ssl_connection_failure(ssl_analysis)
            
            if ssl_connection_failed and not connectivity.get("can_fetch_content", False):
                # If SSL failed and basic connectivity also failed, cascade the failure
                logger.warning(f"SSL connection failed and basic connectivity issues detected for {url}")
                headers_analysis = self._create_failed_headers_analysis("Connection failed - cannot reach server")
                cookie_analysis = self._create_failed_cookie_analysis("Connection failed - cannot reach server")
                https_analysis = self._create_failed_https_analysis("Connection failed - cannot reach server")
                
                # Set very low content score for failed connection
                csp_analysis = self._create_failed_csp_analysis("Connection failed - cannot reach server")
            else:
                # Analyze content security policies - run separately due to potential browser dependency
                try:
                    csp_analysis = await self._analyze_content_security_enhanced(url)
                    
                    # If SSL failed but other analyses succeeded, reduce their reliability
                    if ssl_connection_failed:
                        headers_analysis = self._reduce_analysis_confidence(headers_analysis, "SSL connection issues detected")
                        cookie_analysis = self._reduce_analysis_confidence(cookie_analysis, "SSL connection issues detected")
                        
                except Exception as e:
                    logger.warning(f"Content security analysis failed: {e}")
                    csp_analysis = self._create_failed_csp_analysis(str(e))
            
            # Calculate individual scores
            ssl_score = self._calculate_ssl_score(ssl_analysis)
            headers_score = self._calculate_headers_score(headers_analysis)
            https_score = self._calculate_https_score(https_analysis)
            cookie_score = self._calculate_cookie_score(cookie_analysis)
            content_score = self._calculate_content_security_score(csp_analysis)
            
            # Calculate overall security score
            overall_score = self._calculate_overall_score(
                ssl_score, headers_score, https_score, cookie_score, content_score
            )
            
            # Identify vulnerabilities and issues
            vulnerabilities = self._identify_vulnerabilities(
                ssl_analysis, headers_analysis, https_analysis, cookie_analysis, csp_analysis
            )
            
            recommendations = self._generate_security_recommendations(
                ssl_analysis, headers_analysis, https_analysis, cookie_analysis, csp_analysis, overall_score
            )
            
            analysis_time = time.time() - start_time
            
            results = {
                "score": overall_score,
                "grade": self._get_grade_from_score(overall_score),
                
                # Core security status
                "ssl_status": ssl_analysis,
                "https_redirect": https_analysis.get("redirect_working", False),
                "security_headers": headers_analysis,
                
                # Detailed analysis results
                "ssl_analysis": ssl_analysis,
                "headers_analysis": headers_analysis,
                "https_analysis": https_analysis,
                "cookie_analysis": cookie_analysis,
                "content_security_analysis": csp_analysis,
                
                # Security scoring breakdown
                "score_breakdown": {
                    "ssl_score": ssl_score,
                    "headers_score": headers_score,
                    "https_score": https_score,
                    "cookie_score": cookie_score,
                    "content_score": content_score
                },
                "vulnerabilities": vulnerabilities,
                "recommendations": recommendations,
                "security_level": self._get_security_level(overall_score),
                
                # Metadata
                "analysis_duration": analysis_time,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "analyzer_version": "1.0.0",
                "connectivity_info": connectivity  # Add connectivity info for debugging
            }
            
            logger.info(f"Security analysis completed. Score: {overall_score}/100, Level: {results['security_level']}")
            return results
            
        except Exception as e:
            logger.error(f"Security analysis failed for {url}: {e}")
            return self._create_error_result(url, str(e), time.time() - start_time)

    def _is_ssl_connection_failure(self, ssl_analysis: Dict[str, Any]) -> bool:
        """Check if SSL analysis indicates a connection failure"""
        if not ssl_analysis.get("certificate_found", True):
            error = ssl_analysis.get("error", "").lower()
            return any(keyword in error for keyword in ["timeout", "connection", "dns", "network"])
        return False
    
    def _reduce_analysis_confidence(self, analysis: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Reduce confidence in analysis results due to connection issues"""
        if "error" not in analysis:
            # Reduce scores by 50% if there were connection issues
            if "headers_score" in analysis:
                analysis["headers_score"] = max(0, analysis["headers_score"] // 2)
                analysis["confidence_warning"] = f"Reduced confidence: {reason}"
            
            if "cookie_security_score" in analysis:
                analysis["cookie_security_score"] = max(0, analysis["cookie_security_score"] // 2)
                analysis["confidence_warning"] = f"Reduced confidence: {reason}"
        
        return analysis

    async def _analyze_ssl_certificate(self, domain: str, url: str) -> Dict[str, Any]:
        try:
            clean_domain = domain.split(':')[0]  # Remove port if present
            logger.info(f"Analyzing SSL certificate for domain: {clean_domain}")
            
            context = ssl.create_default_context()
        
            # Connect and get certificate with shorter timeout for faster failure detection
            with socket.create_connection((clean_domain, 443), timeout=8) as sock:
                with context.wrap_socket(sock, server_hostname=clean_domain) as secure_sock:
                    cert = secure_sock.getpeercert()
                    cipher = secure_sock.cipher()
                    version = secure_sock.version()
        
            if not cert:
                logger.warning(f"No certificate received for {clean_domain}")
                return {
                    "certificate_found": False,
                    "error": "No certificate received",
                    "domain": clean_domain,
                    "is_valid": False,
                    "security_issues": ["No certificate received"],
                    "security_warnings": [],
                }
        
            # Parse certificate information
            ssl_info = {
                "certificate_found": True,
                "domain": clean_domain,
                "subject": dict(x[0] for x in cert.get('subject', [])),
                "issuer": dict(x[0] for x in cert.get('issuer', [])),
                "version": cert.get('version', 'Unknown'),
                "serial_number": cert.get('serialNumber', 'Unknown'),
                "not_before": cert.get('notBefore', ''),
                "not_after": cert.get('notAfter', ''),
                "signature_algorithm": cert.get('signatureAlgorithm', 'Unknown'),
                "tls_version": version,
                "cipher_suite": cipher[0] if cipher else 'Unknown',
                "key_size": cipher[2] if cipher and len(cipher) > 2 else 0
            }
        
            # Check certificate validity
            validity_info = self._check_certificate_validity(cert)
            ssl_info.update(validity_info)
        
            # Check for security issues
            security_info = self._check_ssl_security_issues(ssl_info)
            ssl_info.update(security_info)
        
            logger.info(f"SSL analysis completed for {clean_domain}. Valid: {ssl_info.get('is_valid', False)}")
            return ssl_info
        
        except ssl.SSLError as e:
            logger.warning(f"SSL error for {domain}: {e}")
            return {
                "certificate_found": False,
                "ssl_error": str(e),
                "domain": domain,
                "is_valid": False,
                "days_until_expiry": 0,
                "expiry_status": "error",
                "security_issues": [f"SSL connection failed: {str(e)}"],
                "security_warnings": [],
                "issue": "SSL connection failed",
                "recommendation": "Fix SSL certificate configuration",
                "error": f"SSL connection failed: {str(e)}"  # Add for detection
            }
        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed for {domain}: {e}")
            return {
                "certificate_found": False,
                "error": f"DNS resolution failed: {str(e)}",
                "domain": domain,
                "is_valid": False,
                "days_until_expiry": 0,
                "expiry_status": "error",
                "security_issues": [f"Cannot resolve domain: {domain}"],
                "security_warnings": [],
                "issue": "DNS resolution failed",
                "recommendation": "Check domain name and DNS configuration"
            }
        except socket.timeout as e:
            logger.warning(f"Connection timeout for {domain}: {e}")
            return {
                "certificate_found": False,
                "error": f"Connection timeout: {str(e)}",
                "domain": domain,
                "is_valid": False,
                "days_until_expiry": 0,
                "expiry_status": "error",
                "security_issues": ["Connection timeout"],
                "security_warnings": [],
                "issue": "Connection timeout",
                "recommendation": "Check if server is accessible on port 443"
            }
        except Exception as e:
            logger.error(f"Unexpected error analyzing SSL for {domain}: {e}")
            return {
                "certificate_found": False,
                "error": str(e),
                "domain": domain,
                "is_valid": False,
                "days_until_expiry": 0,
                "expiry_status": "error",
                "security_issues": [f"SSL analysis failed: {str(e)}"],
                "security_warnings": [],
                "issue": "Unable to analyze SSL certificate",
                "recommendation": "Manual SSL certificate review recommended"
            }

    def _check_certificate_validity(self, cert: Dict) -> Dict[str, Any]:
        try:
            # Updated date formats to handle various certificate date formats
            date_formats = [
                '%b %d %H:%M:%S %Y %Z',     # Standard format
                '%b %d %H:%M:%S %Y GMT',    # GMT timezone
                '%b %d %H:%M:%S %Y UTC',    # UTC timezone
                '%b  %d %H:%M:%S %Y %Z',    # Double space for single digit days
                '%b  %d %H:%M:%S %Y GMT',   # Double space with GMT
                '%b  %d %H:%M:%S %Y UTC',   # Double space with UTC
                '%Y%m%d%H%M%SZ',            # ASN.1 format
                '%Y-%m-%d %H:%M:%S'         # ISO-like format
            ]
    
            not_before_str = cert.get('notBefore', '')
            not_after_str = cert.get('notAfter', '')
        
            if not not_before_str or not not_after_str:
                return {
                    "is_valid": False,
                    "days_until_expiry": 0,
                    "expiry_status": "unknown",
                    "error": "Certificate dates not found"
                }
    
            not_before = None
            not_after = None
    
            # Try parsing with different date formats
            for date_format in date_formats:
                try:
                    not_before = datetime.strptime(not_before_str, date_format)
                    not_after = datetime.strptime(not_after_str, date_format)
                    break
                except ValueError:
                    continue
    
            if not_before is None or not_after is None:
                logger.warning(f"Could not parse certificate dates: {not_before_str}, {not_after_str}")
                return {
                    "is_valid": False,
                    "days_until_expiry": 0,
                    "expiry_status": "unknown",
                    "error": f"Could not parse certificate dates"
                }
    
            # Ensure timezone awareness
            if not_before.tzinfo is None:
                not_before = not_before.replace(tzinfo=timezone.utc)
            if not_after.tzinfo is None:
                not_after = not_after.replace(tzinfo=timezone.utc)
    
            now = datetime.now(timezone.utc)
            is_valid = not_before <= now <= not_after
            days_until_expiry = (not_after - now).days
        
            # Determine expiry status
            if days_until_expiry < 0:
                expiry_status = "expired"
            elif days_until_expiry < 30:
                expiry_status = "expiring_soon"
            elif days_until_expiry < 90:
                expiry_status = "renewal_recommended"
            else:
                expiry_status = "valid"
    
            return {
                "is_valid": is_valid,
                "days_until_expiry": days_until_expiry,
                "expiry_status": expiry_status,
                "expires_on": not_after.isoformat(),
                "issued_on": not_before.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error checking certificate validity: {e}")
            return {
                "is_valid": False,
                "days_until_expiry": 0,
                "expiry_status": "unknown",
                "error": f"Certificate validation error: {str(e)}"
            }
        
    def _check_ssl_security_issues(self, ssl_info: Dict) -> Dict[str, Any]:
        issues = []
        warnings = []
        
        # Check TLS version
        tls_version = ssl_info.get('tls_version', '')
        if tls_version in ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1']:
            issues.append(f"Outdated TLS version: {tls_version}")
        elif tls_version == 'TLSv1.2':
            warnings.append("Consider upgrading to TLS 1.3 for better security")
        
        # Check key size
        key_size = ssl_info.get('key_size', 0)
        if key_size > 0:  # Only check if we have key size info
            if key_size < 2048:
                issues.append(f"Weak key size: {key_size} bits (minimum 2048 recommended)")
            elif key_size < 4096:
                warnings.append("Consider using 4096-bit keys for enhanced security")
        
        # Check signature algorithm
        sig_algo = ssl_info.get('signature_algorithm', '').lower()
        if 'sha1' in sig_algo:
            issues.append("Weak signature algorithm: SHA-1 is deprecated")
        elif 'md5' in sig_algo:
            issues.append("Very weak signature algorithm: MD5 is insecure")
        
        # Check certificate expiry
        expiry_status = ssl_info.get('expiry_status', 'unknown')
        if expiry_status == 'expired':
            issues.append("SSL certificate has expired")
        elif expiry_status == 'expiring_soon':
            warnings.append("SSL certificate expires soon")
        
        return {
            "security_issues": issues,
            "security_warnings": warnings,
            "security_score": max(0, 100 - len(issues) * 25 - len(warnings) * 10)
        }
    
    def _calculate_ssl_score(self, ssl_analysis: Dict) -> int:
        """Calculate SSL security score"""
        if not ssl_analysis.get("certificate_found", False):
            return 0
        
        if not ssl_analysis.get("is_valid", False):
            return 10  # Certificate found but invalid
        
        # Start with full score for valid certificate
        score = 100
        
        # Deduct for security issues and warnings
        security_issues = ssl_analysis.get("security_issues", [])
        security_warnings = ssl_analysis.get("security_warnings", [])
        
        score -= len(security_issues) * 20  # -20 points per security issue (was 25)
        score -= len(security_warnings) * 5   # -5 points per warning (was 10)
        
        # Check certificate expiry
        days_until_expiry = ssl_analysis.get("days_until_expiry", 365)
        if days_until_expiry < 0:
            score -= 50  # Certificate expired
        elif days_until_expiry < 30:
            score -= 15  # Expiring soon (reduced penalty)
        elif days_until_expiry < 90:
            score -= 5   # Should renew soon (reduced penalty)
        
        return max(0, min(100, score))
    
    def _get_header_value(self, headers: Dict[str, str], header_name: str) -> Optional[str]:
        """Helper method to get header value with case-insensitive matching"""
        for key, value in headers.items():
            if key.lower() == header_name.lower():
                return value
        return None

    def _analyze_header_value(self, header_key: str, header_value: str) -> Dict[str, Any]:
        """Analyze specific header value for security issues"""
        analysis = {
            "secure": True,
            "issues": [],
            "recommendations": []
        }
        
        if header_key.lower() == "strict-transport-security":
            # Check HSTS configuration
            if "max-age" not in header_value.lower():
                analysis["issues"].append("Missing max-age directive")
                analysis["secure"] = False
            else:
                # Extract max-age value
                max_age_match = re.search(r'max-age=(\d+)', header_value.lower())
                if max_age_match:
                    max_age = int(max_age_match.group(1))
                    if max_age < 31536000:  # 1 year
                        analysis["recommendations"].append(f"Consider longer max-age (current: {max_age}s)")
            
            if "includesubdomains" not in header_value.lower():
                analysis["recommendations"].append("Consider adding includeSubDomains")
                
        elif header_key.lower() == "content-security-policy":
            # Check CSP configuration
            if "unsafe-inline" in header_value.lower():
                analysis["issues"].append("Uses unsafe-inline which reduces security")
                analysis["secure"] = False
            if "unsafe-eval" in header_value.lower():
                analysis["issues"].append("Uses unsafe-eval which reduces security")
                analysis["secure"] = False
                
        elif header_key.lower() == "x-frame-options":
            # Check X-Frame-Options value
            if header_value.upper() not in ["DENY", "SAMEORIGIN"]:
                if not header_value.upper().startswith("ALLOW-FROM"):
                    analysis["issues"].append("Invalid X-Frame-Options value")
                    analysis["secure"] = False
                    
        return analysis

    async def _analyze_security_headers(self, url: str) -> Dict[str, Any]:
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    headers = dict(response.headers)
                    status_code = response.status
        
            # Analyze each security header with case-insensitive matching
            header_analysis = {}
            missing_headers = []
            present_headers = []
        
            for header_key, header_info in self.security_headers.items():
                header_value = self._get_header_value(headers, header_key)
            
                if header_value:
                    present_headers.append(header_key)
                    header_analysis[header_key] = {
                        "present": True,
                        "value": header_value,
                        "name": header_info["name"],
                        "analysis": self._analyze_header_value(header_key, header_value)
                    }
                else:
                    missing_headers.append(header_key)
                    header_analysis[header_key] = {
                        "present": False,
                        "name": header_info["name"],
                        "importance": header_info["importance"],
                        "description": header_info["description"]
                    }
        
            # Calculate headers score with better weighting
            critical_present = sum(1 for h in present_headers if self.security_headers[h]["importance"] == "critical")
            high_present = sum(1 for h in present_headers if self.security_headers[h]["importance"] == "high")
            medium_present = sum(1 for h in present_headers if self.security_headers[h]["importance"] == "medium")
            low_present = sum(1 for h in present_headers if self.security_headers[h]["importance"] == "low")

            critical_total = sum(1 for h in self.security_headers.values() if h["importance"] == "critical")
            high_total = sum(1 for h in self.security_headers.values() if h["importance"] == "high")
            medium_total = sum(1 for h in self.security_headers.values() if h["importance"] == "medium")
            low_total = sum(1 for h in self.security_headers.values() if h["importance"] == "low")
        
            # Improved scoring formula
            critical_score = (critical_present / max(1, critical_total)) * 40
            high_score = (high_present / max(1, high_total)) * 30
            medium_score = (medium_present / max(1, medium_total)) * 20
            low_score = (low_present / max(1, low_total)) * 10
            
            headers_score = critical_score + high_score + medium_score + low_score
        
            # Check for dangerous headers with case-insensitive matching
            dangerous_headers = self._check_dangerous_headers(headers)
        
            return {
                "status_code": status_code,
                "total_headers_checked": len(self.security_headers),
                "present_headers": len(present_headers),
                "missing_headers": len(missing_headers),
                "headers_score": min(100, round(headers_score)),
                "header_details": header_analysis,
                "missing_critical_headers": [h for h in missing_headers if self.security_headers[h]["importance"] == "critical"],
                "dangerous_headers": dangerous_headers,
                "raw_headers": {k: v for k, v in headers.items() if k.lower().startswith(('x-', 'content-security', 'strict-transport', 'referrer-policy', 'permissions-policy'))}
            }
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout analyzing headers for {url}")
            return {"error": "Request timeout", "headers_score": 0}
        except Exception as e:
            logger.warning(f"Failed to analyze headers for {url}: {e}")
            return {"error": str(e), "headers_score": 0}

    def _check_dangerous_headers(self, headers: Dict[str, str]) -> List[str]:
        dangerous = []
    
        # Headers that reveal server information - case insensitive
        info_headers = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]
        for header in info_headers:
            value = self._get_header_value(headers, header)
            if value:
                dangerous.append(f"Information disclosure: {header} header present")
    
        return dangerous
    
    async def _analyze_https_implementation(self, url: str) -> Dict[str, Any]:
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc or parsed_url.path
            
            # Test HTTP to HTTPS redirect
            http_url = f"http://{domain}"
            https_url = f"https://{domain}"
            
            redirect_test = await self._test_https_redirect(http_url, https_url)
            
            # Test HTTPS connection strength
            https_strength = await self._test_https_strength(https_url)
            
            # Check for mixed content risk (simplified version)
            mixed_content_risk = await self._check_mixed_content_risk(url)
            
            return {
                "original_url": url,
                "uses_https": parsed_url.scheme == "https",
                "redirect_working": redirect_test["redirect_working"],
                "redirect_status": redirect_test["status_code"],
                "redirect_chain": redirect_test["redirect_chain"],
                "https_strength": https_strength,
                "mixed_content_risk": mixed_content_risk
            }
            
        except Exception as e:
            logger.warning(f"Failed to analyze HTTPS implementation for {url}: {e}")
            return {
                "error": str(e),
                "uses_https": False,
                "redirect_working": False,
                "mixed_content_risk": {"mixed_content_found": False}
            }
    
    async def _test_https_redirect(self, http_url: str, https_url: str) -> Dict[str, Any]:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(http_url, allow_redirects=False) as response:
                    status_code = response.status
                    location = response.headers.get('Location', '')
                    
                    # Check for redirect to HTTPS
                    if status_code in [301, 302, 303, 307, 308]:
                        if location.startswith('https://'):
                            return {
                                "redirect_working": True,
                                "status_code": status_code,
                                "redirect_chain": [http_url, location]
                            }
                    
                    return {
                        "redirect_working": False,
                        "status_code": status_code,
                        "redirect_chain": [http_url]
                    }
                    
        except Exception as e:
            logger.debug(f"HTTPS redirect test failed: {e}")
            return {
                "redirect_working": False,
                "status_code": 0,
                "redirect_chain": [],
                "error": str(e)
            }
    
    async def _test_https_strength(self, https_url: str) -> Dict[str, Any]:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(https_url) as response:
                    return {
                        "connection_successful": True,
                        "status_code": response.status,
                        "protocol_version": "HTTP/2" if hasattr(response, 'version') and response.version.major == 2 else "HTTP/1.1"
                    }
                    
        except ssl.SSLError as e:
            return {
                "connection_successful": False,
                "ssl_error": str(e),
                "issue": "SSL connection failed"
            }
        except Exception as e:
            return {
                "connection_successful": False,
                "error": str(e)
            }
    
    async def _check_mixed_content_risk(self, url: str) -> Dict[str, Any]:
        """Simplified mixed content check without browser dependency"""
        try:
            # If not HTTPS, no mixed content risk
            if not url.startswith('https://'):
                return {
                    "mixed_content_found": False,
                    "mixed_content_issues": [],
                    "risk_level": "low"
                }
            
            # Basic check - fetch page content and look for http:// resources
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Simple regex search for mixed content
                        mixed_content_issues = []
                        
                        # Check for HTTP resources in HTTPS page
                        if re.search(r'src=["\']http://', content):
                            mixed_content_issues.append('HTTP resources found in src attributes')
                        
                        if re.search(r'href=["\']http://', content):
                            mixed_content_issues.append('HTTP resources found in href attributes')
                        
                        return {
                            "mixed_content_found": len(mixed_content_issues) > 0,
                            "mixed_content_issues": mixed_content_issues,
                            "risk_level": "high" if mixed_content_issues else "low"
                        }
            
            return {
                "mixed_content_found": False,
                "mixed_content_issues": [],
                "risk_level": "unknown"
            }
                
        except Exception as e:
            logger.debug(f"Mixed content check failed: {e}")
            return {
                "mixed_content_found": False,
                "mixed_content_issues": [],
                "risk_level": "unknown",
                "error": str(e)
            }
    
    async def _analyze_cookie_security(self, url: str) -> Dict[str, Any]:
        """
        Analyze cookie security settings using HTTP headers instead of browser
        """
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    # Get Set-Cookie headers
                    set_cookie_headers = response.headers.getall('Set-Cookie')
                    
                    if not set_cookie_headers:
                        return {
                            "cookies_found": False,
                            "total_cookies": 0,
                            "secure_cookies": 0,
                            "httponly_cookies": 0,
                            "samesite_cookies": 0,
                            "cookie_security_score": 100  # No cookies = no cookie security issues
                        }
                    
                    # Analyze each cookie
                    total_cookies = len(set_cookie_headers)
                    secure_count = 0
                    httponly_count = 0
                    samesite_count = 0
                    insecure_cookies = []
                    
                    for cookie_header in set_cookie_headers:
                        cookie_lower = cookie_header.lower()
                        
                        # Extract cookie name
                        cookie_name = cookie_header.split('=')[0] if '=' in cookie_header else 'unknown'
                        
                        # Check security flags
                        has_secure = 'secure' in cookie_lower
                        has_httponly = 'httponly' in cookie_lower
                        has_samesite = 'samesite=' in cookie_lower
                        
                        if has_secure:
                            secure_count += 1
                        if has_httponly:
                            httponly_count += 1
                        if has_samesite:
                            samesite_count += 1
                        
                        # Check for sensitive cookies without security flags
                        if any(sensitive in cookie_name.lower() for sensitive in ['session', 'auth', 'login', 'token', 'csrf']):
                            issues = []
                            if not has_secure:
                                issues.append('not secure')
                            if not has_httponly:
                                issues.append('not httpOnly')
                            if not has_samesite:
                                issues.append('no sameSite protection')
                            
                            if issues:
                                insecure_cookies.append({
                                    "name": cookie_name,
                                    "issues": issues
                                })
                    
                    return {
                        "cookies_found": True,
                        "total_cookies": total_cookies,
                        "secure_cookies": secure_count,
                        "httponly_cookies": httponly_count,
                        "samesite_cookies": samesite_count,
                        "insecure_sensitive_cookies": insecure_cookies,
                        "cookie_security_score": self._calculate_cookie_security_score(
                            total_cookies, secure_count, httponly_count, samesite_count, len(insecure_cookies)
                        )
                    }
                
        except Exception as e:
            logger.debug(f"Cookie security analysis failed: {e}")
            return {
                "cookies_found": False,
                "total_cookies": 0,
                "cookie_security_score": 50,  # Unknown state
                "error": str(e)
            }

    def _calculate_cookie_security_score(self, total: int, secure: int, httponly: int, samesite: int, insecure_sensitive: int) -> int:
        """Calculate cookie security score based on security flags"""
        if total == 0:
            return 100  # No cookies = no issues
        
        # Calculate percentages
        secure_pct = (secure / total) * 100
        httponly_pct = (httponly / total) * 100
        samesite_pct = (samesite / total) * 100
        
        # Base score from security flag adoption
        base_score = (secure_pct * 0.4 + httponly_pct * 0.3 + samesite_pct * 0.3)
        
        # Penalty for insecure sensitive cookies
        penalty = insecure_sensitive * 20  # -20 points per insecure sensitive cookie
        
        return max(0, min(100, round(base_score - penalty)))
    
    def _count_sri_usage(self, page_content: str) -> int:
        # Look for script and link tags with integrity attribute
        sri_pattern = r'<(?:script|link)[^>]*integrity\s*=\s*["\'][^"\']*["\'][^>]*>'
        matches = re.findall(sri_pattern, page_content, re.IGNORECASE)
        return len(matches)

    def _check_csrf_protection(self, page_content: str) -> str:
        csrf_patterns = [
            r'<input[^>]*name\s*=\s*["\']csrf[_-]?token["\'][^>]*>',
            r'<input[^>]*name\s*=\s*["\']_token["\'][^>]*>',
            r'<meta[^>]*name\s*=\s*["\']csrf[_-]?token["\'][^>]*>',
            r'csrfToken\s*[:=]\s*["\'][^"\']+["\']',
            r'_token\s*[:=]\s*["\'][^"\']+["\']'
        ]
    
        for pattern in csrf_patterns:
            if re.search(pattern, page_content, re.IGNORECASE):
                return "present"
    
        return "not_detected"

    async def _analyze_content_security_enhanced(self, url: str) -> Dict[str, Any]:
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    headers = dict(response.headers)
                    page_content = await response.text()
                    
                    # Add content size limit to prevent memory issues
                    if len(page_content) > 5_000_000:  # 5MB limit
                        page_content = page_content[:5_000_000]
                        logger.warning(f"Page content truncated for analysis: {url}")

            csp_header = self._get_header_value(headers, 'content-security-policy')
            csp_report_only_header = self._get_header_value(headers, 'content-security-policy-report-only')
        
            csp_implemented = bool(csp_header or csp_report_only_header)
        
            csp_analysis = {}
            if csp_header:
                csp_analysis = self._analyze_csp_directives(csp_header)
            elif csp_report_only_header:
                csp_analysis = self._analyze_csp_directives(csp_report_only_header)
                csp_analysis["report_only"] = True
        
            # Check for meta CSP tags
            meta_csp_count = self._count_meta_csp_usage(page_content)
            if meta_csp_count > 0 and not csp_implemented:
                csp_implemented = True
                csp_analysis = {
                    "meta_csp_found": True, 
                    "directives": {}, 
                    "issues": [], 
                    "recommendations": ["Consider using HTTP header instead of meta tag for better security"], 
                    "score": 60
                }
        
            # Analyze page content for security features
            sri_count = self._count_sri_usage(page_content)
            csrf_protection = self._check_csrf_protection(page_content)
            has_inline_scripts = self._check_inline_scripts(page_content)
            has_inline_styles = self._check_inline_styles(page_content)
        
            return {
                "csp_implemented": csp_implemented,
                "csp_header": csp_header,
                "csp_report_only_header": csp_report_only_header,
                "meta_csp_count": meta_csp_count,
                "csp_analysis": csp_analysis,
                "sri_usage": sri_count,
                "csrf_protection": csrf_protection,
                "has_inline_scripts": has_inline_scripts,
                "has_inline_styles": has_inline_styles,
                "content_security_score": 0  # Will be calculated separately
            }
        
        except Exception as e:
            logger.debug(f"Enhanced content security analysis failed: {e}")
            return {
                "csp_implemented": False,
                "sri_usage": 0,
                "csrf_protection": "unknown",
                "has_inline_scripts": False,
                "has_inline_styles": False,
                "error": str(e),
                "content_security_score": 20  # Minimal score for failed analysis
            }

    def _count_meta_csp_usage(self, page_content: str) -> int:
        meta_csp_pattern = r'<meta[^>]+http-equiv\s*=\s*["\']content-security-policy["\'][^>]*>'
        matches = re.findall(meta_csp_pattern, page_content, re.IGNORECASE)
        return len(matches)

    def _check_inline_scripts(self, page_content: str) -> bool:
        """Fixed regex pattern to avoid catastrophic backtracking"""
        try:
            # Simpler pattern that avoids nested quantifiers
            inline_script_pattern = r'<script(?![^>]*\bsrc\s*=)[^>]*>[\s\S]*?</script>'
            matches = re.findall(inline_script_pattern, page_content, re.IGNORECASE)
            return len(matches) > 0
        except Exception as e:
            logger.warning(f"Error checking inline scripts: {e}")
            return False

    def _check_inline_styles(self, page_content: str) -> bool:
        """Check for inline styles with improved error handling"""
        try:
            # Check for style tags
            style_pattern = r'<style[^>]*>[\s\S]*?</style>'
            style_matches = re.findall(style_pattern, page_content, re.IGNORECASE)
        
            # Check for inline style attributes
            inline_style_pattern = r'\bstyle\s*=\s*["\'][^"\']*["\']'
            inline_style_matches = re.findall(inline_style_pattern, page_content, re.IGNORECASE)
        
            return len(style_matches) > 0 or len(inline_style_matches) > 0
        except Exception as e:
            logger.warning(f"Error checking inline styles: {e}")
            return False

    def _calculate_content_security_score(self, csp_analysis: Dict) -> int:
        score = 40  # Base score for any website
    
        if csp_analysis.get("csp_implemented", False):
            score += 40

            csp_details = csp_analysis.get("csp_analysis", {})
            if isinstance(csp_details, dict):
                csp_score = csp_details.get("score", 0)
                score += min(20, csp_score // 5)
        else:
            # No CSP - check for other security measures
            if csp_analysis.get("has_inline_scripts", False):
                score -= 15  # Penalty for inline scripts without CSP
            if csp_analysis.get("has_inline_styles", False):
                score -= 5   # Penalty for inline styles without CSP
                
        sri_usage = csp_analysis.get("sri_usage", 0)
        if sri_usage > 0:
            score += min(15, sri_usage * 3)  # Up to 15 points for SRI usage
    
        # Points for CSRF protection
        csrf_protection = csp_analysis.get("csrf_protection", "unknown")
        if csrf_protection == "present":
            score += 10
        elif csrf_protection == "not_detected":
            score -= 5  # Small penalty for no CSRF protection
    
        # Ensure score is within bounds
        return max(0, min(100, score))

    def _analyze_csp_directives(self, csp_header: str) -> Dict[str, Any]:
        directives = {}
        issues = []
        recommendations = []
    
        # Parse directives
        for directive in csp_header.split(';'):
            directive = directive.strip()
            if directive:
                parts = directive.split()
                if parts:
                    directive_name = parts[0]
                    directive_values = parts[1:] if len(parts) > 1 else []
                    directives[directive_name] = directive_values

        for directive, values in directives.items():
            if "'unsafe-inline'" in values:
                issues.append(f"{directive} allows unsafe-inline")
            if "'unsafe-eval'" in values:
                issues.append(f"{directive} allows unsafe-eval")
            if "*" in values:
                issues.append(f"{directive} uses wildcard (*) - too permissive")
            if "data:" in values and directive in ["script-src", "object-src"]:
                issues.append(f"{directive} allows data: URIs which can be risky")

        # Check for missing important directives
        important_directives = ['default-src', 'script-src', 'style-src', 'img-src', 'connect-src', 'font-src']
        missing_directives = []
        for directive in important_directives:
            if directive not in directives:
                missing_directives.append(directive)
    
        if missing_directives:
            if len(missing_directives) == len(important_directives):
                recommendations.append("Add basic CSP directives: default-src, script-src, style-src")
            else:
                recommendations.append(f"Consider adding missing directives: {', '.join(missing_directives[:3])}")

        # Check for good practices
        if 'default-src' in directives:
            if "'self'" in directives['default-src']:
                # Good practice
                pass
            elif "'none'" in directives['default-src']:
                # Very restrictive but good
                pass
            else:
                recommendations.append("Consider using 'self' or 'none' in default-src")

        # Calculate CSP quality score
        quality_score = 100
        quality_score -= len(issues) * 15  # -15 points per issue
        quality_score -= len(missing_directives) * 5  # -5 points per missing directive
    
        # Bonus points for having strict directives
        if "'none'" in directives.get('object-src', []):
            quality_score += 5
        if "'self'" in directives.get('default-src', []):
            quality_score += 5

        return {
            "directives": directives,
            "issues": issues,
            "recommendations": recommendations,
            "missing_directives": missing_directives,
            "score": max(0, min(100, quality_score))
        }

    def _calculate_headers_score(self, headers_analysis: Dict) -> int:
        return headers_analysis.get("headers_score", 0)
    
    def _calculate_https_score(self, https_analysis: Dict) -> int:
        score = 0
        
        # Base points for using HTTPS
        if https_analysis.get("uses_https", False):
            score += 50
        
        # Points for HTTP to HTTPS redirect
        if https_analysis.get("redirect_working", False):
            score += 30
        
        # Points for HTTPS connection strength
        https_strength = https_analysis.get("https_strength", {})
        if https_strength.get("connection_successful", False):
            score += 15
        
        # Deduct for mixed content
        mixed_content = https_analysis.get("mixed_content_risk", {})
        if mixed_content.get("mixed_content_found", False):
            score -= 20
        
        return max(0, min(100, score))
    
    def _calculate_cookie_score(self, cookie_analysis: Dict) -> int:
        """Calculate cookie security score"""
        return cookie_analysis.get("cookie_security_score", 50)

    def _calculate_overall_score(self, ssl_score: int, headers_score: int, https_score: int, cookie_score: int, content_score: int) -> int:
        weighted_score = (
            ssl_score * self.scoring_weights["ssl_score"] +
            headers_score * self.scoring_weights["headers_score"] +
            https_score * self.scoring_weights["https_score"] +
            cookie_score * self.scoring_weights["cookie_score"] +
            content_score * self.scoring_weights["content_score"]
        )
        
        return max(0, min(100, round(weighted_score)))
    
    def _identify_vulnerabilities(self, ssl_analysis: Dict, headers_analysis: Dict,
                                https_analysis: Dict, cookie_analysis: Dict, 
                                csp_analysis: Dict) -> List[str]:
        vulnerabilities = []
        
        # Critical SSL vulnerabilities
        if not ssl_analysis.get("certificate_found", False):
            vulnerabilities.append("CRITICAL: No SSL certificate found - site is not secure")
        elif not ssl_analysis.get("is_valid", True):
            vulnerabilities.append("CRITICAL: SSL certificate is invalid or expired")
        
        # Check for outdated TLS
        security_issues = ssl_analysis.get("security_issues", [])
        for issue in security_issues:
            if "TLS" in issue or "SSL" in issue:
                vulnerabilities.append(f"HIGH: {issue}")
        
        # Critical header vulnerabilities
        missing_critical = headers_analysis.get("missing_critical_headers", [])
        for header in missing_critical:
            header_info = self.security_headers.get(header, {})
            vulnerabilities.append(f"HIGH: Missing {header_info.get('name', header)} - {header_info.get('description', 'Security risk')}")
        
        # HTTPS implementation issues
        if not https_analysis.get("uses_https", False):
            vulnerabilities.append("CRITICAL: Website does not use HTTPS")
        elif not https_analysis.get("redirect_working", False):
            vulnerabilities.append("HIGH: HTTP does not redirect to HTTPS")
        
        # Mixed content vulnerabilities
        mixed_content = https_analysis.get("mixed_content_risk", {})
        if mixed_content.get("mixed_content_found", False):
            vulnerabilities.append("HIGH: Mixed content detected - insecure resources on secure page")
        
        # Cookie security vulnerabilities
        insecure_cookies = cookie_analysis.get("insecure_sensitive_cookies", [])
        for cookie in insecure_cookies:
            vulnerabilities.append(f"MEDIUM: Sensitive cookie '{cookie['name']}' has security issues: {', '.join(cookie['issues'])}")
        
        # Information disclosure
        dangerous_headers = headers_analysis.get("dangerous_headers", [])
        for danger in dangerous_headers:
            vulnerabilities.append(f"LOW: {danger}")
        
        return vulnerabilities[:10]  # Return top 10 most critical
    
    def _generate_security_recommendations(self, ssl_analysis: Dict, headers_analysis: Dict,
                                         https_analysis: Dict, cookie_analysis: Dict,
                                         csp_analysis: Dict, overall_score: int) -> List[str]:
        recommendations = []
        
        # SSL/TLS recommendations (highest priority)
        if not ssl_analysis.get("certificate_found", False):
            recommendations.append("URGENT: Install an SSL certificate (use Let's Encrypt for free SSL)")
        elif not ssl_analysis.get("is_valid", True):
            recommendations.append("URGENT: Renew or fix your SSL certificate")
        else:
            # Certificate is valid, check for improvements
            expiry_status = ssl_analysis.get("expiry_status", "valid")
            if expiry_status in ["expiring_soon", "renewal_recommended"]:
                days = ssl_analysis.get("days_until_expiry", 0)
                recommendations.append(f"Renew SSL certificate (expires in {days} days)")
            
            # TLS version recommendations
            tls_version = ssl_analysis.get("tls_version", "")
            if tls_version in ["TLSv1", "TLSv1.1"]:
                recommendations.append("Upgrade to TLS 1.2 or 1.3 for better security")
            elif tls_version == "TLSv1.2":
                recommendations.append("Consider upgrading to TLS 1.3 for optimal security")
        
        # HTTPS implementation recommendations
        if not https_analysis.get("uses_https", False):
            recommendations.append("URGENT: Switch to HTTPS to protect user data")
        elif not https_analysis.get("redirect_working", False):
            recommendations.append("Set up automatic HTTP to HTTPS redirects")
        
        # Security headers recommendations (prioritized by importance)
        missing_headers = headers_analysis.get("missing_critical_headers", [])
        if "strict-transport-security" in missing_headers:
            recommendations.append("Add HTTP Strict Transport Security (HSTS) header")
        if "content-security-policy" in missing_headers:
            recommendations.append("Implement Content Security Policy (CSP) to prevent XSS attacks")
        if "x-frame-options" in missing_headers:
            recommendations.append("Add X-Frame-Options header to prevent clickjacking")

        # Cookie security recommendations
        insecure_cookies = cookie_analysis.get("insecure_sensitive_cookies", [])
        if insecure_cookies:
            recommendations.append("Secure sensitive cookies with Secure, HttpOnly, and SameSite flags")
        
        # Mixed content recommendations
        mixed_content = https_analysis.get("mixed_content_risk", {})
        if mixed_content.get("mixed_content_found", False):
            recommendations.append("Fix mixed content by using HTTPS for all resources")
        
        # Information disclosure recommendations
        dangerous_headers = headers_analysis.get("dangerous_headers", [])
        if dangerous_headers:
            recommendations.append("Remove server information headers to reduce information disclosure")
        
        # General recommendations based on score
        if overall_score < 50:
            recommendations.append("Consider conducting a professional security audit")
            recommendations.append("Implement a Web Application Firewall (WAF)")
        
        if overall_score < 70:
            recommendations.append("Enable security monitoring and logging")
            recommendations.append("Regularly update server software and dependencies")
        
        # Content Security Policy recommendations
        if not csp_analysis.get("csp_implemented", False):
            recommendations.append("Implement Subresource Integrity (SRI) for external scripts")
        
        return recommendations[:12]  # Return top 12 recommendations
    
    def _get_security_level(self, score: int) -> str:
        """Get security level description based on score"""
        if score >= 85:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"
    
    def _get_grade_from_score(self, score: int) -> str:
        """Convert numerical score to letter grade"""
        if score >= 85:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
    
    # Error handling helper methods
    def _create_failed_ssl_analysis(self, error: str) -> Dict[str, Any]:
        """Create failed SSL analysis result"""
        return {
            "certificate_found": False,
            "error": error,
            "is_valid": False,
            "security_issues": ["SSL analysis failed"],
            "security_warnings": [],
            "security_score": 0
        }
    
    def _create_failed_headers_analysis(self, error: str) -> Dict[str, Any]:
        """Create failed headers analysis result"""
        return {
            "error": error,
            "headers_score": 0,
            "missing_critical_headers": list(self.security_headers.keys()),
            "dangerous_headers": []
        }
    
    def _create_failed_https_analysis(self, error: str) -> Dict[str, Any]:
        """Create failed HTTPS analysis result"""
        return {
            "error": error,
            "uses_https": False,
            "redirect_working": False,
            "mixed_content_risk": {"mixed_content_found": False}
        }
    
    def _create_failed_cookie_analysis(self, error: str) -> Dict[str, Any]:
        """Create failed cookie analysis result"""
        return {
            "error": error,
            "cookies_found": False,
            "cookie_security_score": 0,
            "insecure_sensitive_cookies": []
        }
    
    def _create_failed_csp_analysis(self, error: str) -> Dict[str, Any]:
        return {
            "error": error,
            "csp_implemented": False,
            "sri_usage": 0,
            "csrf_protection": "unknown",
            "has_inline_scripts": False,
            "has_inline_styles": False
        }
    
    def _create_error_result(self, url: str, error_msg: str, analysis_time: float) -> Dict[str, Any]:
        """Create result when entire analysis fails"""
        return {
            "score": 0,
            "grade": "F",
            "ssl_status": {"certificate_found": False, "error": error_msg},
            "https_redirect": False,
            "security_headers": {"headers_score": 0},
            "vulnerabilities": [f"CRITICAL: Security analysis failed - {error_msg}"],
            "recommendations": [
                "Unable to analyze website security - check if URL is accessible",
                "Verify website is online and responding to requests",
                "Manual security review recommended"
            ],
            "security_level": "Critical",
            "analysis_duration": analysis_time,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "error": error_msg
        }

    def generate_security_report(self, analysis_results: Dict) -> str:
        """Generate a formatted security report"""
        report = f"""
WEBSITE SECURITY ANALYSIS REPORT
================================

Generated: {analysis_results['analyzed_at']}
URL: {analysis_results.get('analyzed_url', 'Unknown')}

OVERALL SECURITY ASSESSMENT
===========================
Overall Security Score: {analysis_results['score']}/100 ({analysis_results['grade']})
Security Level: {analysis_results['security_level']}

DETAILED ANALYSIS
=================

SSL/TLS CERTIFICATE
-------------------
Score: {analysis_results['score_breakdown']['ssl_score']}/100
Certificate Status: {'Valid' if analysis_results['ssl_status'].get('is_valid') else 'Invalid'}
Days to Expiry: {analysis_results['ssl_status'].get('days_until_expiry', 'Unknown')}

SECURITY HEADERS
----------------
Score: {analysis_results['score_breakdown']['headers_score']}/100
Present Headers: {analysis_results['headers_analysis'].get('present_headers', 0)}/{analysis_results['headers_analysis'].get('total_headers_checked', 0)}

HTTPS IMPLEMENTATION
--------------------
Score: {analysis_results['score_breakdown']['https_score']}/100
HTTPS Redirect: {'Working' if analysis_results.get('https_redirect') else 'Not Working'}

COOKIE SECURITY
---------------
Score: {analysis_results['score_breakdown']['cookie_score']}/100
Cookies Found: {analysis_results.get('cookie_analysis', {}).get('cookies_found', False)}

CONTENT SECURITY
----------------
Score: {analysis_results['score_breakdown']['content_score']}/100
CSP Implemented: {analysis_results.get('content_security_analysis', {}).get('csp_implemented', False)}

SECURITY VULNERABILITIES
========================
"""
    
        for i, vuln in enumerate(analysis_results.get('vulnerabilities', []), 1):
            report += f"{i}. {vuln}\n"
    
        report += "\nSECURITY RECOMMENDATIONS\n"
        report += "========================\n"
    
        for i, rec in enumerate(analysis_results.get('recommendations', []), 1):
            report += f"{i}. {rec}\n"
    
        return report

# Example usage and testing functions
async def test_security_analyzer(url: str = "https://example.com"):
    """Test function for the SecurityAnalyzer"""
    from utils.browser_manager import BrowserManager
    
    # Initialize browser manager
    browser_manager = BrowserManager(pool_size=3)
    await browser_manager.initialize()
    
    try:
        # Create security analyzer
        analyzer = SecurityAnalyzer(browser_manager)
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        # Test with a real website
        print(f"Testing security analysis for: {url}")
        results = await analyzer.analyze(url)
        
        print("\n=== SECURITY ANALYSIS RESULTS ===")
        print(f"Overall Score: {results['score']}/100 ({results['grade']})")
        print(f"Security Level: {results['security_level']}")
        
        # SSL Status
        ssl_status = results['ssl_status']
        print(f"\nSSL Certificate: {'✓' if ssl_status.get('certificate_found') else '✗'}")
        if ssl_status.get('certificate_found'):
            print(f"  Valid: {'✓' if ssl_status.get('is_valid') else '✗'}")
            print(f"  Days until expiry: {ssl_status.get('days_until_expiry', 'Unknown')}")
        
        # HTTPS Status
        print(f"HTTPS Redirect: {'✓' if results.get('https_redirect') else '✗'}")
        
        # Security Headers
        headers = results.get('security_headers', {})
        print(f"Security Headers Score: {headers.get('headers_score', 0)}/100")
        
        print("\n=== VULNERABILITIES ===")
        for i, vuln in enumerate(results.get('vulnerabilities', [])[:5], 1):
            print(f"{i}. {vuln}")
        
        print("\n=== TOP SECURITY RECOMMENDATIONS ===")
        for i, rec in enumerate(results.get('recommendations', [])[:6], 1):
            print(f"{i}. {rec}")
        
        print(f"\n=== SCORE BREAKDOWN ===")
        breakdown = results.get('score_breakdown', {})
        print(f"SSL Score: {breakdown.get('ssl_score', 0)}/100")
        print(f"Headers Score: {breakdown.get('headers_score', 0)}/100")
        print(f"HTTPS Score: {breakdown.get('https_score', 0)}/100")
        print(f"Cookie Score: {breakdown.get('cookie_score', 0)}/100")
        print(f"Content Security Score: {breakdown.get('content_score', 0)}/100")
        
        # Generate and display report
        report = analyzer.generate_security_report(results)
        print("\n=== FULL SECURITY REPORT ===")
        print(report)
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await browser_manager.cleanup()


if __name__ == "__main__":
    import sys
    import asyncio
    
    # Get URL from command line arguments
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    asyncio.run(test_security_analyzer(url))
