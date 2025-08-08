import asyncio
import logging
import time
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.browser_manager import BrowserManager, create_mobile_page_options, create_desktop_page_options

logger = logging.getLogger(__name__)

class MobileAnalyzer:  
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        
        # Device configurations for testing - Fixed: Removed 'name' parameter for Playwright compatibility
        self.devices = {
            "mobile_phone": {
                "viewport": {"width": 390, "height": 844},
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                "device_scale_factor": 3,
                "is_mobile": True,
                "has_touch": True
            },
            "tablet": {
                "viewport": {"width": 820, "height": 1180},
                "user_agent": "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                "device_scale_factor": 2,
                "is_mobile": True,
                "has_touch": True
            },
            "desktop": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False
            }
        }
        
        # Store device names separately for reference
        self.device_names = {
            "mobile_phone": "iPhone 12",
            "tablet": "iPad",
            "desktop": "Desktop"
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
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
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
        """Check if the page has a proper viewport meta tag - FIXED"""
        try:
            async with self.browser_manager.get_browser_page() as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # More comprehensive viewport meta tag check
                viewport_check = await page.evaluate("""
                    () => {
                        // Check for viewport meta tag
                        const viewportMeta = document.querySelector('meta[name="viewport"]');
                        if (!viewportMeta) {
                            return { found: false, reason: "No viewport meta tag" };
                        }
                        
                        const content = viewportMeta.getAttribute("content");
                        if (!content) {
                            return { found: false, reason: "Viewport meta tag has no content" };
                        }
                        
                        const contentLower = content.toLowerCase();
                        
                        // Check for essential viewport properties
                        const hasDeviceWidth = contentLower.includes('width=device-width') || 
                                             contentLower.includes('width = device-width');
                        const hasInitialScale = contentLower.includes('initial-scale') ||
                                              contentLower.includes('initial-scale=1');
                        
                        // More lenient check - at least one of these should be present
                        if (hasDeviceWidth || hasInitialScale) {
                            return { found: true, content: content };
                        }
                        
                        return { found: false, reason: "Viewport content doesn't include required properties", content: content };
                    }
                """)
                
                return viewport_check["found"]
                
        except Exception as e:
            logger.error(f"Viewport meta check failed: {e}")
            return False
    
    async def _analyze_device_compatibility(self, url: str, include_screenshots: bool = False) -> Dict[str, Any]:
        """Analyze how the website performs across different devices"""
        compatibility_results = {}
        screenshots = {}
        
        for device_type, device_config in self.devices.items():
            try:
                device_name = self.device_names[device_type]
                logger.info(f"Testing device compatibility for {device_name}")
                
                # Use the device configuration directly with BrowserManager
                async with self.browser_manager.get_browser_page(**device_config) as page:
                    start_time = time.time()
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    load_time = time.time() - start_time
                    
                    # Get page dimensions and content - ENHANCED CHECK
                    page_info = await page.evaluate("""
                        () => {
                            const body = document.body;
                            const html = document.documentElement;
                            
                            const scrollWidth = Math.max(
                                body.scrollWidth, body.offsetWidth, 
                                html.clientWidth, html.scrollWidth, html.offsetWidth
                            );
                            
                            const hasSignificantHorizontalScroll = scrollWidth > (window.innerWidth + 20); // 20px tolerance
                            
                            return {
                                scrollWidth: scrollWidth,
                                scrollHeight: Math.max(body.scrollHeight, html.scrollHeight),
                                clientWidth: html.clientWidth,
                                clientHeight: html.clientHeight,
                                hasHorizontalScroll: hasSignificantHorizontalScroll,
                                hasVerticalScroll: document.documentElement.scrollHeight > window.innerHeight,
                                viewportWidth: window.innerWidth,
                                viewportHeight: window.innerHeight,
                                scrollWidthDifference: scrollWidth - window.innerWidth
                            }
                        }
                    """)
                    
                    # More lenient responsive check
                    is_responsive = not page_info["hasHorizontalScroll"] or page_info["scrollWidthDifference"] <= 50
                    
                    compatibility_results[device_type] = {
                        "device_name": device_name,
                        "viewport": device_config["viewport"],
                        "load_time": load_time,
                        "page_dimensions": page_info,
                        "has_horizontal_scroll": page_info["hasHorizontalScroll"],
                        "responsive": is_responsive
                    }
                    
                    # Capture screenshot if requested
                    if include_screenshots:
                        try:
                            screenshot_buffer = await page.screenshot(full_page=True, type="png")
                            screenshots[device_type] = {
                                "device_name": device_name,
                                "data": screenshot_buffer,
                                "dimensions": device_config["viewport"]
                            }
                            logger.info(f"Screenshot captured for {device_name}")
                        except Exception as e:
                            logger.error(f"Screenshot capture failed for {device_name}: {e}")
                    
            except Exception as e:
                logger.error(f"Device analysis failed for {device_type}: {e}")
                compatibility_results[device_type] = {
                    "device_name": self.device_names[device_type],
                    "error": str(e),
                    "responsive": False
                }
        
        return {
            "compatibility": compatibility_results,
            "screenshots": screenshots if include_screenshots else {}
        }
    
    async def _analyze_responsive_design(self, url: str) -> Dict[str, Any]:
        """Analyze responsive design implementation - ENHANCED"""
        try:
            async with self.browser_manager.get_browser_page() as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Enhanced responsive design analysis
                responsive_analysis = await page.evaluate("""
                    () => {
                        let mediaQueries = [];
                        let flexibleElements = 0;
                        let totalElements = 0;
                        let cssFlexGrid = 0;
                        
                        // Check stylesheets for media queries (with error handling)
                        try {
                            const styleSheets = Array.from(document.styleSheets);
                            styleSheets.forEach(sheet => {
                                try {
                                    if (sheet.cssRules && sheet.cssRules.length) {
                                        Array.from(sheet.cssRules).forEach(rule => {
                                            if (rule.type === 4) { // CSSRule.MEDIA_RULE = 4
                                                mediaQueries.push(rule.media.mediaText);
                                            }
                                        });
                                    }
                                } catch (e) {
                                    // Cross-origin or security restrictions - ignore
                                }
                            });
                        } catch (e) {
                            // Fallback: Check for media queries in style tags
                            try {
                                const styleTags = document.querySelectorAll('style');
                                styleTags.forEach(style => {
                                    if (style.textContent && style.textContent.includes('@media')) {
                                        mediaQueries.push('Found in inline styles');
                                    }
                                });
                            } catch (e2) {
                                // Even fallback failed, continue without media queries
                            }
                        }
                        
                        // Check for flexible layouts and modern CSS
                        try {
                            const allElements = Array.from(document.querySelectorAll('*'));
                            totalElements = allElements.length;
                            
                            allElements.forEach(el => {
                                try {
                                    const style = window.getComputedStyle(el);
                                    const display = style.display;
                                    const width = style.width;
                                    const maxWidth = style.maxWidth;
                                    
                                    // Modern layout methods
                                    if (display === 'flex' || display === 'grid') {
                                        cssFlexGrid++;
                                    }
                                    
                                    // Flexible sizing
                                    if (width && (width.includes('%') || width.includes('vw') || width.includes('vh') || width === 'auto') ||
                                        maxWidth && (maxWidth.includes('%') || maxWidth.includes('vw') || maxWidth !== 'none')) {
                                        flexibleElements++;
                                    }
                                } catch (e) {
                                    // Skip elements that cause issues
                                }
                            });
                        } catch (e) {
                            // If element analysis fails, set reasonable defaults
                            totalElements = 100;
                            flexibleElements = 10;
                        }
                        
                        // Check for responsive images
                        let responsiveImages = 0;
                        let totalImages = 0;
                        try {
                            const images = document.querySelectorAll('img');
                            totalImages = images.length;
                            images.forEach(img => {
                                try {
                                    const style = window.getComputedStyle(img);
                                    if ((style.maxWidth === '100%' || style.width === '100%') || 
                                        img.hasAttribute('srcset')) {
                                        responsiveImages++;
                                    }
                                } catch (e) {
                                    // Skip problematic images
                                }
                            });
                        } catch (e) {
                            totalImages = 0;
                            responsiveImages = 0;
                        }
                        
                        // Check for Bootstrap or similar responsive frameworks
                        let hasBootstrap = false;
                        try {
                            hasBootstrap = !!(document.querySelector('.container') || 
                                           document.querySelector('.container-fluid') ||
                                           document.querySelector('[class*="col-"]'));
                        } catch (e) {
                            hasBootstrap = false;
                        }
                        
                        // Check for CSS Grid or Flexbox containers
                        const hasModernLayout = cssFlexGrid > 0;
                        
                        return {
                            mediaQueries: mediaQueries,
                            flexibleElements: flexibleElements,
                            totalElements: totalElements,
                            flexiblePercentage: totalElements > 0 ? (flexibleElements / totalElements) * 100 : 0,
                            cssFlexGrid: cssFlexGrid,
                            responsiveImages: responsiveImages,
                            totalImages: totalImages,
                            hasBootstrap: hasBootstrap,
                            hasModernLayout: hasModernLayout
                        };
                    }
                """)
                
                # Calculate responsive score with better logic
                responsive_score = 0
                issues = []
                
                # Media queries check (25 points)
                if responsive_analysis["mediaQueries"] and len(responsive_analysis["mediaQueries"]) > 0:
                    responsive_score += 25
                elif responsive_analysis["hasBootstrap"] or responsive_analysis["hasModernLayout"]:
                    # Give credit for responsive frameworks even without detectable media queries
                    responsive_score += 20
                else:
                    issues.append("No CSS media queries detected")
                
                # Flexible layout check (30 points)
                flexible_percentage = responsive_analysis["flexiblePercentage"]
                if flexible_percentage > 30:
                    responsive_score += 30
                elif flexible_percentage > 15:
                    responsive_score += 20
                elif flexible_percentage > 5:
                    responsive_score += 10
                else:
                    issues.append("Limited use of flexible layouts")
                
                # Modern CSS layout methods (20 points)
                if responsive_analysis["cssFlexGrid"] > 10:
                    responsive_score += 20
                elif responsive_analysis["cssFlexGrid"] > 0:
                    responsive_score += 15
                
                # Responsive images (15 points)
                if responsive_analysis["totalImages"] > 0:
                    image_responsive_ratio = responsive_analysis["responsiveImages"] / responsive_analysis["totalImages"]
                    if image_responsive_ratio > 0.7:
                        responsive_score += 15
                    elif image_responsive_ratio > 0.3:
                        responsive_score += 10
                    elif image_responsive_ratio > 0:
                        responsive_score += 5
                
                # Viewport meta tag check (10 points) - will be added in overall calculation
                
                return {
                    "score": min(responsive_score, 100),
                    "media_queries": len(responsive_analysis["mediaQueries"]),
                    "flexible_elements": responsive_analysis["flexibleElements"],
                    "flexible_percentage": flexible_percentage,
                    "modern_layout_elements": responsive_analysis["cssFlexGrid"],
                    "responsive_images": responsive_analysis["responsiveImages"],
                    "total_images": responsive_analysis["totalImages"],
                    "has_responsive_framework": responsive_analysis["hasBootstrap"],
                    "issues": issues
                }
                
        except Exception as e:
            logger.error(f"Responsive design analysis failed: {e}")
            return {
                "score": 0,
                "issues": [f"Analysis failed: {str(e)}"]
            }
    
    async def _analyze_touch_friendliness(self, url: str) -> Dict[str, Any]:
        """Analyze touch-friendly design elements - IMPROVED"""
        try:
            mobile_config = self.devices["mobile_phone"]
            async with self.browser_manager.get_browser_page(**mobile_config) as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Enhanced touch analysis
                touch_analysis = await page.evaluate("""
                    () => {
                        const interactiveSelectors = 'a, button, input, select, textarea, [onclick], [role="button"], [tabindex]';
                        const elements = Array.from(document.querySelectorAll(interactiveSelectors));
                        
                        let touchFriendlyCount = 0;
                        let totalElements = elements.length;
                        let smallElements = [];
                        let acceptableElements = 0;
                        
                        const minTouchSize = 44; // Apple's recommended minimum
                        const acceptableSize = 32; // Somewhat acceptable minimum
                        
                        elements.forEach((el, index) => {
                            const rect = el.getBoundingClientRect();
                            
                            // Skip hidden elements
                            if (rect.width === 0 || rect.height === 0) {
                                totalElements--;
                                return;
                            }
                            
                            const area = rect.width * rect.height;
                            const minDimension = Math.min(rect.width, rect.height);
                            
                            if (minDimension >= minTouchSize || area >= (minTouchSize * minTouchSize * 0.7)) {
                                touchFriendlyCount++;
                                acceptableElements++;
                            } else if (minDimension >= acceptableSize || area >= (acceptableSize * acceptableSize)) {
                                acceptableElements++;
                            } else {
                                smallElements.push({
                                    tag: el.tagName.toLowerCase(),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    text: el.textContent ? el.textContent.slice(0, 30) : '',
                                    area: Math.round(area)
                                });
                            }
                        });
                        
                        // Check spacing between elements (more lenient)
                        let crowdedElements = 0;
                        const visibleElements = elements.filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        });
                        
                        visibleElements.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            const nearby = visibleElements.filter(other => {
                                if (other === el) return false;
                                const otherRect = other.getBoundingClientRect();
                                const distance = Math.sqrt(
                                    Math.pow(rect.left - otherRect.left, 2) + 
                                    Math.pow(rect.top - otherRect.top, 2)
                                );
                                return distance < 32; // Reduced from 48px
                            });
                            if (nearby.length > 1) crowdedElements++; // More than 1 nearby element
                        });
                        
                        return {
                            total_interactive: totalElements,
                            touch_friendly: touchFriendlyCount,
                            acceptable_elements: acceptableElements,
                            small_elements: smallElements.slice(0, 10),
                            crowded_elements: crowdedElements,
                            touch_friendly_percentage: totalElements > 0 ? (touchFriendlyCount / totalElements) * 100 : 0,
                            acceptable_percentage: totalElements > 0 ? (acceptableElements / totalElements) * 100 : 0
                        };
                    }
                """)
                
                # Improved scoring logic
                touch_score = 0
                issues = []
                
                acceptable_percentage = touch_analysis["acceptable_percentage"]
                touch_friendly_percentage = touch_analysis["touch_friendly_percentage"]
                
                # Base score on acceptable elements (more lenient)
                if acceptable_percentage >= 85:
                    touch_score = 95
                elif acceptable_percentage >= 75:
                    touch_score = 85
                elif acceptable_percentage >= 60:
                    touch_score = 75
                elif acceptable_percentage >= 40:
                    touch_score = 60
                elif acceptable_percentage >= 20:
                    touch_score = 40
                else:
                    touch_score = 20
                
                # Bonus for optimal touch targets
                if touch_friendly_percentage >= 50:
                    touch_score = min(100, touch_score + 10)
                
                # Issues and penalties
                small_elements_count = len(touch_analysis["small_elements"])
                if small_elements_count > 20:
                    issues.append(f"{small_elements_count} elements are too small for touch")
                    touch_score = max(0, touch_score - 10)
                elif small_elements_count > 10:
                    issues.append(f"{small_elements_count} elements may be difficult to touch")
                    touch_score = max(0, touch_score - 10)
                
                crowded_ratio = touch_analysis["crowded_elements"] / max(touch_analysis["total_interactive"], 1)
                if crowded_ratio > 0.3:
                    issues.append("Many interactive elements are too close together")
                    touch_score = max(0, touch_score - 10)
                elif crowded_ratio > 0.15:
                    issues.append("Some interactive elements may be too close together")
                    touch_score = max(0, touch_score - 5)
                
                return {
                    "score": touch_score,
                    "interactive_elements": touch_analysis["total_interactive"],
                    "touch_friendly_percentage": touch_friendly_percentage,
                    "acceptable_percentage": acceptable_percentage,
                    "small_elements": touch_analysis["small_elements"],
                    "crowded_elements": touch_analysis["crowded_elements"],
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
        """Analyze mobile readability factors - IMPROVED"""
        try:
            mobile_config = self.devices["mobile_phone"]
            async with self.browser_manager.get_browser_page(**mobile_config) as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                readability_analysis = await page.evaluate("""
                    () => {
                        const textElements = Array.from(document.querySelectorAll('p, span, div, li, td, th, h1, h2, h3, h4, h5, h6, a'));
                        let fontSizeIssues = [];
                        let totalTextElements = 0;
                        let readableElements = 0;
                        let acceptableElements = 0;
                        
                        textElements.forEach((el, index) => {
                            const style = window.getComputedStyle(el);
                            const fontSize = parseFloat(style.fontSize);
                            const hasText = el.textContent && el.textContent.trim().length > 0;
                            
                            if (hasText && fontSize > 0) {
                                totalTextElements++;
                                
                                // More lenient readability standards
                                if (fontSize >= 16) { // Ideal for mobile
                                    readableElements++;
                                    acceptableElements++;
                                } else if (fontSize >= 14) { // Acceptable for most content
                                    acceptableElements++;
                                } else if (fontSize >= 12) { // Might be okay for secondary content
                                    // Don't count as acceptable but don't penalize heavily
                                } else {
                                    // Only report very small fonts as issues
                                    fontSizeIssues.push({
                                        tag: el.tagName.toLowerCase(),
                                        fontSize: fontSize,
                                        text: el.textContent.slice(0, 50)
                                    });
                                }
                            }
                        });
                        
                        // Check line height (more lenient)
                        let lineHeightIssues = 0;
                        textElements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            const lineHeight = parseFloat(style.lineHeight);
                            const fontSize = parseFloat(style.fontSize);
                            
                            if (!isNaN(lineHeight) && !isNaN(fontSize) && fontSize > 0) {
                                const ratio = lineHeight / fontSize;
                                if (ratio < 1.2) { // More lenient than 1.4
                                    lineHeightIssues++;
                                }
                            }
                        });
                        
                        // Check for text contrast (basic check)
                        const bodyStyle = window.getComputedStyle(document.body);
                        const hasReadableColors = bodyStyle.color !== bodyStyle.backgroundColor;
                        
                        return {
                            total_text_elements: totalTextElements,
                            readable_elements: readableElements,
                            acceptable_elements: acceptableElements,
                            font_size_issues: fontSizeIssues.slice(0, 10),
                            line_height_issues: lineHeightIssues,
                            readable_percentage: totalTextElements > 0 ? (readableElements / totalTextElements) * 100 : 0,
                            acceptable_percentage: totalTextElements > 0 ? (acceptableElements / totalTextElements) * 100 : 0,
                            has_readable_colors: hasReadableColors
                        };
                    }
                """)
                
                # More balanced scoring
                readability_score = 0
                issues = []
                
                acceptable_percentage = readability_analysis["acceptable_percentage"]
                readable_percentage = readability_analysis["readable_percentage"]
                
                # Base score on acceptable font sizes
                if acceptable_percentage >= 85:
                    readability_score = 90
                elif acceptable_percentage >= 70:
                    readability_score = 80
                elif acceptable_percentage >= 50:
                    readability_score = 70
                elif acceptable_percentage >= 30:
                    readability_score = 55
                else:
                    readability_score = 40
                
                # Bonus for optimal font sizes
                if readable_percentage >= 60:
                    readability_score = min(100, readability_score + 10)
                
                # Issues
                font_issues_count = len(readability_analysis["font_size_issues"])
                if font_issues_count > 10:
                    issues.append(f"{font_issues_count} elements have very small font sizes")
                    readability_score = max(0, readability_score - 15)
                elif font_issues_count > 5:
                    issues.append(f"{font_issues_count} elements may have font sizes that are too small")
                    readability_score = max(0, readability_score - 10)
                
                line_height_ratio = readability_analysis["line_height_issues"] / max(readability_analysis["total_text_elements"], 1)
                if line_height_ratio > 0.5:
                    issues.append("Poor line height spacing detected")
                    readability_score = max(0, readability_score - 10)
                
                return {
                    "score": readability_score,
                    "font_size_issues": readability_analysis["font_size_issues"],
                    "readable_percentage": readable_percentage,
                    "acceptable_percentage": acceptable_percentage,
                    "line_height_issues": readability_analysis["line_height_issues"],
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
            mobile_config = self.devices["mobile_phone"]
            async with self.browser_manager.get_browser_page(**mobile_config) as page:
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
        """Calculate overall mobile-friendliness score - IMPROVED WEIGHTING"""
        scores = []
        weights = []
        
        # Viewport meta tag (10% weight - reduced from 15%)
        if results.get("viewport_meta"):
            scores.append(100)
            weights.append(0.10)
        else:
            scores.append(0)
            weights.append(0.10)
        
        # Responsive design (30% weight - increased from 25%)
        responsive_score = results.get("responsive_design", {}).get("score", 0)
        # Add bonus for viewport meta tag in responsive score
        if results.get("viewport_meta") and responsive_score < 90:
            responsive_score = min(100, responsive_score + 10)
        scores.append(responsive_score)
        weights.append(0.30)
        
        # Touch-friendliness (25% weight - increased from 20%)
        touch_score = results.get("touch_friendly", {}).get("score", 0)
        scores.append(touch_score)
        weights.append(0.25)
        
        # Readability (20% weight - same)
        readability_score = results.get("readability", {}).get("score", 0)
        scores.append(readability_score)
        weights.append(0.20)
        
        # Mobile performance (15% weight - reduced from 20%)
        performance = results.get("mobile_performance", {})
        load_time = performance.get("load_time", 30)
        
        if load_time <= 1.5:
            perf_score = 100
        elif load_time <= 2.5:
            perf_score = 90
        elif load_time <= 4:
            perf_score = 80
        elif load_time <= 6:
            perf_score = 65
        elif load_time <= 10:
            perf_score = 45
        else:
            perf_score = 20
        
        scores.append(perf_score)
        weights.append(0.15)
        
        # Calculate weighted average
        if sum(weights) > 0:
            weighted_score = sum(score * weight for score, weight in zip(scores, weights)) / sum(weights)
            return int(round(weighted_score))
        
        return 0
    
    def _get_mobile_friendly_level(self, score: int) -> str:
        """Get mobile-friendly level based on score - ADJUSTED THRESHOLDS"""
        if score >= 85:
            return "Excellent Mobile Experience"
        elif score >= 70:
            return "Good Mobile Experience"
        elif score >= 55:
            return "Mobile-Friendly"
        elif score >= 35:
            return "Partially Mobile-Friendly"
        else:
            return "Not Mobile-Friendly"
    
    def _identify_critical_issues(self, results: Dict[str, Any]) -> List[str]:
        """Identify critical mobile issues - MORE BALANCED"""
        critical_issues = []
        
        # Viewport meta tag - still critical
        if not results.get("viewport_meta"):
            critical_issues.append("CRITICAL: No viewport meta tag - site will not display properly on mobile")
        
        # Responsive design issues - more nuanced
        device_compatibility = results.get("device_compatibility", {})
        problematic_devices = []
        for device_type, device_data in device_compatibility.items():
            if isinstance(device_data, dict) and device_data.get("has_horizontal_scroll"):
                # Only report as critical if scroll width difference is significant
                page_dims = device_data.get("page_dimensions", {})
                scroll_diff = page_dims.get("scrollWidthDifference", 0)
                if scroll_diff > 100:  # More than 100px difference is concerning
                    problematic_devices.append(device_type)
        
        if problematic_devices:
            critical_issues.append(f"HIGH: Significant horizontal scrolling on {', '.join(problematic_devices)} devices")
        
        # Performance issues - more realistic thresholds
        mobile_performance = results.get("mobile_performance", {})
        load_time = mobile_performance.get("load_time", 0)
        if load_time > 15:
            critical_issues.append("CRITICAL: Mobile page load time exceeds 15 seconds")
        elif load_time > 10:
            critical_issues.append("HIGH: Mobile page load time exceeds 10 seconds")
        elif load_time > 6:
            critical_issues.append("MEDIUM: Mobile page load time could be improved (>6 seconds)")
        
        # Touch-friendliness issues - more reasonable threshold
        touch_data = results.get("touch_friendly", {})
        acceptable_percentage = touch_data.get("acceptable_percentage", touch_data.get("score", 0))
        if acceptable_percentage < 30:
            critical_issues.append("HIGH: Most interactive elements are not touch-friendly")
        elif acceptable_percentage < 50:
            critical_issues.append("MEDIUM: Many interactive elements could be more touch-friendly")
        
        # Readability issues
        readability_data = results.get("readability", {})
        if readability_data.get("acceptable_percentage", 0) < 40:
            critical_issues.append("MEDIUM: Text readability could be improved on mobile")
        
        return critical_issues
    
    def _generate_mobile_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate mobile optimization recommendations - IMPROVED"""
        recommendations = []
        
        # Viewport recommendations
        if not results.get("viewport_meta"):
            recommendations.append("URGENT: Add viewport meta tag: <meta name='viewport' content='width=device-width, initial-scale=1'>")
        
        # Responsive design recommendations
        responsive_data = results.get("responsive_design", {})
        responsive_score = responsive_data.get("score", 0)
        
        if responsive_score < 60:
            if responsive_data.get("media_queries", 0) == 0:
                recommendations.append("Implement CSS media queries for responsive design")
            recommendations.append("Use flexible layouts (CSS Flexbox or Grid) for better mobile adaptation")
        
        # Check for horizontal scrolling issues
        device_compatibility = results.get("device_compatibility", {})
        has_scroll_issues = any(
            device_data.get("has_horizontal_scroll", False) 
            for device_data in device_compatibility.values() 
            if isinstance(device_data, dict)
        )
        if has_scroll_issues:
            recommendations.append("Fix horizontal scrolling by using responsive CSS and flexible widths")
        
        # Performance recommendations
        mobile_performance = results.get("mobile_performance", {})
        load_time = mobile_performance.get("load_time", 0)
        if load_time > 4:
            recommendations.append("Optimize mobile page load time through image compression and code minification")
        elif load_time > 2.5:
            recommendations.append("Consider optimizing images and reducing resource sizes for mobile")
        
        # Touch-friendliness recommendations
        touch_data = results.get("touch_friendly", {})
        touch_score = touch_data.get("score", 0)
        acceptable_percentage = touch_data.get("acceptable_percentage", touch_score)
        
        if acceptable_percentage < 60:
            recommendations.append("Increase touch target sizes to at least 44x44 pixels")
        
        if touch_data.get("crowded_elements", 0) > 10:
            recommendations.append("Add more spacing between interactive elements")
        
        # Readability recommendations
        readability_data = results.get("readability", {})
        readable_percentage = readability_data.get("readable_percentage", 0)
        acceptable_percentage = readability_data.get("acceptable_percentage", 0)
        
        if acceptable_percentage < 70:
            recommendations.append("Increase font sizes to at least 14-16px for better mobile readability")
        
        if len(readability_data.get("font_size_issues", [])) > 5:
            recommendations.append("Review and increase font sizes for small text elements")
        
        # General recommendations based on overall score
        overall_score = results.get("overall_score", 0)
        if overall_score >= 70:
            recommendations.append("Great mobile optimization! Consider testing on additional devices")
        elif not recommendations:
            recommendations.append("Consider implementing mobile-first responsive design principles")
        
        return recommendations[:8]  # Return top 8 recommendations

# Utility function for CLI testing
async def test_mobile_analyzer(url: str = None):
    """Test function for mobile analyzer"""
    browser_manager = BrowserManager(pool_size=3)
    
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
        if load_time <= 1.5:
            perf_score = 100
        elif load_time <= 2.5:
            perf_score = 90
        elif load_time <= 4:
            perf_score = 80
        elif load_time <= 6:
            perf_score = 65
        elif load_time <= 10:
            perf_score = 45
        else:
            perf_score = 20
        
        print(f"Performance Score: {perf_score}/100")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
    finally:
        await browser_manager.cleanup()


def _get_grade(score: int) -> str:
    """Get letter grade from score"""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 35:
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
