import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
import os
import sys
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Import analyzers
from analyzers.speed_analyzer import SpeedAnalyzer
from analyzers.seo_analyzer import SEOAnalyzer
from analyzers.security_analyzer import SecurityAnalyzer
from analyzers.mobile_analyzer import MobileAnalyzer

# Import utilities
from utils.browser_manager import BrowserManager
from models import GradeCalculator


logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Main service that coordinates all website analysis.
    Think of this as the PROJECT MANAGER who assigns tasks to different specialists.
    """
    
    def __init__(self):
        # Initialize browser manager (shared across all analyzers)
        self.browser_manager = BrowserManager()
        
        # Initialize all analyzers
        self.speed_analyzer = SpeedAnalyzer(self.browser_manager)
        self.seo_analyzer = SEOAnalyzer()
        self.security_analyzer = SecurityAnalyzer(self.browser_manager)
        self.mobile_analyzer = MobileAnalyzer(self.browser_manager)
        
        # Service state
        self._initialized = False
        self._analysis_count = 0
        self._start_time = time.time()
        
        logger.info("AnalysisService initialized")
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to ensure it has proper protocol.
        """
        if not url.startswith(('http://', 'https://')):
            # Default to https for better security
            url = f"https://{url}"
        
        # Validate URL structure
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception as e:
            raise ValueError(f"Invalid URL: {e}")
            
        return url
    
    async def initialize(self):
        """
        Initialize the service and browser pool.
        This is like warming up the kitchen before service starts.
        """
        try:
            await self.browser_manager.initialize()
            self._initialized = True
            logger.info("AnalysisService initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize AnalysisService: {e}")
            raise
    
    async def cleanup(self):
        """
        Clean up resources when shutting down.
        This is like cleaning the kitchen after service ends.
        """
        try:
            await self.browser_manager.cleanup()
            self._initialized = False
            logger.info("AnalysisService cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def is_ready(self) -> bool:
        """Check if service is ready to handle requests"""
        return self._initialized and self.browser_manager.is_ready()
    
    async def analyze_website(
        self, 
        url: str, 
        include_screenshots: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Main method to analyze a website.
        This coordinates all the different analyzers and combines their results.
        
        Args:
            url: Website URL to analyze
            include_screenshots: Whether to take mobile/desktop screenshots
            progress_callback: Function to call with progress updates (can be sync or async)
            
        Returns:
            Complete analysis results with scores and recommendations
        """
        
        if not self.is_ready():
            raise RuntimeError("Analysis service not initialized")
        
        # Normalize URL
        try:
            url = self._normalize_url(url)
        except ValueError as e:
            await self._send_progress(progress_callback, "Invalid URL", 0, str(e), error=True)
            raise
        
        start_time = time.time()
        self._analysis_count += 1
        analysis_id = self._analysis_count
        
        logger.info(f"Starting analysis #{analysis_id} for URL: {url}")
        
        # Initialize results with fallback values
        speed_results = {"score": 0, "recommendations": [], "error": "Not completed"}
        seo_results = {"score": 0, "recommendations": [], "error": "Not completed"}
        security_results = {"score": 0, "recommendations": [], "error": "Not completed"}
        mobile_results = {"score": 0, "recommendations": [], "error": "Not completed"}
        
        try:
            # Send initial progress
            await self._send_progress(progress_callback, "Initializing analysis...", 0, 
                                    "Setting up analyzers and validating URL")
            
            # Step 1: Run Speed Analysis (25% of work)
            await self._send_progress(progress_callback, "Testing website speed...", 10,
                                    "Measuring page load time and performance metrics")
            
            try:
                speed_results = await self._run_with_timeout(
                    self.speed_analyzer.analyze(url), 
                    timeout=45,  # Increased timeout
                    task_name="Speed Analysis"
                )
                await self._send_progress(progress_callback, "Speed analysis complete", 25,
                                        f"Page loads in {speed_results.get('load_time', 0):.1f}s")
            except Exception as e:
                logger.error(f"Speed analysis failed: {e}")
                speed_results["error"] = str(e)
                await self._send_progress(progress_callback, "Speed analysis failed", 25,
                                        f"Error: {str(e)}", error=True)
            
            # Step 2: Run SEO Analysis (25% of work)
            await self._send_progress(progress_callback, "Analyzing SEO factors...", 30,
                                    "Checking title tags, meta descriptions, and content structure")
            
            try:
                seo_results = await self._run_with_timeout(
                    self.seo_analyzer.analyze(url),
                    timeout=30,  # Increased timeout
                    task_name="SEO Analysis"
                )
                await self._send_progress(progress_callback, "SEO analysis complete", 50,
                                        f"Found {len(seo_results.get('issues', []))} SEO issues")
            except Exception as e:
                logger.error(f"SEO analysis failed: {e}")
                seo_results["error"] = str(e)
                await self._send_progress(progress_callback, "SEO analysis failed", 50,
                                        f"Error: {str(e)}", error=True)
            
            # Step 3: Run Security Analysis (25% of work)
            await self._send_progress(progress_callback, "Testing security features...", 55,
                                    "Checking HTTPS, security headers, and SSL certificate")
            
            try:
                security_results = await self._run_with_timeout(
                    self.security_analyzer.analyze(url),
                    timeout=30,  # Increased timeout
                    task_name="Security Analysis"
                )
                await self._send_progress(progress_callback, "Security analysis complete", 75,
                                        f"Security score: {security_results.get('score', 0)}/100")
            except Exception as e:
                logger.error(f"Security analysis failed: {e}")
                security_results["error"] = str(e)
                await self._send_progress(progress_callback, "Security analysis failed", 75,
                                        f"Error: {str(e)}", error=True)
            
            # Step 4: Run Mobile Analysis (25% of work)
            if include_screenshots:
                await self._send_progress(progress_callback, "Testing mobile compatibility...", 80,
                                        "Taking mobile screenshots and testing responsive design")
                timeout = 40  # Longer timeout for screenshots
            else:
                timeout = 20
            
            try:
                mobile_results = await self._run_with_timeout(
                    self.mobile_analyzer.analyze_mobile_friendliness(url, include_screenshots),
                    timeout=timeout,
                    task_name="Mobile Analysis"
                )
                await self._send_progress(progress_callback, "Mobile analysis complete", 90,
                                        f"Mobile friendliness score: {mobile_results.get('score', 0)}/100")
            except Exception as e:
                logger.error(f"Mobile analysis failed: {e}")
                mobile_results["error"] = str(e)
                await self._send_progress(progress_callback, "Mobile analysis failed", 90,
                                        f"Error: {str(e)}", error=True)
            
            # Step 5: Combine Results and Calculate Overall Score
            await self._send_progress(progress_callback, "Calculating final scores...", 95,
                                    "Combining all analysis results")
            
            # Calculate weighted overall score (only from successful analyses)
            overall_score = self._calculate_overall_score(
                speed_results.get('score', 0),
                seo_results.get('score', 0), 
                security_results.get('score', 0),
                mobile_results.get('score', 0)
            )
            
            # Combine all results
            final_results = {
                "overall_score": overall_score,
                "overall_grade": GradeCalculator.get_grade(overall_score),
                "speed": speed_results,
                "seo": seo_results,
                "security": security_results,
                "mobile": mobile_results,
                "analysis_metadata": {
                    "analysis_id": analysis_id,
                    "url": url,
                    "original_url": url if url != self._normalize_url(url) else url,
                    "duration": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "include_screenshots": include_screenshots,
                    "errors": self._get_analysis_errors(speed_results, seo_results, security_results, mobile_results)
                },
                "top_recommendations": self._extract_top_recommendations(
                    speed_results, seo_results, security_results, mobile_results
                ),
                "critical_issues": self._extract_critical_issues(
                    speed_results, seo_results, security_results, mobile_results
                )
            }
            
            # Final progress update
            total_time = time.time() - start_time
            await self._send_progress(progress_callback, "Analysis complete!", 100,
                                    f"Analysis completed in {total_time:.1f} seconds. Overall score: {overall_score}/100")
            
            logger.info(f"Analysis #{analysis_id} completed in {total_time:.1f}s. Score: {overall_score}/100")
            
            return final_results
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(f"Analysis #{analysis_id} failed: {e}")
            await self._send_progress(progress_callback, "Analysis failed", 0, error_msg, error=True)
            
            # Return partial results if we have any
            total_time = time.time() - start_time
            return {
                "overall_score": 0,
                "overall_grade": "F",
                "speed": speed_results,
                "seo": seo_results,
                "security": security_results,
                "mobile": mobile_results,
                "analysis_metadata": {
                    "analysis_id": analysis_id,
                    "url": url,
                    "duration": total_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "include_screenshots": include_screenshots,
                    "fatal_error": str(e)
                },
                "top_recommendations": [],
                "critical_issues": [f"Analysis failed: {str(e)}"]
            }
    
    def _get_analysis_errors(self, *results) -> list:
        """Extract errors from analysis results"""
        errors = []
        for result in results:
            if isinstance(result, dict) and "error" in result:
                errors.append(result["error"])
        return errors
    
    async def _run_with_timeout(self, coro, timeout: int, task_name: str):
        """
        Run an analyzer with a timeout to prevent hanging.
        This is like setting a timer for each kitchen task.
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"{task_name} timed out after {timeout} seconds")
            raise asyncio.TimeoutError(f"{task_name} took too long to complete")
        except asyncio.CancelledError:
            logger.error(f"{task_name} was cancelled")
            raise asyncio.TimeoutError(f"{task_name} was cancelled")
    
    def _calculate_overall_score(self, speed: int, seo: int, security: int, mobile: int) -> int:
        """
        Calculate weighted overall score.
        Different aspects have different importance weights.
        
        Weights:
        - Speed: 35% (most important for user experience)
        - SEO: 25% (important for visibility)
        - Security: 25% (important for trust)
        - Mobile: 15% (important but often dependent on design)
        """
        weights = {
            "speed": 0.35,
            "seo": 0.25,
            "security": 0.25,
            "mobile": 0.15
        }
        
        weighted_score = (
            speed * weights["speed"] +
            seo * weights["seo"] +
            security * weights["security"] +
            mobile * weights["mobile"]
        )
        
        # Ensure score is between 0 and 100
        return max(0, min(100, round(weighted_score)))
    
    def _extract_top_recommendations(self, speed_results: Dict, seo_results: Dict, 
                                   security_results: Dict, mobile_results: Dict) -> list:
        """
        Extract the most important recommendations from all analyzers.
        Returns top 5 recommendations prioritized by impact.
        """
        all_recommendations = []
        
        # Get recommendations from each analyzer (skip failed analyses)
        for results in [security_results, speed_results, seo_results, mobile_results]:
            if isinstance(results, dict) and "error" not in results:
                all_recommendations.extend(results.get('recommendations', [])[:2])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in all_recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:5]  # Return top 5
    
    def _extract_critical_issues(self, speed_results: Dict, seo_results: Dict,
                               security_results: Dict, mobile_results: Dict) -> list:
        """
        Extract critical issues that need immediate attention.
        These are issues that significantly impact the website.
        """
        critical_issues = []
        
        # Critical security issues (score < 60)
        if security_results.get('score', 0) > 0 and security_results.get('score', 100) < 60:
            if not security_results.get('uses_https', True):
                critical_issues.append("Website not using HTTPS - major security risk")
            if not security_results.get('ssl_status', {}).get('valid', True):
                critical_issues.append("SSL certificate issues detected")
        
        # Critical speed issues (score < 50)
        if speed_results.get('score', 0) > 0 and speed_results.get('score', 100) < 50:
            load_time = speed_results.get('load_time', 0)
            if load_time > 10:
                critical_issues.append(f"Extremely slow loading ({load_time:.1f}s) - users will leave")
            elif load_time > 5:
                critical_issues.append(f"Very slow loading ({load_time:.1f}s) - poor user experience")
        
        # Critical SEO issues (score < 40)
        if seo_results.get('score', 0) > 0 and seo_results.get('score', 100) < 40:
            if not seo_results.get('title', {}).get('exists', True):
                critical_issues.append("Missing page title - invisible to search engines")
            if not seo_results.get('meta_description', {}).get('exists', True):
                critical_issues.append("Missing meta description - poor search visibility")
        
        # Critical mobile issues (score < 30)
        if mobile_results.get('score', 0) > 0 and mobile_results.get('score', 100) < 30:
            if not mobile_results.get('viewport_meta', True):
                critical_issues.append("Not mobile-friendly - will be penalized by Google")
        
        return critical_issues
    
    async def _send_progress(self, callback: Optional[Callable], stage: str, progress: int, 
                           message: str, error: bool = False):
        """
        Send progress update if callback is provided.
        This handles both sync and async callbacks.
        """
        if callback:
            try:
                # Check if callback is async
                if asyncio.iscoroutinefunction(callback):
                    await callback(stage, progress, message, error)
                else:
                    # Call sync function
                    callback(stage, progress, message, error)
            except Exception as e:
                logger.error(f"Error sending progress update: {e}")
                # Don't let progress update errors break the analysis
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "is_ready": self.is_ready(),
            "total_analyses": self._analysis_count,
            "browser_pool_size": self.browser_manager.get_pool_size() if self._initialized else 0,
            "service_uptime": time.time() - self._start_time
        }

# Example usage and testing functions
async def test_analysis_service():
    """
    Test function to verify the analysis service works correctly.
    This is like doing a test run in the kitchen before opening.
    """
    service = AnalysisService()
    
    try:
        print("Initializing analysis service...")
        await service.initialize()
        
        def progress_printer(stage, progress, message, error=False):
            """Sync progress callback function"""
            status = "ERROR" if error else "INFO"
            print(f"[{status}] {progress:3d}%: {stage} - {message}")
        
        # Test with a real website (with proper protocol)
        test_url = "https://www.wikipedia.org"  # Use .org instead of .com for better reliability
        print(f"\nTesting analysis with URL: {test_url}")
        
        results = await service.analyze_website(
            url=test_url,
            include_screenshots=False,  # Skip screenshots for faster testing
            progress_callback=progress_printer
        )
        
        print("\n" + "="*50)
        print("ANALYSIS RESULTS")
        print("="*50)
        print(f"Overall Score: {results['overall_score']}/100 ({results['overall_grade']})")
        print(f"Analysis Duration: {results['analysis_metadata']['duration']:.1f} seconds")
        print()
        print("Individual Scores:")
        print(f"  Speed: {results['speed']['score']}/100")
        print(f"  SEO: {results['seo']['score']}/100") 
        print(f"  Security: {results['security']['score']}/100")
        print(f"  Mobile: {results['mobile']['score']}/100")
        
        # Show errors if any
        errors = results['analysis_metadata'].get('errors', [])
        if errors:
            print(f"\nAnalysis Errors:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        
        if results['top_recommendations']:
            print(f"\nTop Recommendations:")
            for i, rec in enumerate(results['top_recommendations'], 1):
                print(f"  {i}. {rec}")
        
        if results['critical_issues']:
            print(f"\nCritical Issues:")
            for i, issue in enumerate(results['critical_issues'], 1):
                print(f"  {i}. {issue}")
        
        print(f"\nService Stats:")
        stats = service.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        await service.cleanup()
        print("Cleanup complete!")

if __name__ == "__main__":
    # Run test if this file is executed directly
    import sys
    
    # Allow URL to be passed as command line argument
    test_url = "https://www.wikipedia.org"
    if len(sys.argv) > 1:
        # Normalize the URL from command line
        input_url = sys.argv[1]
        if not input_url.startswith(('http://', 'https://')):
            test_url = f"https://{input_url}"
        else:
            test_url = input_url
    
    print(f"Running analysis service test with URL: {test_url}")
    
    async def test_with_url():
        service = AnalysisService()
        try:
            await service.initialize()
            
            def progress_printer(stage, progress, message, error=False):
                status = "ERROR" if error else "INFO"
                print(f"[{status}] {progress:3d}%: {stage} - {message}")
            
            results = await service.analyze_website(
                url=test_url,
                include_screenshots=False,
                progress_callback=progress_printer
            )
            
            print(f"\nOverall Score: {results['overall_score']}/100 ({results['overall_grade']})")
            
        finally:
            await service.cleanup()
    
    asyncio.run(test_with_url())