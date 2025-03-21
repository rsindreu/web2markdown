import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
import logging
import trafilatura

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self, base_url: str, max_depth: int = 3):
        """
        Initialize the web crawler.
        
        Args:
            base_url (str): The starting URL to crawl from
            max_depth (int): Maximum depth of pages to crawl
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.pages: Dict[str, Dict] = {}
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to the same domain and path as base_url."""
        base_parsed = urlparse(self.base_url)
        url_parsed = urlparse(url)
        return (base_parsed.netloc == url_parsed.netloc and 
                url_parsed.path.startswith(base_parsed.path))
    
    def get_page_content(self, url: str) -> Optional[Dict]:
        """Fetch and parse a single page using trafilatura for smart content extraction."""
        try:
            # Set up headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            # Download content using requests
            try:
                response = requests.get(url, headers=headers, timeout=10, stream=True) # Use stream=True
                response.raise_for_status()
                downloaded_bytes = response.content # Get the raw bytes
                downloaded = downloaded_bytes.decode(response.apparent_encoding) # Use apparent encoding
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {str(e)}")
                
            # Extract the main content and metadata
            content = trafilatura.extract(
                downloaded,
                include_links=True,
                include_formatting=True,
                include_images=True,
                output_format='markdown',
                with_metadata=True
            )
            
            if not content:
                logger.warning(f"Could not extract content from {url}")
                return None
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(downloaded)
            
            # Extract links
            soup = BeautifulSoup(downloaded, 'html.parser')
            links = [urljoin(url, link.get('href')) 
                    for link in soup.find_all('a', href=True) 
                    if self.is_valid_url(urljoin(url, link.get('href')))]
            
            return {
                'title': metadata.title if metadata else '',
                'content': content,
                'links': links,
                'metadata': {
                    'author': metadata.author if metadata else None,
                    'date': metadata.date if metadata else None,
                    'description': metadata.description if metadata else None,
                    'sitename': metadata.sitename if metadata else None,
                    'categories': metadata.categories if metadata else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
            
    def crawl(self) -> Dict[str, Dict]:
        """
        Start crawling from the base URL.
        
        Returns:
            Dict[str, Dict]: Dictionary of crawled pages with their content
        """
        def _crawl_recursive(url: str, depth: int = 0):
            if (depth >= self.max_depth or 
                url in self.visited_urls or 
                not self.is_valid_url(url)):
                return
                
            logger.info(f"Crawling: {url}")
            self.visited_urls.add(url)
            
            page_content = self.get_page_content(url)
            if page_content:
                self.pages[url] = page_content
                for link in page_content['links']:
                    _crawl_recursive(link, depth + 1)
        
        _crawl_recursive(self.base_url)
        return self.pages
