#!/usr/bin/env python3

import logging
import requests
import time
from pathlib import Path
import yaml
from typing import Dict, List, Any
import os

from crawler import Crawler
from method_extractor import MethodExtractor
from api_parser import APIMethodParser
from categorizer import MethodCategorizer
from docx_generator_v2 import DOCXGeneratorV2
from pdf_converter import PDFConverter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = ['output', 'cache', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    logger.info("✓ All required directories exist")


def fetch_method_urls(method_urls: List[str], config: Dict[str, Any], existing_pages: Dict[str, Dict]) -> Dict[str, Dict]:
    """Fetch all method URLs and cache them"""
    pages = dict(existing_pages)
    
    session = requests.Session()
    session.headers.update({'User-Agent': config['crawler']['user_agent']})
    timeout = config['crawler']['timeout_seconds']
    max_retries = config['crawler']['max_retries']
    retry_backoff = config['crawler']['retry_backoff_factor']
    
    for url in method_urls:
        if url in pages:
            continue
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Fetching method ({attempt}/{max_retries}): {url}")
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                pages[url] = {'raw_html': response.text}
                break
            except requests.RequestException as e:
                wait_time = (retry_backoff ** (attempt - 1))
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    
    return pages


def parse_methods(pages: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Parse HTML pages with APIMethodParser"""
    parser = APIMethodParser()
    methods = []
    
    for url, page_data in pages.items():
        html = page_data.get('raw_html', '')
        if not html:
            continue
        
        method = parser.parse_method_page(html, url)
        if method:
            methods.append(method)
            logger.info(f"✓ Parsed method: {method.get('name')}")
        else:
            if parser.is_method_page(html, url):
                logger.warning(f"Method page detected but parsing failed: {url}")
    
    return methods


def main():
    # Ensure all necessary directories exist
    ensure_directories()
    
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    output_dir = Path(config['output']['output_dir'])
    output_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("STARTING DOCUMENTATION CRAWLER")
    logger.info("=" * 60)
    
    crawler = Crawler()
    pages, errors = crawler.crawl()
    
    logger.info(f"\n✓ Crawled {len(pages)} pages")
    logger.info(f"✗ Errors: {len(errors)}\n")
    
    logger.info("=" * 60)
    logger.info("EXTRACTING METHOD URLS")
    logger.info("=" * 60)
    
    extractor = MethodExtractor()
    method_urls = extractor.extract_method_urls(pages)
    
    if not method_urls:
        logger.error("No method URLs found! Check crawler output.")
        return
    
    logger.info("=" * 60)
    logger.info("FETCHING METHODS")
    logger.info("=" * 60)
    
    pages = fetch_method_urls(method_urls, config, pages)
    
    logger.info("=" * 60)
    logger.info("PARSING METHODS")
    logger.info("=" * 60)
    
    methods = parse_methods(pages)
    logger.info(f"\n✓ Parsed {len(methods)} API methods\n")
    
    if not methods:
        logger.error("No methods parsed! Check extraction.")
        return
    
    logger.info("=" * 60)
    logger.info("CATEGORIZING METHODS")
    logger.info("=" * 60)
    
    categorizer = MethodCategorizer()
    categories = categorizer.categorize_methods(methods)
    categories = categorizer.sort_categories(categories)
    
    for cat_name, cat_methods in categories.items():
        logger.info(f"  {cat_name}: {len(cat_methods)} methods")
    
    logger.info("=" * 60)
    logger.info("GENERATING DOCX")
    logger.info("=" * 60)
    
    docx_gen = DOCXGeneratorV2(config)
    docx_gen.generate(categories)
    
    docx_path = output_dir / config['output']['docx_filename']
    docx_gen.save(str(docx_path))
    
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING PDF")
    logger.info("=" * 60)
    
    pdf_path = None
    if PDFConverter.check_libreoffice_installed():
        pdf_path = PDFConverter.convert(str(docx_path), str(output_dir))
    else:
        logger.warning("LibreOffice not found. PDF generation skipped.")
        logger.info("To enable PDF export, install LibreOffice:")
        logger.info("  Windows: choco install libreoffice")
        logger.info("  Linux: sudo apt-get install libreoffice")
        logger.info("  macOS: brew install libreoffice")
    
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✓ Total URLs crawled: {len(pages)}")
    logger.info(f"✓ Methods parsed: {len(methods)}")
    logger.info(f"✓ Categories: {len(categories)}")
    logger.info(f"✓ DOCX saved: {docx_path}")
    if pdf_path:
        logger.info(f"✓ PDF saved: {pdf_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
