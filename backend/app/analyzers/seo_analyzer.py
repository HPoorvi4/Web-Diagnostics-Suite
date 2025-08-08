import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SEOAnalyzer:
    def __init__(self, debug=False):
        self.timeout = 15  # Maximum time to wait for page content
        self.debug = debug
        
        # SEO scoring weights
        self.scoring_weights = {
            "title": 0.20,          # 20% - Critical for rankings
            "meta_description": 0.15, # 15% - Important for CTR
            "headings": 0.15,       # 15% - Content structure
            "images": 0.15,         # 15% - Image optimization
            "links": 0.10,          # 10% - Link structure
            "content": 0.15,        # 15% - Content quality
            "technical": 0.10       # 10% - Technical SEO
        }
        
        # SEO best practice thresholds
        self.thresholds = {
            "title_min_length": 30,
            "title_max_length": 60,
            "meta_desc_min_length": 120,
            "meta_desc_max_length": 160,
            "content_min_words": 300,
            "images_with_alt_percentage": 90,
            "internal_links_min": 3
        }
        
        logger.info("SEOAnalyzer initialized")
    
    def _debug_log(self, message: str):
        """Log debug messages if debug mode is enabled."""
        if self.debug:
            print(f"DEBUG: {message}")
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        logger.info(f"Starting SEO analysis for: {url}")
        start_time = time.time()
        
        try:
            # Fetch page content
            html_content, page_info = await self._fetch_page_content(url)
            
            if not html_content:
                return self._create_error_result(url, "Could not fetch page content", time.time() - start_time)
            
            self._debug_log(f"Fetched {len(html_content)} characters of HTML content")
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Analyze different SEO factors
            title_analysis = self._analyze_title(soup, url)
            meta_desc_analysis = self._analyze_meta_description(soup)
            headings_analysis = self._analyze_headings(soup)
            images_analysis = self._analyze_images(soup, url)
            links_analysis = self._analyze_links(soup, url)
            content_analysis = self._analyze_content(soup)
            technical_analysis = self._analyze_technical_seo(soup, page_info)
            
            # Calculate overall SEO score
            seo_score = self._calculate_seo_score(
                title_analysis, meta_desc_analysis, headings_analysis,
                images_analysis, links_analysis, content_analysis, technical_analysis
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                title_analysis, meta_desc_analysis, headings_analysis,
                images_analysis, links_analysis, content_analysis, technical_analysis
            )
            
            # Identify SEO issues
            issues = self._identify_seo_issues(
                title_analysis, meta_desc_analysis, headings_analysis,
                images_analysis, links_analysis, content_analysis, technical_analysis
            )
            
            # Compile final results
            analysis_time = time.time() - start_time
            
            results = {
                "score": seo_score,
                "grade": self._get_grade_from_score(seo_score),
                
                # Core SEO factors
                "title": title_analysis,
                "meta_description": meta_desc_analysis,
                "headings": headings_analysis,
                "images": images_analysis,
                "links": links_analysis,
                "content": content_analysis,
                "technical": technical_analysis,
                
                # Actionable insights
                "recommendations": recommendations,
                "issues": issues,
                "seo_summary": self._create_seo_summary(
                    title_analysis, meta_desc_analysis, headings_analysis,
                    images_analysis, links_analysis, content_analysis
                ),
                
                # Metadata
                "analysis_duration": analysis_time,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "analyzer_version": "1.0.1"
            }
            
            logger.info(f"SEO analysis completed. Score: {seo_score}/100")
            return results
            
        except asyncio.TimeoutError:
            logger.error(f"SEO analysis timed out for {url}")
            return self._create_timeout_result(url, time.time() - start_time)
            
        except Exception as e:
            logger.error(f"SEO analysis failed for {url}: {e}")
            return self._create_error_result(url, str(e), time.time() - start_time)
    
    async def _fetch_page_content(self, url: str) -> tuple:
        """
        Fetch HTML content from the URL.
        Returns both content and response info for analysis.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            # Use proper headers to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    content = await response.text()
                    
                    page_info = {
                        "status_code": response.status,
                        "content_type": response.headers.get('content-type', ''),
                        "final_url": str(response.url),
                        "redirected": str(response.url) != url
                    }
                    
                    self._debug_log(f"Response status: {response.status}")
                    self._debug_log(f"Content type: {page_info['content_type']}")
                    
                    return content, page_info
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching content from {url}")
            return None, None
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return None, None
    
    def _analyze_title(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Analyze the page title tag.
        Title is the most important on-page SEO factor.
        """
        title_tag = soup.find('title')
        
        if not title_tag:
            self._debug_log("No title tag found")
            return {
                "exists": False,
                "text": "",
                "length": 0,
                "score": 0,
                "issues": ["Missing title tag"],
                "recommendations": ["Add a descriptive title tag"]
            }
        
        title_text = title_tag.get_text(strip=True)
        self._debug_log(f"Found title: '{title_text}' (length: {len(title_text)})")
        
        if not title_text:
            return {
                "exists": False,
                "text": "",
                "length": 0,
                "score": 0,
                "issues": ["Empty title tag"],
                "recommendations": ["Add a descriptive title tag"]
            }
        
        title_length = len(title_text)
        
        # Score title based on length and quality
        score = 100
        issues = []
        recommendations = []
        
        # Length checks
        if title_length < self.thresholds["title_min_length"]:
            score -= 30
            issues.append(f"Title too short ({title_length} chars)")
            recommendations.append("Make title longer and more descriptive")
        elif title_length > self.thresholds["title_max_length"]:
            score -= 20
            issues.append(f"Title too long ({title_length} chars)")
            recommendations.append("Shorten title to under 60 characters")
        
        # Quality checks
        if title_text.lower() == urlparse(url).netloc.lower():
            score -= 40
            issues.append("Title is just the domain name")
            recommendations.append("Create descriptive, keyword-rich title")
        
        if not re.search(r'[a-zA-Z]', title_text):
            score -= 50
            issues.append("Title contains no readable text")
        
        # Duplicate word check
        words = title_text.lower().split()
        if len(words) != len(set(words)) and len(words) > 1:
            score -= 10
            issues.append("Title contains duplicate words")
        
        return {
            "exists": True,
            "text": title_text,
            "length": title_length,
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "word_count": len(words)
        }
    
    def _analyze_meta_description(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analyze the meta description tag.
        Critical for search result click-through rates.
        """
        # Look for meta description with different approaches
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'name': 'Description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'})
        
        if not meta_desc:
            self._debug_log("No meta description found")
            return {
                "exists": False,
                "text": "",
                "length": 0,
                "score": 0,
                "issues": ["Missing meta description"],
                "recommendations": ["Add compelling meta description"]
            }
        
        desc_text = meta_desc.get('content', '').strip()
        self._debug_log(f"Found meta description: '{desc_text[:50]}...' (length: {len(desc_text)})")
        
        if not desc_text:
            return {
                "exists": False,
                "text": "",
                "length": 0,
                "score": 0,
                "issues": ["Empty meta description"],
                "recommendations": ["Add compelling meta description"]
            }
        
        desc_length = len(desc_text)
        
        # Score description based on length and quality
        score = 100
        issues = []
        recommendations = []
        
        # Length checks
        if desc_length < self.thresholds["meta_desc_min_length"]:
            score -= 25
            issues.append(f"Meta description too short ({desc_length} chars)")
            recommendations.append("Make meta description longer and more compelling")
        elif desc_length > self.thresholds["meta_desc_max_length"]:
            score -= 15
            issues.append(f"Meta description too long ({desc_length} chars)")
            recommendations.append("Shorten meta description to under 160 characters")
        
        # Quality checks
        if desc_text.lower().count('click here') > 0:
            score -= 20
            issues.append("Contains generic 'click here' text")
        
        # Check for call-to-action words
        cta_words = ['learn', 'discover', 'find', 'get', 'buy', 'try', 'start']
        has_cta = any(word in desc_text.lower() for word in cta_words)
        if not has_cta:
            score -= 10
            recommendations.append("Add call-to-action words to increase clicks")
        
        return {
            "exists": True,
            "text": desc_text,
            "length": desc_length,
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "has_call_to_action": has_cta
        }
    
    def _analyze_headings(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analyze heading structure (H1-H6).
        Proper heading hierarchy helps search engines understand content.
        """
        headings = {"h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}
        
        for level in range(1, 7):
            tags = soup.find_all(f'h{level}')
            headings[f'h{level}'] = [tag.get_text(strip=True) for tag in tags if tag.get_text(strip=True)]
        
        # Count headings
        h1_count = len(headings["h1"])
        total_headings = sum(len(headings[level]) for level in headings)
        
        self._debug_log(f"Found headings - H1: {h1_count}, Total: {total_headings}")
        if h1_count > 0:
            self._debug_log(f"H1 text: '{headings['h1'][0][:50]}...'")
        
        # Score heading structure
        score = 100
        issues = []
        recommendations = []
        
        # H1 checks
        if h1_count == 0:
            score -= 40
            issues.append("Missing H1 tag")
            recommendations.append("Add one H1 tag as main page heading")
        elif h1_count > 1:
            score -= 20
            issues.append(f"Multiple H1 tags ({h1_count})")
            recommendations.append("Use only one H1 tag per page")
        
        # Content structure checks
        if total_headings < 3:
            score -= 15
            issues.append("Few heading tags for content structure")
            recommendations.append("Use more heading tags to structure content")
        
        # Check for proper hierarchy
        has_h2_without_h1 = len(headings["h2"]) > 0 and h1_count == 0
        if has_h2_without_h1:
            score -= 10
            issues.append("H2 tags without H1")
        
        # Check heading lengths
        long_headings = []
        for level in headings:
            for heading in headings[level]:
                if len(heading) > 70:
                    long_headings.append(f"{level.upper()}: {heading[:50]}...")
        
        if long_headings:
            score -= 5
            issues.append("Some headings are too long")
        
        return {
            "structure": headings,
            "h1_count": h1_count,
            "total_count": total_headings,
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "long_headings": long_headings
        }
    
    def _analyze_images(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Analyze image optimization for SEO.
        Images need alt text for accessibility and SEO.
        """
        images = soup.find_all('img')
        total_images = len(images)
        
        self._debug_log(f"Found {total_images} images")
        
        if total_images == 0:
            return {
                "total_count": 0,
                "with_alt": 0,
                "without_alt": 0,
                "score": 100,  # No images is not an SEO penalty
                "issues": [],
                "recommendations": [],
                "alt_percentage": 100
            }
        
        images_with_alt = 0
        images_without_alt = 0
        empty_alt = 0
        large_images = []
        
        for i, img in enumerate(images):
            alt_text = img.get('alt')
            src = img.get('src', '')
            
            if self.debug and i < 3:  # Debug first 3 images
                self._debug_log(f"Image {i+1}: src='{src[:30]}...', alt='{alt_text}'")
            
            if alt_text is not None and alt_text.strip():
                images_with_alt += 1
            else:
                images_without_alt += 1
                if alt_text == '':
                    empty_alt += 1
            
            # Check for large images (basic heuristic)
            if any(size in src.lower() for size in ['large', 'big', 'huge', 'xl']):
                large_images.append(src)
        
        # Calculate metrics
        alt_percentage = (images_with_alt / total_images) * 100 if total_images > 0 else 100
        
        self._debug_log(f"Images with alt: {images_with_alt}/{total_images} ({alt_percentage:.1f}%)")
        
        # Score images
        score = 100
        issues = []
        recommendations = []
        
        if alt_percentage < self.thresholds["images_with_alt_percentage"]:
            penalty = (100 - alt_percentage) * 0.5  # Max 50 point penalty
            score -= penalty
            issues.append(f"{images_without_alt} images missing alt text")
            recommendations.append("Add descriptive alt text to all images")
        
        if empty_alt > 0:
            score -= 10
            issues.append(f"{empty_alt} images have empty alt attributes")
        
        if large_images:
            score -= 5
            recommendations.append("Optimize large images for faster loading")
        
        return {
            "total_count": total_images,
            "with_alt": images_with_alt,
            "without_alt": images_without_alt,
            "empty_alt": empty_alt,
            "alt_percentage": round(alt_percentage, 1),
            "score": max(0, round(score)),
            "issues": issues,
            "recommendations": recommendations,
            "large_images_count": len(large_images)
        }
    
    def _analyze_links(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Analyze link structure and quality.
        Good internal linking helps SEO and user experience.
        """
        links = soup.find_all('a', href=True)
        
        internal_links = []
        external_links = []
        
        domain = urlparse(url).netloc.lower()
        self._debug_log(f"Analyzing links for domain: {domain}")
        
        for link in links:
            href = link.get('href', '').strip()
            link_text = link.get_text(strip=True)
            
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue  # Skip anchor links, javascript, and mailto
            
            # Resolve relative URLs and normalize
            if href.startswith('/'):
                full_url = urljoin(url, href)
                link_domain = domain  # It's a relative link, so same domain
            elif href.startswith('http'):
                full_url = href
                link_domain = urlparse(href).netloc.lower()
            else:
                # Relative path
                full_url = urljoin(url, href)
                link_domain = domain
            
            # Categorize links
            if link_domain == domain:
                internal_links.append({"url": full_url, "text": link_text})
            else:
                external_links.append({"url": full_url, "text": link_text})
        
        self._debug_log(f"Found {len(internal_links)} internal links, {len(external_links)} external links")
        
        # Score link structure
        score = 100
        issues = []
        recommendations = []
        
        # Internal linking checks
        if len(internal_links) < self.thresholds["internal_links_min"]:
            score -= 20
            issues.append(f"Few internal links ({len(internal_links)})")
            recommendations.append("Add more internal links to improve site navigation")
        
        # Check for link text quality
        generic_link_texts = ['click here', 'read more', 'more', 'here', 'link']
        generic_links = 0
        
        for link in internal_links + external_links:
            if link["text"].lower() in generic_link_texts:
                generic_links += 1
        
        if generic_links > 0:
            score -= 15
            issues.append(f"{generic_links} links have generic text")
            recommendations.append("Use descriptive link text instead of 'click here'")
        
        # External link checks
        external_without_nofollow = 0
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('http') and urlparse(href).netloc.lower() != domain:
                rel = link.get('rel', [])
                if isinstance(rel, str):
                    rel = [rel]
                if 'nofollow' not in rel:
                    external_without_nofollow += 1
        
        return {
            "internal_count": len(internal_links),
            "external_count": len(external_links),
            "total_count": len(internal_links) + len(external_links),
            "generic_link_text_count": generic_links,
            "external_without_nofollow": external_without_nofollow,
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations
        }
    
    def _analyze_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analyze content quality and structure.
        Quality content is crucial for SEO rankings.
        """
        # Create a copy to avoid modifying the original
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # Remove script and style elements more comprehensively
        for script in soup_copy(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content area
        main_content = soup_copy.find('main') or soup_copy.find('article') or soup_copy.find('div', class_=re.compile(r'content|main|body', re.I))
        
        if main_content:
            text = main_content.get_text()
        else:
            text = soup_copy.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Count words
        words = [word for word in text.split() if len(word) > 1]  # Filter out single characters
        word_count = len(words)
        
        self._debug_log(f"Content analysis: {word_count} words")
        
        # Calculate reading level (simplified)
        sentences = [s.strip() for s in text.split('.') if s.strip() and len(s.strip()) > 10]
        sentence_count = len(sentences)
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        
        # Score content
        score = 100
        issues = []
        recommendations = []
        
        # Word count checks
        if word_count < self.thresholds["content_min_words"]:
            score -= 30
            issues.append(f"Low word count ({word_count} words)")
            recommendations.append("Add more comprehensive content (aim for 300+ words)")
        
        # Reading difficulty
        if avg_words_per_sentence > 25:
            score -= 10
            issues.append("Sentences may be too complex")
            recommendations.append("Use shorter sentences for better readability")
        
        # Check for duplicate content patterns
        if word_count > 0:
            word_frequency = {}
            for word in words:
                if len(word) > 3:  # Only count meaningful words
                    word_lower = word.lower()
                    word_frequency[word_lower] = word_frequency.get(word_lower, 0) + 1
            
            # Find overused words
            total_meaningful_words = sum(word_frequency.values())
            overused_words = []
            if total_meaningful_words > 0:
                for word, count in word_frequency.items():
                    if count / total_meaningful_words > 0.05:  # More than 5% of content
                        overused_words.append(f"{word} ({count} times)")
            
            if overused_words:
                score -= 5
                issues.append("Some words may be overused")
        else:
            overused_words = []
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": round(avg_words_per_sentence, 1),
            "estimated_reading_time": max(1, round(word_count / 200)),  # 200 WPM average
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "overused_words": overused_words[:3]  # Show top 3
        }
    
    def _analyze_technical_seo(self, soup: BeautifulSoup, page_info: Dict) -> Dict[str, Any]:
        """
        Analyze technical SEO factors.
        """
        score = 100
        issues = []
        recommendations = []
        
        # Check for canonical URL
        canonical = soup.find('link', rel='canonical')
        has_canonical = canonical is not None
        
        if not has_canonical:
            score -= 15
            issues.append("Missing canonical URL")
            recommendations.append("Add canonical URL to prevent duplicate content")
        
        # Check for meta robots
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        robots_content = robots_meta.get('content', '') if robots_meta else ''
        
        if 'noindex' in robots_content.lower():
            score -= 20
            issues.append("Page set to noindex")
        
        # Check for schema markup
        has_json_ld = soup.find('script', type='application/ld+json') is not None
        has_microdata = soup.find(attrs={'itemscope': True}) is not None
        has_schema = has_json_ld or has_microdata
        
        if not has_schema:
            score -= 10
            recommendations.append("Add structured data markup for better search results")
        
        # Check content type
        if 'text/html' not in page_info.get('content_type', ''):
            score -= 25
            issues.append("Non-HTML content type")
        
        self._debug_log(f"Technical SEO - Canonical: {has_canonical}, Schema: {has_schema}")
        
        return {
            "has_canonical": has_canonical,
            "canonical_url": canonical.get('href') if canonical else None,
            "robots_meta": robots_content,
            "has_schema_markup": has_schema,
            "content_type": page_info.get('content_type', ''),
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations
        }
    
    def _calculate_seo_score(self, title_analysis: Dict, meta_desc_analysis: Dict,
                           headings_analysis: Dict, images_analysis: Dict,
                           links_analysis: Dict, content_analysis: Dict,
                           technical_analysis: Dict) -> int:
        """
        Calculate weighted overall SEO score.
        Combines all SEO factors with appropriate weights.
        """
        weighted_score = (
            title_analysis["score"] * self.scoring_weights["title"] +
            meta_desc_analysis["score"] * self.scoring_weights["meta_description"] +
            headings_analysis["score"] * self.scoring_weights["headings"] +
            images_analysis["score"] * self.scoring_weights["images"] +
            links_analysis["score"] * self.scoring_weights["links"] +
            content_analysis["score"] * self.scoring_weights["content"] +
            technical_analysis["score"] * self.scoring_weights["technical"]
        )
        
        return max(0, min(100, round(weighted_score)))
    
    def _generate_recommendations(self, title_analysis: Dict, meta_desc_analysis: Dict,
                                headings_analysis: Dict, images_analysis: Dict,
                                links_analysis: Dict, content_analysis: Dict,
                                technical_analysis: Dict) -> List[str]:
        """Generate prioritized SEO recommendations."""
        all_recommendations = []
        
        # Collect recommendations from all analyses
        for analysis in [title_analysis, meta_desc_analysis, headings_analysis,
                        images_analysis, links_analysis, content_analysis, technical_analysis]:
            all_recommendations.extend(analysis.get("recommendations", []))
        
        # Prioritize critical recommendations
        critical_keywords = ["missing", "add", "fix", "critical"]
        critical_recs = [rec for rec in all_recommendations if any(keyword in rec.lower() for keyword in critical_keywords)]
        other_recs = [rec for rec in all_recommendations if rec not in critical_recs]
        
        # Return top recommendations
        prioritized = critical_recs + other_recs
        return prioritized[:8]  # Return top 8 recommendations
    
    def _identify_seo_issues(self, title_analysis: Dict, meta_desc_analysis: Dict,
                           headings_analysis: Dict, images_analysis: Dict,
                           links_analysis: Dict, content_analysis: Dict,
                           technical_analysis: Dict) -> List[str]:
        """Identify critical SEO issues."""
        all_issues = []
        
        # Collect issues from all analyses
        for analysis in [title_analysis, meta_desc_analysis, headings_analysis,
                        images_analysis, links_analysis, content_analysis, technical_analysis]:
            issues = analysis.get("issues", [])
            all_issues.extend(issues)
        
        return all_issues
    
    def _create_seo_summary(self, title_analysis: Dict, meta_desc_analysis: Dict,
                          headings_analysis: Dict, images_analysis: Dict,
                          links_analysis: Dict, content_analysis: Dict) -> Dict[str, Any]:
        """Create a summary of key SEO metrics."""
        return {
            "has_title": title_analysis.get("exists", False),
            "has_meta_description": meta_desc_analysis.get("exists", False),
            "has_h1": headings_analysis.get("h1_count", 0) > 0,
            "word_count": content_analysis.get("word_count", 0),
            "images_optimized": images_analysis.get("alt_percentage", 0),
            "internal_links": links_analysis.get("internal_count", 0)
        }
    
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
    
    def _create_timeout_result(self, url: str, analysis_time: float) -> Dict[str, Any]:
        """Create result when analysis times out"""
        return {
            "score": 20,
            "grade": "F",
            "title": {"exists": False, "score": 0, "issues": ["Analysis timed out"]},
            "meta_description": {"exists": False, "score": 0, "issues": ["Analysis timed out"]},
            "headings": {"score": 0, "issues": ["Analysis timed out"]},
            "images": {"score": 0, "issues": ["Analysis timed out"]},
            "links": {"score": 0, "issues": ["Analysis timed out"]},
            "content": {"score": 0, "issues": ["Analysis timed out"]},
            "technical": {"score": 0, "issues": ["Analysis timed out"]},
            "recommendations": [
                "Website took too long to analyze",
                "Check if website is accessible and responsive",
                "Improve server response time"
            ],
            "issues": ["CRITICAL: SEO analysis timed out"],
            "analysis_duration": analysis_time,
            "analyzed_at": datetime.utcnow().isoformat(),
            "error": "Analysis timed out"
        }
    
    def _create_error_result(self, url: str, error_msg: str, analysis_time: float) -> Dict[str, Any]:
        """Create result when analysis fails"""
        return {
            "score": 0,
            "grade": "F",
            "title": {"exists": False, "score": 0, "issues": [f"Error: {error_msg}"]},
            "meta_description": {"exists": False, "score": 0, "issues": [f"Error: {error_msg}"]},
            "headings": {"score": 0, "issues": [f"Error: {error_msg}"]},
            "images": {"score": 0, "issues": [f"Error: {error_msg}"]},
            "links": {"score": 0, "issues": [f"Error: {error_msg}"]},
            "content": {"score": 0, "issues": [f"Error: {error_msg}"]},
            "technical": {"score": 0, "issues": [f"Error: {error_msg}"]},
            "recommendations": [
                "Unable to analyze website SEO",
                "Check if URL is accessible",
                "Verify website returns valid HTML content"
            ],
            "issues": [f"CRITICAL: SEO analysis failed - {error_msg}"],
            "analysis_duration": analysis_time,
            "analyzed_at": datetime.utcnow().isoformat(),
            "error": error_msg
        }

# Example usage and testing functions
async def test_seo_analyzer():
    """
    Test function to verify the SEO analyzer works correctly.
    """
    analyzer = SEOAnalyzer(debug=True)  # Enable debug mode
    try:
        # Test with a real website
        print("Testing SEO analysis...")
        results = await analyzer.analyze("https://www.wikipedia.org")
        
        print("\n=== SEO ANALYSIS RESULTS ===")
        print(f"Overall Score: {results['score']}/100 ({results['grade']})")
        print(f"Title: {results['title']['text'][:80]}..." if results['title']['exists'] else "No title")
        print(f"Title Length: {results['title']['length']} chars")
        print(f"Meta Description: {results['meta_description']['text'][:80]}..." if results['meta_description']['exists'] else "No meta description")
        print(f"Meta Description Length: {results['meta_description']['length']} chars")
        print(f"H1 Count: {results['headings']['h1_count']}")
        print(f"Total Headings: {results['headings']['total_count']}")
        print(f"Images: {results['images']['total_count']} ({results['images']['alt_percentage']}% with alt text)")
        print(f"Internal Links: {results['links']['internal_count']}")
        print(f"External Links: {results['links']['external_count']}")
        print(f"Word Count: {results['content']['word_count']}")
        
        print("\n=== COMPONENT SCORES ===")
        print(f"Title: {results['title']['score']}/100")
        print(f"Meta Description: {results['meta_description']['score']}/100")
        print(f"Headings: {results['headings']['score']}/100")
        print(f"Images: {results['images']['score']}/100")
        print(f"Links: {results['links']['score']}/100")
        print(f"Content: {results['content']['score']}/100")
        print(f"Technical: {results['technical']['score']}/100")
        
        print("\n=== TOP RECOMMENDATIONS ===")
        for i, rec in enumerate(results['recommendations'][:5], 1):
            print(f"{i}. {rec}")
        
        if results.get('issues'):
            print("\n=== SEO ISSUES ===")
            for i, issue in enumerate(results['issues'][:5], 1):
                print(f"{i}. {issue}")
        
        # Test with a simpler site for comparison
        print("\n\n=== TESTING WITH EXAMPLE.COM ===")
        results2 = await analyzer.analyze("https://example.com")
        print(f"Example.com Score: {results2['score']}/100 ({results2['grade']})")
        print(f"Title: '{results2['title']['text']}'")
        print(f"Word Count: {results2['content']['word_count']}")
        print(f"Internal Links: {results2['links']['internal_count']}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run test if this file is executed directly
    import asyncio
    asyncio.run(test_seo_analyzer())