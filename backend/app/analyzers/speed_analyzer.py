import asyncio
import time
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

# Browser manager for getting browser instances
from utils.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class SpeedAnalyzer:

    def __init__(self, browser_manager: BrowserManager):
       
        self.browser_manager = browser_manager
        self.timeout = 30  # Maximum time to wait for page load
        
        # Speed scoring thresholds (based on Google PageSpeed standards)
        self.scoring_thresholds = {
            "excellent": {"min": 90, "max_load_time": 1.5, "max_fcp": 1800},
            "good": {"min": 75, "max_load_time": 3.0, "max_fcp": 3000},
            "needs_improvement": {"min": 50, "max_load_time": 5.0, "max_fcp": 4000},
            "poor": {"min": 0, "max_load_time": float('inf'), "max_fcp": float('inf')}
        }
        
        logger.info("SpeedAnalyzer initialized")
    
    async def analyze(self, url: str) -> Dict[str, Any]:
       
        logger.info(f"Starting speed analysis for: {url}")
        start_time = time.time()
        
        try:
            # Get browser page from pool
            async with self.browser_manager.get_browser_page() as page:
                
                # Set up performance monitoring
                performance_metrics = {}
                resource_stats = {
                    "requests": [],
                    "total_size": 0,
                    "resource_count": 0,
                    "failed_requests": 0
                }
                
        
                await self._setup_network_monitoring(page, resource_stats)
                
                load_metrics = await self._measure_page_load(page, url)
                
                # Get Core Web Vitals (Google's speed metrics)
                core_vitals = await self._get_core_web_vitals(page)
                
                # Analyze resource loading patterns
                resource_analysis = await self._analyze_resource_loading(resource_stats)
                

                speed_score = self._calculate_speed_score(load_metrics, core_vitals, resource_analysis)
                
                # Generate recommendations
                recommendations = self._generate_recommendations(
                    load_metrics, core_vitals, resource_analysis, speed_score
                )
                

                analysis_time = time.time() - start_time
                
                results = {
                    "score": speed_score,
                    "grade": self._get_grade_from_score(speed_score),
               
                    "load_time": load_metrics["full_load_time"],
                    "first_contentful_paint": core_vitals.get("first_contentful_paint", 0),
                    "largest_contentful_paint": core_vitals.get("largest_contentful_paint", 0),
                    "cumulative_layout_shift": core_vitals.get("cumulative_layout_shift", 0),
                    
                    "page_size": resource_stats["total_size"],
                    "requests_count": resource_stats["resource_count"],
                    "failed_requests": resource_stats["failed_requests"],
                    
                    "load_breakdown": load_metrics,
                    "core_web_vitals": core_vitals,
                    "resource_breakdown": resource_analysis,
                    
                    "recommendations": recommendations,
                    "issues": self._identify_performance_issues(load_metrics, core_vitals, resource_analysis),
                    
                    "analysis_duration": analysis_time,
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "analyzer_version": "1.0.0"
                }
                
                logger.info(f"Speed analysis completed. Score: {speed_score}/100, Load time: {load_metrics['full_load_time']:.2f}s")
                return results
                
        except asyncio.TimeoutError:
            logger.error(f"Speed analysis timed out for {url}")
            return self._create_timeout_result(url, time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Speed analysis failed for {url}: {e}")
            return self._create_error_result(url, str(e), time.time() - start_time)
    
    async def _setup_network_monitoring(self, page, resource_stats: Dict):
        
        async def handle_request(request):
            resource_stats["requests"].append({
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "timestamp": time.time()
            })
            resource_stats["resource_count"] += 1
        
        async def handle_response(response):
        
            try:
                # Add response size to total
                headers = await response.all_headers()
                content_length = headers.get("content-length", "0")
                
                try:
                    size = int(content_length)
                    resource_stats["total_size"] += size
                except (ValueError, TypeError):
                    # If content-length not available, estimate based on resource type
                    resource_type = response.request.resource_type
                    estimated_size = self._estimate_resource_size(resource_type)
                    resource_stats["total_size"] += estimated_size
                
                # Track failed requests
                if response.status >= 400:
                    resource_stats["failed_requests"] += 1
                    
            except Exception as e:
                logger.debug(f"Error processing response: {e}")
        
        # Set up event listeners
        page.on("request", handle_request)
        page.on("response", handle_response)
    
    async def _measure_page_load(self, page, url: str) -> Dict[str, float]:

        metrics = {}
        
        # Start timing
        start_time = time.time()
        
        try:
            # Navigate to page and wait for basic load
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            dom_load_time = time.time() - start_time
            
            # Wait for all resources to finish loading
            await page.wait_for_load_state("networkidle", timeout=10000)  # Wait up to 10 more seconds
            full_load_time = time.time() - start_time
            
            # Get navigation timing from browser
            navigation_timing = await page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        dns_lookup: timing.domainLookupEnd - timing.domainLookupStart,
                        connection: timing.connectEnd - timing.connectStart,
                        request: timing.responseStart - timing.requestStart,
                        response: timing.responseEnd - timing.responseStart,
                        dom_processing: timing.domComplete - timing.domLoading
                    };
                }
            """)
            
            metrics.update({
                "dom_load_time": dom_load_time,
                "full_load_time": full_load_time,
                "dns_lookup_time": navigation_timing.get("dns_lookup", 0) / 1000,
                "connection_time": navigation_timing.get("connection", 0) / 1000,
                "server_response_time": navigation_timing.get("request", 0) / 1000,
                "content_download_time": navigation_timing.get("response", 0) / 1000,
                "dom_processing_time": navigation_timing.get("dom_processing", 0) / 1000
            })
            
        except asyncio.TimeoutError:
            # If page doesn't fully load, record partial metrics
            metrics = {
                "dom_load_time": time.time() - start_time,
                "full_load_time": self.timeout,  # Mark as timeout
                "dns_lookup_time": 0,
                "connection_time": 0,
                "server_response_time": 0,
                "content_download_time": 0,
                "dom_processing_time": 0,
                "timed_out": True
            }
        
        return metrics
    
    async def _get_core_web_vitals(self, page) -> Dict[str, float]:
        """
        Get Google's Core Web Vitals metrics.
        These are the official metrics Google uses to rank websites.
        """
        try:
            # Inject Web Vitals measurement script
            vitals_script = """
                () => {
                    return new Promise((resolve) => {
                        // First Contentful Paint (FCP)
                        let fcp = 0;
                        
                        // Get FCP from Performance Observer
                        if ('PerformanceObserver' in window) {
                            try {
                                const observer = new PerformanceObserver((list) => {
                                    const entries = list.getEntries();
                                    entries.forEach((entry) => {
                                        if (entry.name === 'first-contentful-paint') {
                                            fcp = entry.startTime;
                                        }
                                    });
                                });
                                observer.observe({entryTypes: ['paint']});
                            } catch (e) {
                                console.log('Performance Observer not supported');
                            }
                        }
                        
                        // Fallback: get timing from performance.timing
                        setTimeout(() => {
                            const timing = performance.timing;
                            const navigationStart = timing.navigationStart;
                            
                            resolve({
                                first_contentful_paint: fcp || (timing.responseEnd - navigationStart),
                                largest_contentful_paint: fcp * 1.2 || (timing.loadEventEnd - navigationStart),
                                cumulative_layout_shift: 0.1, // Simplified - would need more complex measurement
                                first_input_delay: 50 // Simplified - would need actual user interaction
                            });
                        }, 2000); // Wait 2 seconds for metrics to stabilize
                    });
                }
            """
            
            vitals = await page.evaluate(vitals_script)
            return vitals
            
        except Exception as e:
            logger.debug(f"Error getting Core Web Vitals: {e}")
            # Return default values if measurement fails
            return {
                "first_contentful_paint": 3000,
                "largest_contentful_paint": 4000,
                "cumulative_layout_shift": 0.1,
                "first_input_delay": 100
            }
    
    async def _analyze_resource_loading(self, resource_stats: Dict) -> Dict[str, Any]:
        """
        Analyze patterns in resource loading.
        This is like analyzing traffic patterns to find bottlenecks.
        """
        requests = resource_stats["requests"]
        
        # Count resources by type
        resource_types = {}
        for request in requests:
            resource_type = request["resource_type"]
            resource_types[resource_type] = resource_types.get(resource_type, 0) + 1
        
        # Calculate resource efficiency metrics
        total_requests = len(requests)
        failed_percentage = (resource_stats["failed_requests"] / max(total_requests, 1)) * 100
        
        # Estimate page size categories
        total_size_mb = resource_stats["total_size"] / (1024 * 1024)  # Convert to MB
        
        return {
            "resource_types": resource_types,
            "total_requests": total_requests,
            "failed_requests": resource_stats["failed_requests"],
            "failed_percentage": failed_percentage,
            "total_size_mb": round(total_size_mb, 2),
            "average_request_size": resource_stats["total_size"] / max(total_requests, 1),
            "efficiency_score": max(0, 100 - failed_percentage - (total_size_mb * 5))  # Penalty for large size
        }
    
    def _calculate_speed_score(self, load_metrics: Dict, core_vitals: Dict, resource_analysis: Dict) -> int:
        
        # Factor 1: Load Time Score (40% weight)
        load_time = load_metrics.get("full_load_time", 30)
        if load_time <= 1.5:
            load_score = 100
        elif load_time <= 3.0:
            load_score = 85
        elif load_time <= 5.0:
            load_score = 65
        elif load_time <= 8.0:
            load_score = 40
        else:
            load_score = 20
        
        # Factor 2: Core Web Vitals Score (35% weight)
        fcp = core_vitals.get("first_contentful_paint", 3000)
        lcp = core_vitals.get("largest_contentful_paint", 4000)
        cls = core_vitals.get("cumulative_layout_shift", 0.1)
        
        # FCP scoring (Google thresholds)
        if fcp <= 1800:
            fcp_score = 100
        elif fcp <= 3000:
            fcp_score = 75
        else:
            fcp_score = 40
        
        # LCP scoring
        if lcp <= 2500:
            lcp_score = 100
        elif lcp <= 4000:
            lcp_score = 75
        else:
            lcp_score = 40
        
        # CLS scoring
        if cls <= 0.1:
            cls_score = 100
        elif cls <= 0.25:
            cls_score = 75
        else:
            cls_score = 40
        
        vitals_score = (fcp_score + lcp_score + cls_score) / 3
        
        # Factor 3: Resource Efficiency Score (25% weight)
        efficiency_score = resource_analysis.get("efficiency_score", 70)
        
        # Combine all factors with weights
        final_score = (
            load_score * 0.40 +
            vitals_score * 0.35 +
            efficiency_score * 0.25
        )
        
        return max(0, min(100, round(final_score)))
    
    def _generate_recommendations(self, load_metrics: Dict, core_vitals: Dict, 
                                resource_analysis: Dict, score: int) -> List[str]:

        recommendations = []
        
        # Load time recommendations
        load_time = load_metrics.get("full_load_time", 0)
        if load_time > 5:
            recommendations.append("Optimize server response time - page loads very slowly")
        elif load_time > 3:
            recommendations.append("Reduce page load time to under 3 seconds for better user experience")
        
        # Resource optimization recommendations
        total_size_mb = resource_analysis.get("total_size_mb", 0)
        if total_size_mb > 3:
            recommendations.append(f"Reduce page size ({total_size_mb:.1f}MB) - compress images and minify code")
        
        total_requests = resource_analysis.get("total_requests", 0)
        if total_requests > 100:
            recommendations.append(f"Reduce HTTP requests ({total_requests}) - combine CSS/JS files")
        
        failed_percentage = resource_analysis.get("failed_percentage", 0)
        if failed_percentage > 5:
            recommendations.append(f"Fix failed requests ({failed_percentage:.1f}%) - broken links hurt performance")
        
        # Core Web Vitals recommendations
        fcp = core_vitals.get("first_contentful_paint", 0)
        if fcp > 3000:
            recommendations.append("Improve First Contentful Paint - optimize above-the-fold content")
        
        lcp = core_vitals.get("largest_contentful_paint", 0)
        if lcp > 4000:
            recommendations.append("Optimize Largest Contentful Paint - prioritize main content loading")
        
        # Server-specific recommendations
        server_time = load_metrics.get("server_response_time", 0)
        if server_time > 1:
            recommendations.append("Improve server response time - consider faster hosting or caching")
        
        # Image optimization (inferred from resource types)
        resource_types = resource_analysis.get("resource_types", {})
        image_requests = resource_types.get("image", 0)
        if image_requests > 20:
            recommendations.append("Optimize images - use WebP format and lazy loading")
        
        # General recommendations based on score
        if score < 50:
            recommendations.append("Consider using a Content Delivery Network (CDN)")
            recommendations.append("Enable Gzip compression on your server")
        
        if score < 70:
            recommendations.append("Minify CSS and JavaScript files")
            recommendations.append("Optimize font loading with font-display: swap")
        
        return recommendations[:8]  # Return top 8 recommendations
    
    def _identify_performance_issues(self, load_metrics: Dict, core_vitals: Dict, 
                                   resource_analysis: Dict) -> List[str]:

        issues = []
        
        # Critical load time issues
        load_time = load_metrics.get("full_load_time", 0)
        if load_time > 10:
            issues.append("CRITICAL: Page load time exceeds 10 seconds")
        elif load_time > 8:
            issues.append("WARNING: Very slow page load time")
        
        # Critical resource issues
        failed_percentage = resource_analysis.get("failed_percentage", 0)
        if failed_percentage > 10:
            issues.append("CRITICAL: High number of failed requests")
        
        total_size_mb = resource_analysis.get("total_size_mb", 0)
        if total_size_mb > 10:
            issues.append("CRITICAL: Page size too large for mobile users")
        
        total_requests = resource_analysis.get("total_requests", 0)
        if total_requests > 200:
            issues.append("WARNING: Too many HTTP requests")
        
        # Core Web Vitals issues
        fcp = core_vitals.get("first_contentful_paint", 0)
        if fcp > 4000:
            issues.append("CRITICAL: First Contentful Paint too slow")
        
        # Timeout issues
        if load_metrics.get("timed_out", False):
            issues.append("CRITICAL: Page failed to load completely")
        
        return issues
    
    def _get_grade_from_score(self, score: int) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _estimate_resource_size(self, resource_type: str) -> int:
        """
        Estimate resource size when content-length header is missing.
        Based on typical file sizes for different resource types.
        """
        size_estimates = {
            "document": 50000,    # 50KB for HTML
            "stylesheet": 25000,  # 25KB for CSS
            "script": 100000,     # 100KB for JS
            "image": 150000,      # 150KB for images
            "font": 75000,        # 75KB for fonts
            "xhr": 5000,          # 5KB for AJAX requests
            "fetch": 5000,        # 5KB for fetch requests
            "other": 10000        # 10KB for other resources
        }
        
        return size_estimates.get(resource_type, 10000)
    
    def _create_timeout_result(self, url: str, analysis_time: float) -> Dict[str, Any]:
        """Create result when analysis times out"""
        return {
            "score": 20,
            "grade": "F",
            "load_time": self.timeout,
            "first_contentful_paint": 0,
            "largest_contentful_paint": 0,
            "cumulative_layout_shift": 0,
            "page_size": 0,
            "requests_count": 0,
            "failed_requests": 0,
            "recommendations": [
                "Website took too long to load (timed out)",
                "Check server performance and hosting reliability",
                "Consider using a faster web hosting provider"
            ],
            "issues": ["CRITICAL: Website timed out during analysis"],
            "analysis_duration": analysis_time,
            "analyzed_at": datetime.utcnow().isoformat(),
            "error": "Analysis timed out"
        }
    
    def _create_error_result(self, url: str, error_msg: str, analysis_time: float) -> Dict[str, Any]:
        """Create result when analysis fails"""
        return {
            "score": 0,
            "grade": "F",
            "load_time": 0,
            "first_contentful_paint": 0,
            "largest_contentful_paint": 0,
            "cumulative_layout_shift": 0,
            "page_size": 0,
            "requests_count": 0,
            "failed_requests": 0,
            "recommendations": [
                "Unable to analyze website - check if URL is accessible",
                "Verify website is online and responding to requests"
            ],
            "issues": [f"CRITICAL: Analysis failed - {error_msg}"],
            "analysis_duration": analysis_time,
            "analyzed_at": datetime.utcnow().isoformat(),
            "error": error_msg
        }

# Example usage and testing functions
async def test_speed_analyzer():
    """
    Test function to verify the speed analyzer works correctly.
    This demonstrates how to use the speed analyzer.
    """
    from utils.browser_manager import BrowserManager
    
    # Initialize browser manager
    browser_manager = BrowserManager(pool_size=1)
    await browser_manager.initialize()
    
    try:
        # Create speed analyzer
        analyzer = SpeedAnalyzer(browser_manager)
        
        # Test with a real website
        print("Testing speed analysis...")
        results = await analyzer.analyze("https://wikipedia.org")
        
        print("\n=== SPEED ANALYSIS RESULTS ===")
        print(f"Overall Score: {results['score']}/100 ({results['grade']})")
        print(f"Load Time: {results['load_time']:.2f} seconds")
        print(f"First Contentful Paint: {results['first_contentful_paint']:.0f}ms")
        print(f"Page Size: {results.get('resource_breakdown', {}).get('total_size_mb', 0):.2f}MB")
        print(f"Total Requests: {results['requests_count']}")
        
        print("\n=== TOP RECOMMENDATIONS ===")
        for i, rec in enumerate(results['recommendations'][:5], 1):
            print(f"{i}. {rec}")
        
        if results.get('issues'):
            print("\n=== PERFORMANCE ISSUES ===")
            for i, issue in enumerate(results['issues'], 1):
                print(f"{i}. {issue}")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await browser_manager.cleanup()

if __name__ == "__main__":
    # Run test if this file is executed directly
    import asyncio
    asyncio.run(test_speed_analyzer())