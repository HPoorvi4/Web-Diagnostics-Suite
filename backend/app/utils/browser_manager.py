import asyncio
import logging
import time
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Fix import path for both direct execution and module execution
try:
    # Try importing from current directory structure (when run as module)
    from browser_manager import BrowserManager, create_mobile_page_options, create_desktop_page_options
except ImportError:
    # Add parent directory to path and try again
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.join(current_dir, '..')
    sys.path.insert(0, os.path.abspath(parent_dir))
    
    try:
        from browser_manager import BrowserManager, create_mobile_page_options, create_desktop_page_options
    except ImportError:
        # Try adding the app directory to path (if we're deeper in structure)
        app_dir = os.path.join(current_dir, '..', '..')
        sys.path.insert(0, os.path.abspath(app_dir))
        try:
            from browser_manager import BrowserManager, create_mobile_page_options, create_desktop_page_options
        except ImportError as e:
            print(f"Could not import browser_manager. Make sure browser_manager.py exists in the app directory.")
            print(f"Current directory: {current_dir}")
            print(f"Parent directory: {os.path.abspath(parent_dir)}")
            print(f"Error: {e}")
            sys.exit(1)

logger = logging.getLogger(__name__)

class MobileAnalyzer:
    """
    Analyzes mobile-friendliness and responsive design of websites.
    
    This analyzer checks:
    - Viewport meta tag
    - Responsive design across different screen sizes
    - Touch-friendly elements
    - Mobile load times
    - Mobile-specific UI issues
    """
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        
        # Device configurations for testing
        self.devices = {
            "mobile_phone": {
                "name": "iPhone 12",
                "viewport": {"width": 390, "height": 844},
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                "device_scale_factor": 3,
                "is_mobile": True,
                "has_touch": True
            },
            "tablet": {
                "name": "iPad",
                "viewport": {"width": 820, "height": 1180},
                "user_agent": "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                "device_scale_factor": 2,
                "is_mobile": True,
                "has_touch": True
            },
            "desktop": {
                "name": "Desktop",
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False
            }
        }
    
    async def analyze_mobile_friendliness(self, url: str, include_screenshots: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive mobile-friendliness analysis.
        
        Args:
            url: Website URL to analyze
            include_screenshots: Whether to capture screenshots
        
        Returns:
            Dict containing mobile analysis results
        """
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        logger.info(f"Starting mobile analysis for {url}")
        
        results = {
            "url": url,
            "analyzed_at": datetime.utcnow().isoformat(),
            "viewport_meta": False,
            "responsive_design": {
                "score": 0,
                "issues": []
            },
            "touch_friendly": {
                "score": 0,
                "interactive_elements": 0,
                "issues": []
            },
            "mobile_performance": {
                "load_time": 0,
                "first_contentful_paint": 0,
                "largest_contentful_paint": 0
            },
            "readability": {
                "score": 0,
                "font_size_issues": [],
                "contrast_issues": []
            },
            "device_compatibility": {},
            "screenshots": {} if include_screenshots else None,
            "overall_score": 0,
            "mobile_friendly_level": "Not Mobile-Friendly",
            "critical_issues": [],
            "recommendations": []
        }
        
        try:
            # 1. Check viewport meta tag
            results["viewport_meta"] = await self._check_viewport_meta(url)
            
            # 2. Analyze across different devices
            device_results = await self._analyze_device_compatibility(url, include_screenshots)
            results["device_compatibility"] = device_results["compatibility"]
            if include_screenshots:
                results["screenshots"] = device_results["screenshots"]
            
            # 3. Analyze responsive design
            results["responsive_design"] = await self._analyze_responsive_design(url)
            
            # 4. Check touch-friendliness
            results["touch_friendly"] = await self._analyze_touch_friendliness(url)
            
            # 5. Analyze mobile readability
            results["readability"] = await self._analyze_mobile_readability(url)
            
            # 6. Check mobile performance
            results["mobile_performance"] = await self._analyze_mobile_performance(url)
            
            # Calculate overall score
            results["overall_score"] = self._calculate_mobile_score(results)
            results["mobile_friendly_level"] = self._get_mobile_friendly_level(results["overall_score"])
            
            # Generate issues and recommendations
            results["critical_issues"] = self._identify_critical_issues(results)
            results["recommendations"] = self._generate_mobile_recommendations(results)
            
            logger.info(f"Mobile analysis completed for {url} - Score: {results['overall_score']}")
            
        except Exception as e:
            logger.error(f"Mobile analysis failed for {url}: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _check_viewport_meta(self, url: str) -> bool:
        """Check if the page has a proper viewport meta tag"""
        try:
            async with self.browser_manager.get_browser_page() as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Check for viewport meta tag
                viewport_meta = await page.query_selector('meta[name="viewport"]')
                if viewport_meta:
                    content = await viewport_meta.get_attribute("content")
                    # Check if it has proper mobile viewport settings
                    return "width=device-width" in content.lower() if content else False
                
                return False
                
        except Exception as e:
            logger.error(f"Viewport meta check failed: {e}")
            return False
    
    async def _analyze_device_compatibility(self, url: str, include_screenshots: bool = False) -> Dict[str, Any]:
        """Analyze how the website performs across different devices"""
        compatibility_results = {}
        screenshots = {}
        
        for device_type, device_config in self.devices.items():
            try:
                logger.info(f"Testing device compatibility for {device_config['name']}")
                
                async with self.browser_manager.get_browser_page(**device_config) as page:
                    start_time = time.time()
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    load_time = time.time() - start_time
                    
                    # Get page dimensions and content
                    page_info = await page.evaluate("""
                        () => {
                            return {
                                scrollWidth: document.documentElement.scrollWidth,
                                scrollHeight: document.documentElement.scrollHeight,
                                clientWidth: document.documentElement.clientWidth,
                                clientHeight: document.documentElement.clientHeight,
                                hasHorizontalScroll: document.documentElement.scrollWidth > window.innerWidth,
                                hasVerticalScroll: document.documentElement.scrollHeight > window.innerHeight,
                                viewportWidth: window.innerWidth,
                                viewportHeight: window.innerHeight
                            }
                        }
                    """)
                    
                    compatibility_results[device_type] = {
                        "device_name": device_config["name"],
                        "viewport": device_config["viewport"],
                        "load_time": load_time,
                        "page_dimensions": page_info,
                        "has_horizontal_scroll": page_info["hasHorizontalScroll"],
                        "responsive": not page_info["hasHorizontalScroll"]
                    }
                    
                    # Capture screenshot if requested
                    if include_screenshots:
                        try:
                            screenshot_buffer = await page.screenshot(full_page=True, type="png")
                            screenshots[device_type] = {
                                "device_name": device_config["name"],
                                "data": screenshot_buffer,
                                "dimensions": device_config["viewport"]
                            }
                            logger.info(f"Screenshot captured for {device_config['name']}")
                        except Exception as e:
                            logger.error(f"Screenshot capture failed for {device_config['name']}: {e}")
                    
            except Exception as e:
                logger.error(f"Device analysis failed for {device_type}: {e}")
                compatibility_results[device_type] = {
                    "device_name": device_config["name"],
                    "error": str(e),
                    "responsive": False
                }
        
        return {
            "compatibility": compatibility_results,
            "screenshots": screenshots if include_screenshots else {}
        }
    
    async def _analyze_responsive_design(self, url: str) -> Dict[str, Any]:
        """Analyze responsive design implementation"""
        try:
            async with self.browser_manager.get_browser_page() as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Check for CSS media queries
                media_queries = await page.evaluate("""
                    () => {
                        const styleSheets = Array.from(document.styleSheets);
                        let mediaQueries = [];
                        
                        try {
                            styleSheets.forEach(sheet => {
                                if (sheet.cssRules) {
                                    Array.from(sheet.cssRules).forEach(rule => {
                                        if (rule.type === CSSRule.MEDIA_RULE) {
                                            mediaQueries.push(rule.media.mediaText);
                                        }
                                    });
                                }
                            });
                        } catch (e) {
                            // Can't access cross-origin stylesheets
                        }
                        
                        return mediaQueries;
                    }
                """)
                
                # Check for flexible layouts
                flexible_elements = await page.evaluate("""
                    () => {
                        const elements = Array.from(document.querySelectorAll('*'));
                        let flexibleCount = 0;
                        
                        elements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.display === 'flex' || 
                                style.display === 'grid' || 
                                style.width.includes('%') ||
                                style.maxWidth.includes('%') ||
                                style.minWidth.includes('%')) {
                                flexibleCount++;
                            }
                        });
                        
                        return {
                            total_elements: elements.length,
                            flexible_elements: flexibleCount,
                            percentage: flexibleCount / elements.length * 100
                        };
                    }
                """)
                
                # Calculate responsive score
                responsive_score = 0
                issues = []
                
                # Media queries check (30 points)
                if media_queries and len(media_queries) > 0:
                    responsive_score += 30
                else:
                    issues.append("No CSS media queries detected")
                
                # Flexible layout check (40 points)
                if flexible_elements["percentage"] > 20:
                    responsive_score += 40
                elif flexible_elements["percentage"] > 10:
                    responsive_score += 20
                else:
                    issues.append("Limited use of flexible layouts")
                
                # Viewport meta tag check (30 points)
                has_viewport = await self._check_viewport_meta(url)
                if has_viewport:
                    responsive_score += 30
                else:
                    issues.append("Missing or improper viewport meta tag")
                
                return {
                    "score": min(responsive_score, 100),
                    "media_queries": len(media_queries),
                    "flexible_elements": flexible_elements,
                    "issues": issues
                }
                
        except Exception as e:
            logger.error(f"Responsive design analysis failed: {e}")
            return {
                "score": 0,
                "issues": [f"Analysis failed: {str(e)}"]
            }
    
    async def _analyze_touch_friendliness(self, url: str) -> Dict[str, Any]:
        """Analyze touch-friendly design elements"""
        try:
            mobile_options = await create_mobile_page_options()
            async with self.browser_manager.get_browser_page(**mobile_options) as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Analyze interactive elements
                touch_analysis = await page.evaluate("""
                    () => {
                        const interactiveSelectors = 'a, button, input, select, textarea, [onclick], [role="button"]';
                        const elements = Array.from(document.querySelectorAll(interactiveSelectors));
                        
                        let touchFriendlyCount = 0;
                        let totalElements = elements.length;
                        let smallElements = [];
                        
                        elements.forEach((el, index) => {
                            const rect = el.getBoundingClientRect();
                            const minSize = 44; // Apple's recommended minimum touch target size
                            
                            if (rect.width >= minSize && rect.height >= minSize) {
                                touchFriendlyCount++;
                            } else {
                                smallElements.push({
                                    tag: el.tagName.toLowerCase(),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    text: el.textContent ? el.textContent.slice(0, 30) : ''
                                });
                            }
                        });
                        
                        // Check spacing between elements
                        let crowdedElements = 0;
                        elements.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            const nearby = elements.filter(other => {
                                if (other === el) return false;
                                const otherRect = other.getBoundingClientRect();
                                const distance = Math.sqrt(
                                    Math.pow(rect.left - otherRect.left, 2) + 
                                    Math.pow(rect.top - otherRect.top, 2)
                                );
                                return distance < 48; // Less than recommended spacing
                            });
                            if (nearby.length > 0) crowdedElements++;
                        });
                        
                        return {
                            total_interactive: totalElements,
                            touch_friendly: touchFriendlyCount,
                            small_elements: smallElements.slice(0, 10), // Limit to 10 examples
                            crowded_elements: crowdedElements,
                            percentage: totalElements > 0 ? (touchFriendlyCount / totalElements) * 100 : 0
                        };
                    }
                """)
                
                # Calculate touch score
                touch_score = 0
                issues = []
                
                if touch_analysis["percentage"] >= 80:
                    touch_score = 90
                elif touch_analysis["percentage"] >= 60:
                    touch_score = 70
                elif touch_analysis["percentage"] >= 40:
                    touch_score = 50
                else:
                    touch_score = 30
                
                # Penalties for issues
                if len(touch_analysis["small_elements"]) > 0:
                    issues.append(f"{len(touch_analysis['small_elements'])} elements are too small for touch")
                    touch_score = max(0, touch_score - 20)
                
                if touch_analysis["crowded_elements"] > 5:
                    issues.append("Interactive elements are too close together")
                    touch_score = max(0, touch_score - 15)
                
                return {
                    "score": touch_score,
                    "interactive_elements": touch_analysis["total_interactive"],
                    "touch_friendly_percentage": touch_analysis["percentage"],
                    "small_elements": touch_analysis["small_elements"],
                    "issues": issues
                }
                
        except Exception as e:
            logger.error(f"Touch-friendliness analysis failed: {e}")
            return {
                "score": 0,
                "interactive_elements": 0,
                "issues": [f"Analysis failed: {str(e)}"]
            }
    
    async def _analyze_mobile_readability(self, url: str) -> Dict[str, Any]:
        """Analyze mobile readability factors"""
        try:
            mobile_options = await create_mobile_page_options()
            async with self.browser_manager.get_browser_page(**mobile_options) as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                readability_analysis = await page.evaluate("""
                    () => {
                        const textElements = Array.from(document.querySelectorAll('p, span, div, li, td, th, h1, h2, h3, h4, h5, h6'));
                        let fontSizeIssues = [];
                        let totalTextElements = 0;
                        let readableElements = 0;
                        
                        textElements.forEach((el, index) => {
                            const style = window.getComputedStyle(el);
                            const fontSize = parseFloat(style.fontSize);
                            const hasText = el.textContent && el.textContent.trim().length > 0;
                            
                            if (hasText) {
                                totalTextElements++;
                                
                                if (fontSize >= 16) { // Recommended minimum for mobile
                                    readableElements++;
                                } else {
                                    fontSizeIssues.push({
                                        tag: el.tagName.toLowerCase(),
                                        fontSize: fontSize,
                                        text: el.textContent.slice(0, 50)
                                    });
                                }
                            }
                        });
                        
                        // Check line height
                        let lineHeightIssues = 0;
                        textElements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            const lineHeight = parseFloat(style.lineHeight);
                            const fontSize = parseFloat(style.fontSize);
                            const ratio = lineHeight / fontSize;
                            
                            if (ratio < 1.4) { // Recommended minimum line height ratio
                                lineHeightIssues++;
                            }
                        });
                        
                        return {
                            total_text_elements: totalTextElements,
                            readable_elements: readableElements,
                            font_size_issues: fontSizeIssues.slice(0, 10),
                            line_height_issues: lineHeightIssues,
                            readability_percentage: totalTextElements > 0 ? (readableElements / totalTextElements) * 100 : 0
                        };
                    }
                """)
                
                # Calculate readability score
                readability_score = 0
                issues = []
                
                if readability_analysis["readability_percentage"] >= 90:
                    readability_score = 95
                elif readability_analysis["readability_percentage"] >= 75:
                    readability_score = 80
                elif readability_analysis["readability_percentage"] >= 50:
                    readability_score = 60
                else:
                    readability_score = 40
                
                # Add specific issues
                if len(readability_analysis["font_size_issues"]) > 0:
                    issues.append(f"{len(readability_analysis['font_size_issues'])} elements have font size below 16px")
                
                if readability_analysis["line_height_issues"] > 5:
                    issues.append("Poor line height spacing detected")
                    readability_score = max(0, readability_score - 10)
                
                return {
                    "score": readability_score,
                    "font_size_issues": readability_analysis["font_size_issues"],
                    "readability_percentage": readability_analysis["readability_percentage"],
                    "issues": issues
                }
                
        except Exception as e:
            logger.error(f"Mobile readability analysis failed: {e}")
            return {
                "score": 0,
                "font_size_issues": [],
                "issues": [f"Analysis failed: {str(e)}"]
            }
    
    async def _analyze_mobile_performance(self, url: str) -> Dict[str, Any]:
        """Analyze mobile-specific performance metrics"""
        try:
            mobile_options = await create_mobile_page_options()
            async with self.browser_manager.get_browser_page(**mobile_options) as page:
                start_time = time.time()
                
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                load_time = time.time() - start_time
                
                # Get performance metrics
                performance_metrics = await page.evaluate("""
                    () => {
                        const perfData = performance.getEntriesByType('navigation')[0];
                        return {
                            loadEventEnd: perfData ? perfData.loadEventEnd : 0,
                            domContentLoadedEventEnd: perfData ? perfData.domContentLoadedEventEnd : 0,
                            firstContentfulPaint: 0, // Would need PerformanceObserver for real FCP
                            largestContentfulPaint: 0 // Would need PerformanceObserver for real LCP
                        };
                    }
                """)
                
                # Simulate mobile network conditions performance (basic estimation)
                return {
                    "load_time": load_time,
                    "first_contentful_paint": performance_metrics["firstContentfulPaint"] or load_time * 0.6,
                    "largest_contentful_paint": performance_metrics["largestContentfulPaint"] or load_time * 0.8,
                    "dom_content_loaded": performance_metrics["domContentLoadedEventEnd"] / 1000 if performance_metrics["domContentLoadedEventEnd"] else load_time * 0.7
                }
                
        except Exception as e:
            logger.error(f"Mobile performance analysis failed: {e}")
            return {
                "load_time": 30.0,  # Timeout fallback
                "first_contentful_paint": 0,
                "largest_contentful_paint": 0,
                "dom_content_loaded": 0
            }
    
    def _calculate_mobile_score(self, results: Dict[str, Any]) -> int:
        """Calculate overall mobile-friendliness score"""
        scores = []
        weights = []
        
        # Viewport meta tag (15% weight)
        if results.get("viewport_meta"):
            scores.append(100)
            weights.append(0.15)
        else:
            scores.append(0)
            weights.append(0.15)
        
        # Responsive design (25% weight)
        responsive_score = results.get("responsive_design", {}).get("score", 0)
        scores.append(responsive_score)
        weights.append(0.25)
        
        # Touch-friendliness (20% weight)
        touch_score = results.get("touch_friendly", {}).get("score", 0)
        scores.append(touch_score)
        weights.append(0.20)
        
        # Readability (20% weight)
        readability_score = results.get("readability", {}).get("score", 0)
        scores.append(readability_score)
        weights.append(0.20)
        
        # Mobile performance (20% weight)
        performance = results.get("mobile_performance", {})
        load_time = performance.get("load_time", 30)
        
        if load_time <= 2:
            perf_score = 100
        elif load_time <= 3:
            perf_score = 85
        elif load_time <= 5:
            perf_score = 70
        elif load_time <= 8:
            perf_score = 50
        else:
            perf_score = 20
        
        scores.append(perf_score)
        weights.append(0.20)
        
        # Calculate weighted average
        if sum(weights) > 0:
            weighted_score = sum(score * weight for score, weight in zip(scores, weights)) / sum(weights)
            return int(round(weighted_score))
        
        return 0
    
    def _get_mobile_friendly_level(self, score: int) -> str:
        """Get mobile-friendly level based on score"""
        if score >= 90:
            return "Excellent Mobile Experience"
        elif score >= 75:
            return "Good Mobile Experience"
        elif score >= 60:
            return "Mobile-Friendly"
        elif score >= 40:
            return "Partially Mobile-Friendly"
        else:
            return "Not Mobile-Friendly"
    
    def _identify_critical_issues(self, results: Dict[str, Any]) -> List[str]:
        """Identify critical mobile issues"""
        critical_issues = []
        
        # Viewport meta tag
        if not results.get("viewport_meta"):
            critical_issues.append("CRITICAL: No viewport meta tag - site will not display properly on mobile")
        
        # Responsive design issues
        device_compatibility = results.get("device_compatibility", {})
        non_responsive_devices = []
        for device_type, device_data in device_compatibility.items():
            if isinstance(device_data, dict) and device_data.get("has_horizontal_scroll"):
                non_responsive_devices.append(device_type)
        
        if non_responsive_devices:
            critical_issues.append(f"HIGH: Horizontal scrolling on {', '.join(non_responsive_devices)} devices")
        
        # Performance issues
        mobile_performance = results.get("mobile_performance", {})
        load_time = mobile_performance.get("load_time", 0)
        if load_time > 8:
            critical_issues.append("CRITICAL: Mobile page load time exceeds 8 seconds")
        elif load_time > 5:
            critical_issues.append("HIGH: Mobile page load time exceeds 5 seconds")
        
        # Touch-friendliness issues
        touch_data = results.get("touch_friendly", {})
        if touch_data.get("score", 0) < 40:
            critical_issues.append("HIGH: Many interactive elements are not touch-friendly")
        
        return critical_issues
    
    def _generate_mobile_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate mobile optimization recommendations"""
        recommendations = []
        
        # Viewport recommendations
        if not results.get("viewport_meta"):
            recommendations.append("URGENT: Add viewport meta tag: <meta name='viewport' content='width=device-width, initial-scale=1'>")
        
        # Responsive design recommendations
        responsive_data = results.get("responsive_design", {})
        if responsive_data.get("score", 0) < 70:
            recommendations.append("Fix horizontal scrolling by implementing proper responsive CSS")
            recommendations.append("Use CSS media queries to adapt layout for different screen sizes")
        
        # Performance recommendations
        mobile_performance = results.get("mobile_performance", {})
        load_time = mobile_performance.get("load_time", 0)
        if load_time > 3:
            recommendations.append("Optimize mobile page load time to under 3 seconds")
            recommendations.append("Compress and optimize images for mobile devices")
        
        # Touch-friendliness recommendations
        touch_data = results.get("touch_friendly", {})
        if touch_data.get("score", 0) < 70:
            recommendations.append("Increase touch target sizes to at least 44x44 pixels")
            recommendations.append("Add more spacing between interactive elements")
        
        # Readability recommendations
        readability_data = results.get("readability", {})
        if readability_data.get("score", 0) < 70:
            recommendations.append("Increase font sizes to at least 16px for body text")
            recommendations.append("Improve line height for better readability")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Great mobile optimization! Consider testing on more devices")
        else:
            recommendations.append("Add mobile-specific CSS with media queries")
        
        return recommendations[:6]  # Limit to top 6 recommendations


# Utility function for CLI testing
async def test_mobile_analyzer(url: str = None):
    """Test function for mobile analyzer"""
    browser_manager = BrowserManager(pool_size=2)
    
    try:
        await browser_manager.initialize()
        analyzer = MobileAnalyzer(browser_manager)
        
        # Use provided URL or default
        test_url = url or "https://www.wikipedia.org"
        
        print(f"Testing mobile analysis for: {test_url}")
        results = await analyzer.analyze_mobile_friendliness(test_url, include_screenshots=True)
        
        print(f"\n=== MOBILE ANALYSIS RESULTS ===")
        print(f"Overall Score: {results['overall_score']}/100 ({_get_grade(results['overall_score'])})")
        print(f"Mobile-Friendly Level: {results['mobile_friendly_level']}")
        
        print(f"\nViewport Meta Tag: {'✓' if results['viewport_meta'] else '✗'}")
        print(f"Responsive Design: {results['responsive_design']['score']:.1f}%")
        
        # Show device compatibility
        device_issues = []
        for device_type, device_data in results['device_compatibility'].items():
            if isinstance(device_data, dict) and device_data.get('has_horizontal_scroll'):
                device_issues.append(device_type)
        
        if device_issues:
            print(f"  Issues on: {', '.join(device_issues)}")
        
        print(f"Touch-Friendly Elements: {results['touch_friendly']['score']:.1f}%")
        print(f"Interactive Elements: {results['touch_friendly']['interactive_elements']}")
        print(f"Mobile Load Time: {results['mobile_performance']['load_time']:.2f}s")
        
        if results.get('screenshots'):
            print(f"\nScreenshots captured: {len(results['screenshots'])} devices")
        
        # Show critical issues
        if results['critical_issues']:
            print(f"\n=== MOBILE ISSUES ===")
            for i, issue in enumerate(results['critical_issues'], 1):
                print(f"{i}. {issue}")
        
        # Show recommendations
        if results['recommendations']:
            print(f"\n=== TOP MOBILE RECOMMENDATIONS ===")
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Score breakdown
        print(f"\n=== SCORE BREAKDOWN ===")
        print(f"Viewport Score: {100 if results['viewport_meta'] else 0}/100")
        print(f"Responsive Score: {results['responsive_design']['score']}/100")
        print(f"Touch Score: {results['touch_friendly']['score']}/100")
        print(f"Readability Score: {results['readability']['score']}/100")
        
        # Performance score calculation
        load_time = results['mobile_performance']['load_time']
        if load_time <= 2:
            perf_score = 100
        elif load_time <= 3:
            perf_score = 85
        elif load_time <= 5:
            perf_score = 70
        elif load_time <= 8:
            perf_score = 50
        else:
            perf_score = 20
        
        print(f"Performance Score: {perf_score}/100")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
    finally:
        await browser_manager.cleanup()


def _get_grade(score: int) -> str:
    """Get letter grade from score"""
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


# Main execution logic
async def main():
    """Main function to handle command line execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mobile-Friendliness Analyzer')
    parser.add_argument('url', nargs='?', help='URL to analyze', default=None)
    parser.add_argument('--screenshots', action='store_true', help='Include screenshots')
    
    # Handle both direct execution and module execution
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # Direct URL argument (for backward compatibility)
        url = sys.argv[1]
        include_screenshots = '--screenshots' in sys.argv
    else:
        # Use argparse for more complex argument handling
        args = parser.parse_args()
        url = args.url
        include_screenshots = args.screenshots
    
    if not url:
        print("Usage: python -m analyzers.mobile_analyzer <url> [--screenshots]")
        print("Example: python -m analyzers.mobile_analyzer www.wikipedia.org")
        return
    
    await test_mobile_analyzer(url)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    asyncio.run(main())