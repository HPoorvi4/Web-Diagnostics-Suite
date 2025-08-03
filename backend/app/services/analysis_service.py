import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

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
        self.security_analyzer = SecurityAnalyzer()
        self.mobile_analyzer = MobileAnalyzer(self.browser_manager)
        
        # Service state
        self._initialized = False
        self._analysis_count = 0
        
        logger.info("AnalysisService initialized")
    
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
            progress_callback: Function to call with progress updates
            
        Returns:
            Complete analysis results with scores and recommendations
        """
        
        if not self.is_ready():
            raise RuntimeError("Analysis service not initialized")
        
        start_time = time.time()
        self._analysis_count += 1
        analysis_id = self._analysis_count
        
        logger.info(f"Starting analysis #{analysis_id} for URL: {url}")
        
        try:
            # Send initial progress
            await self._send_progress(progress_callback, "Initializing analysis...", 0, 
                                    "Setting up analyzers and validating URL")
            
            # Step 1: Run Speed Analysis (25% of work)
            await self._send_progress(progress_callback, "Testing website speed...", 10,
                                    "Measuring page load time and performance metrics")
            
            speed_results = await self._run_with_timeout(
                self.speed_analyzer.analyze(url), 
                timeout=30,
                task_name="Speed Analysis"
            )
            
            await self._send_progress(progress_callback, "Speed analysis complete", 25,
                                    f"Page loads in {speed_results.get('load_time', 0):.1f}s")
            
            # Step 2: Run SEO Analysis (25% of work)
            await self._send_progress(progress_callback, "Analyzing SEO factors...", 30,
                                    "Checking title tags, meta descriptions, and content structure")
            
            seo_results = await self._run_with_timeout(
                self.seo_analyzer.analyze(url),
                timeout=20,
                task_name="SEO Analysis"
            )
            
            await self._send_progress(progress_callback, "SEO analysis complete", 50,
                                    f"Found {len(seo_results.get('issues', []))} SEO issues")
            
            # Step 3: Run Security Analysis (25% of work)
            await self._send_progress(progress_callback, "Testing security features...", 55,
                                    "Checking HTTPS, security headers, and SSL certificate")
            
            security_results = await self._run_with_timeout(
                self.security_analyzer.analyze(url),
                timeout=15,
                task_name="Security Analysis"
            )
            
            await self._send_progress(progress_callback, "Security analysis complete", 75,
                                    f"Security score: {security_results.get('score', 0)}/100")
            
            # Step 4: Run Mobile Analysis (25% of work)
            if include_screenshots:
                await self._send_progress(progress_callback, "Testing mobile compatibility...", 80,
                                        "Taking mobile screenshots and testing responsive design")
                
                mobile_results = await self._run_with_timeout(
                    self.mobile_analyzer.analyze(url, include_screenshots),
                    timeout=25,
                    task_name="Mobile Analysis"
                )
            else:
                # Quick mobile analysis without screenshots
                mobile_results = await self._run_with_timeout(
                    self.mobile_analyzer.analyze(url, False),
                    timeout=10,
                    task_name="Mobile Analysis (No Screenshots)"
                )
            
            await self._send_progress(progress_callback, "Mobile analysis complete", 90,
                                    f"Mobile friendliness score: {mobile_results.get('score', 0)}/100")
            
            # Step 5: Combine Results and Calculate Overall Score
            await self._send_progress(progress_callback, "Calculating final scores...", 95,
                                    "Combining all analysis results")
            
            # Calculate weighted overall score
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
                    "duration": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "include_screenshots": include_screenshots
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
            
            logger.info(f"Analysis #{analysis_id} completed successfully in {total_time:.1f}s. Score: {overall_score}/100")
            
            return final_results
            
        except asyncio.TimeoutError as e:
            error_msg = f"Analysis timed out: {str(e)}"
            logger.error(f"Analysis #{analysis_id} timed out: {e}")
            await self._send_progress(progress_callback, "Analysis timed out", 0, error_msg, error=True)
            raise RuntimeError(error_msg)
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(f"Analysis #{analysis_id} failed: {e}")
            await self._send_progress(progress_callback, "Analysis failed", 0, error_msg, error=True)
            raise
    
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
        
        # Get recommendations from each analyzer
        speed_recs = speed_results.get('recommendations', [])
        seo_recs = seo_results.get('recommendations', [])
        security_recs = security_results.get('recommendations', [])
        mobile_recs = mobile_results.get('recommendations', [])
        
        # Prioritize security and speed recommendations
        all_recommendations.extend(security_recs[:2])  # Top 2 security
        all_recommendations.extend(speed_recs[:2])     # Top 2 speed
        all_recommendations.extend(seo_recs[:2])       # Top 2 SEO
        all_recommendations.extend(mobile_recs[:1])    # Top 1 mobile
        
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
        if security_results.get('score', 100) < 60:
            if not security_results.get('uses_https', True):
                critical_issues.append("Website not using HTTPS - major security risk")
            if not security_results.get('ssl_status', {}).get('valid', True):
                critical_issues.append("SSL certificate issues detected")
        
        # Critical speed issues (score < 50)
        if speed_results.get('score', 100) < 50:
            load_time = speed_results.get('load_time', 0)
            if load_time > 10:
                critical_issues.append(f"Extremely slow loading ({load_time:.1f}s) - users will leave")
            elif load_time > 5:
                critical_issues.append(f"Very slow loading ({load_time:.1f}s) - poor user experience")
        
        # Critical SEO issues (score < 40)
        if seo_results.get('score', 100) < 40:
            if not seo_results.get('title', {}).get('exists', True):
                critical_issues.append("Missing page title - invisible to search engines")
            if not seo_results.get('meta_description', {}).get('exists', True):
                critical_issues.append("Missing meta description - poor search visibility")
        
        # Critical mobile issues (score < 30)
        if mobile_results.get('score', 100) < 30:
            if not mobile_results.get('viewport_meta', True):
                critical_issues.append("Not mobile-friendly - will be penalized by Google")
        
        return critical_issues
    
    async def _send_progress(self, callback: Optional[Callable], stage: str, progress: int, 
                           message: str, error: bool = False):
        """
        Send progress update if callback is provided.
        This is like giving status updates to the customer.
        """
        if callback:
            try:
                await callback(stage, progress, message, error)
            except Exception as e:
                logger.error(f"Error sending progress update: {e}")
                # Don't let progress update errors break the analysis
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "is_ready": self.is_ready(),
            "total_analyses": self._analysis_count,
            "browser_pool_size": self.browser_manager.get_pool_size() if self._initialized else 0,
            "service_uptime": time.time() - getattr(self, '_start_time', time.time())
        }

# Example usage and testing functions
async def test_analysis_service():
    """
    Test function to verify the analysis service works correctly.
    This is like doing a test run in the kitchen before opening.
    """
    service = AnalysisService()
    
    try:
        await service.initialize()
        
        def progress_printer(stage, progress, message, error=False):
            status = "ERROR" if error else "INFO"
            print(f"[{status}] {progress:3d}%: {stage} - {message}")
        
        # Test with a real website
        results = await service.analyze_website(
            url="https://example.com",
            include_screenshots=False,  # Skip screenshots for faster testing
            progress_callback=progress_printer
        )
        
        print("\n=== ANALYSIS RESULTS ===")
        print(f"Overall Score: {results['overall_score']}/100 ({results['overall_grade']})")
        print(f"Speed: {results['speed']['score']}/100")
        print(f"SEO: {results['seo']['score']}/100") 
        print(f"Security: {results['security']['score']}/100")
        print(f"Mobile: {results['mobile']['score']}/100")
        
        print("\n=== TOP RECOMMENDATIONS ===")
        for i, rec in enumerate(results['top_recommendations'], 1):
            print(f"{i}. {rec}")
        
        if results['critical_issues']:
            print("\n=== CRITICAL ISSUES ===")
            for i, issue in enumerate(results['critical_issues'], 1):
                print(f"{i}. {issue}")
        
    finally:
        await service.cleanup()

if __name__ == "__main__":
    # Run test if this file is executed directly
    import asyncio
    asyncio.run(test_analysis_service())