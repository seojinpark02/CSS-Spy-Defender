"""
CSS Spy Defender - Chrome/MV3 Performance Evaluation Script

This script measures the overhead of CSS Spy Defender extension
by comparing network traffic and performance metrics with/without the extension.

Based on the original Firefox evaluation script from "Cascading Spy Sheets" (NDSS 2025)
Adapted for Chrome Manifest V3 extensions.

Usage:
    python3 measure_overhead_chrome.py

Output:
    - resultsWithExtension.json
    - resultsWithoutExtension.json
    - correlatedResults.json
"""

import asyncio
import shutil
from json import dumps
from pathlib import Path

from loguru import logger
from playwright._impl._errors import Error, TimeoutError
from playwright.async_api import BrowserContext, Request, Response, async_playwright

# ============================================================================
# Configuration
# ============================================================================

TRANCO_FILE = "tranco_LJ494.csv"
PAGE_TIMEOUT = 20000  # 20 seconds
DOMAIN_AMOUNT = 50    # Number of successful queries to collect

# Chrome extension directory (folder containing manifest.json)
# Adjust this path to point to your CSS Spy Defender extension
EXTENSION_DIR = Path(__file__).resolve().parent.parent / "extension"

# Persistent context user data directory
# Using separate directories to avoid state contamination
USER_DATA_DIR_WITH_EXT = Path(__file__).resolve().parent / ".chrome-profile-with-ext"
USER_DATA_DIR_WITHOUT_EXT = Path(__file__).resolve().parent / ".chrome-profile-without-ext"

# ============================================================================
# Data Classes
# ============================================================================

class QueryError:
    """Stores error information for failed queries."""
    
    def __init__(self):
        self.code = None
        self.error = None

    def request_error(self, code: int) -> None:
        self.code = code

    def exception(self, error: str) -> None:
        self.error = error


class QueryResult:
    """Stores measurement results for a single domain query."""
    
    def __init__(self):
        self.requests = {"accumulatedRequestBodySize": 0, "requestCount": 0}
        self.responses = {"accumulatedResposeBodySize": 0, "responseCount": 0}
        self.error = None
        self.fcp = None
        self.navigationDuration = None
        self.resourceDuration = None

    def add_request(self, request: Request) -> None:
        """Record a network request."""
        self.requests["requestCount"] += 1
        if "content-length" in request.headers:
            self.requests["accumulatedRequestBodySize"] += int(
                request.headers["content-length"]
            )

    def add_response(self, response: Response) -> None:
        """Record a network response."""
        self.responses["responseCount"] += 1
        if "content-length" in response.headers:
            self.responses["accumulatedResposeBodySize"] += int(
                response.headers["content-length"]
            )

    def got_error(self, code: int | None = None, error: str | None = None) -> None:
        """Record an error."""
        if not self.error:
            self.error = QueryError()
        if code:
            self.error.request_error(code)
        if error:
            self.error.exception(error)


# ============================================================================
# Domain Query
# ============================================================================

async def query_domain(context: BrowserContext, domain: str) -> QueryResult:
    """
    Query a single domain and collect performance metrics.
    
    Args:
        context: Playwright browser context
        domain: URL to query (e.g., "https://example.com")
    
    Returns:
        QueryResult with network and performance data
    """
    logger.debug(f"Querying {domain}")
    result = QueryResult()
    page = await context.new_page()
    
    try:
        # Attach network event listeners
        page.on("request", result.add_request)
        page.on("response", result.add_response)

        # Navigate to the domain
        response = await page.goto(url=domain, wait_until="load", timeout=PAGE_TIMEOUT)
        if response and not response.ok:
            result.got_error(code=response.status)

        # Collect Navigation Timing
        navigationPerformance = await page.evaluate(
            "performance.getEntriesByType('navigation')"
        )
        if navigationPerformance and len(navigationPerformance) > 0:
            if "duration" in navigationPerformance[0]:
                result.navigationDuration = navigationPerformance[0]["duration"]

        # Collect Resource Timing (first resource)
        resourcePerformance = await page.evaluate(
            "performance.getEntriesByType('resource')"
        )
        if resourcePerformance and len(resourcePerformance) > 0:
            if "duration" in resourcePerformance[0]:
                result.resourceDuration = resourcePerformance[0]["duration"]

        # Collect First Contentful Paint
        paintPerformance = await page.evaluate(
            "performance.getEntriesByType('paint')"
        )
        if paintPerformance and len(paintPerformance) > 0:
            if "startTime" in paintPerformance[0]:
                result.fcp = paintPerformance[0]["startTime"]

    except TimeoutError:
        result.got_error(error="TimeoutError")
        logger.error(f"Page load timed out for {domain}")
    except Error as e:
        result.got_error(error=str(e))
        logger.error(f"Failed to query {domain}: {str(e)}")
    finally:
        if result.error and result.error.code:
            logger.error(
                f"Received error code {result.error.code} when requesting {domain}"
            )
        await page.close()
    
    return result


# ============================================================================
# Browser Runner
# ============================================================================

async def run_browser(
    domains: list[str], 
    with_extension: bool = False
) -> dict[str, QueryResult]:
    """
    Run browser and query domains with or without extension.
    
    For Chrome/MV3 extensions, we use launch_persistent_context
    with --load-extension flag to automatically load the extension.
    
    Args:
        domains: List of URLs to query
        with_extension: Whether to load CSS Spy Defender extension
    
    Returns:
        Dictionary mapping domain URLs to QueryResult objects
    """
    async with async_playwright() as playwright:
        # Select user data directory based on extension mode
        user_data_dir = USER_DATA_DIR_WITH_EXT if with_extension else USER_DATA_DIR_WITHOUT_EXT
        
        # Clean up previous profile to ensure fresh state
        if user_data_dir.exists():
            shutil.rmtree(user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Build Chrome arguments
        chrome_args = []
        
        if with_extension:
            if not EXTENSION_DIR.exists():
                raise FileNotFoundError(
                    f"Extension directory not found: {EXTENSION_DIR}\n"
                    "Please ensure EXTENSION_DIR points to the folder containing manifest.json"
                )
            logger.info(f"Launching Chrome with CSS Spy Defender extension from {EXTENSION_DIR}")
            chrome_args = [
                f"--disable-extensions-except={EXTENSION_DIR}",
                f"--load-extension={EXTENSION_DIR}",
            ]
        else:
            logger.info("Launching Chrome without extension")
            chrome_args = ["--disable-extensions"]
        
        # Launch persistent context (required for extension loading)
        # Note: headless=False is required for extension support in Chromium
        context = await playwright.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=False,
            args=chrome_args,
        )
        
        try:
            # Wait a moment for extension to initialize
            if with_extension:
                logger.info("Waiting for extension to initialize...")
                await asyncio.sleep(2)
            
            results: dict[str, QueryResult] = {}
            successful_queries = 0
            
            for domain in domains:
                if successful_queries >= DOMAIN_AMOUNT:
                    break
                
                result = await query_domain(context, domain)
                results[domain] = result
                
                if not result.error:
                    successful_queries += 1
                    logger.info(f"[{successful_queries}/{DOMAIN_AMOUNT}] Successfully queried {domain}")
                else:
                    logger.warning(f"Failed to query {domain}, skipping...")
        
        finally:
            await context.close()
        
        return results


# ============================================================================
# Data Processing
# ============================================================================

def parse_domains(filename: str = TRANCO_FILE) -> list[str]:
    """
    Parse domain list from Tranco CSV file.
    
    Args:
        filename: Path to Tranco CSV file
    
    Returns:
        List of URLs with https:// prefix
    """
    with open(filename) as fp:
        domains = ["https://" + line.strip().split(",")[-1] for line in fp.readlines()]
    return domains


def evaluate_requests(
    results: dict[str, QueryResult]
) -> dict[str, dict[str, int | float]]:
    """
    Extract measurement data from QueryResult objects.
    
    Args:
        results: Dictionary of domain -> QueryResult
    
    Returns:
        Dictionary of domain -> measurement metrics
    """
    evaluated_requests = dict()
    
    for domain, query_result in results.items():
        # Skip domains with non-timeout errors
        if query_result.error and query_result.error.error != "TimeoutError":
            logger.error(f"Error for {domain}: {query_result.error.error}")
            continue

        domain_result = {
            "requestCount": query_result.requests["requestCount"],
            "responseCount": query_result.responses["responseCount"],
        }

        if "accumulatedRequestBodySize" in query_result.requests:
            domain_result["accumulatedRequestBodySize"] = query_result.requests[
                "accumulatedRequestBodySize"
            ]

        if "accumulatedResposeBodySize" in query_result.responses:
            domain_result["accumulatedResposeBodySize"] = query_result.responses[
                "accumulatedResposeBodySize"
            ]

        if query_result.navigationDuration:
            domain_result["navigationDuration"] = query_result.navigationDuration

        if query_result.resourceDuration:
            domain_result["resourceDuration"] = query_result.resourceDuration

        if query_result.fcp:
            domain_result["fcp"] = query_result.fcp

        evaluated_requests[domain] = domain_result
    
    return evaluated_requests


def correlate_results(
    results_with_ext: dict[str, dict[str, int | float]],
    results_without_ext: dict[str, dict[str, int | float]],
) -> dict[str, dict[str, int | float]]:
    """
    Calculate the difference between with-extension and without-extension results.
    
    Args:
        results_with_ext: Measurements with extension enabled
        results_without_ext: Measurements without extension
    
    Returns:
        Dictionary of domain -> metric differences (with - without)
    """
    common_domains = set(results_with_ext.keys()).intersection(set(results_without_ext.keys()))
    correlated_results = {}
    
    for domain in common_domains:
        correlated_results[domain] = {
            key: results_with_ext[domain][key] - results_without_ext[domain][key]
            for key in set(results_with_ext[domain].keys()).intersection(
                set(results_without_ext[domain].keys())
            )
        }
    
    return correlated_results


def write_results(results: dict[str, dict[str, int | float]], filename: str) -> None:
    """Write results dictionary to JSON file."""
    with open(filename, "w") as fp:
        fp.write(dumps(results, indent=4))


# ============================================================================
# Main
# ============================================================================

async def main():
    """Main entry point for the evaluation script."""
    
    # Parse domain list
    domains = parse_domains()
    logger.info(f"Loaded {len(domains)} domains from {TRANCO_FILE}")
    
    # Crawl WITH extension
    logger.info("=" * 60)
    logger.info("Starting Chrome crawl WITH CSS Spy Defender extension")
    logger.info("=" * 60)
    results_with_ext = await run_browser(domains, with_extension=True)
    evaluated_with_ext = evaluate_requests(results_with_ext)
    logger.info(f"Collected {len(evaluated_with_ext)} successful measurements with extension")
    
    # Crawl WITHOUT extension (only domains that succeeded with extension)
    logger.info("=" * 60)
    logger.info("Starting Chrome crawl WITHOUT extension")
    logger.info("=" * 60)
    crawled_domains = list(results_with_ext.keys())
    results_without_ext = await run_browser(crawled_domains, with_extension=False)
    evaluated_without_ext = evaluate_requests(results_without_ext)
    logger.info(f"Collected {len(evaluated_without_ext)} successful measurements without extension")
    
    # Calculate differences
    correlated_results = correlate_results(evaluated_with_ext, evaluated_without_ext)
    logger.info(f"Correlated {len(correlated_results)} common domains")
    
    # Write results
    logger.info("Writing results to files...")
    write_results(evaluated_with_ext, "resultsWithExtension.json")
    write_results(evaluated_without_ext, "resultsWithoutExtension.json")
    write_results(correlated_results, "correlatedResults.json")
    
    logger.info("Done! Run 'python3 stats.py' to see statistics.")


if __name__ == "__main__":
    asyncio.run(main())
