#!/usr/bin/env python3

import logging
from pathlib import Path
import yaml
from crawler import Crawler
from parser import HTMLParser
from docx_generator import DOCXGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    output_dir = Path(config['output']['output_dir'])
    output_dir.mkdir(exist_ok=True)
    
    logger.info("="*70)
    logger.info("FULL DOCUMENTATION CRAWLER - pCloud API")
    logger.info("="*70)
    
    crawler = Crawler()
    pages, errors = crawler.crawl()
    
    logger.info("\n" + "="*70)
    logger.info(f"CRAWL SUMMARY")
    logger.info("="*70)
    logger.info(f"Pages crawled: {len(pages)}")
    logger.info(f"Errors: {len(errors)}")
    
    if errors:
        logger.warning("Failed URLs:")
        for url, error in list(errors.items())[:5]:
            logger.warning(f"  - {url}: {error}")
    
    logger.info("\n" + "="*70)
    logger.info("PARSING HTML")
    logger.info("="*70)
    
    parser = HTMLParser(config)
    pages_data = []
    
    for i, (url, page) in enumerate(pages.items(), 1):
        raw_html = page.get('raw_html', '')
        parsed = parser.parse(raw_html, url)
        pages_data.append(parsed)
        
        elements_count = len(parsed.get('elements', []))
        if elements_count > 0:
            logger.info(f"[{i:3d}/{len(pages)}] {parsed['title'][:50]:50s} ({elements_count} elements)")
        else:
            logger.info(f"[{i:3d}/{len(pages)}] {parsed['title'][:50]:50s} (empty)")
    
    logger.info("\n" + "="*70)
    logger.info("GENERATING DOCX")
    logger.info("="*70)
    
    docx_gen = DOCXGenerator(config)
    docx_gen.generate(pages_data, errors)
    
    docx_path = output_dir / config['output']['docx_filename']
    docx_gen.save(str(docx_path))
    
    logger.info("\n" + "="*70)
    logger.info("FINAL SUMMARY")
    logger.info("="*70)
    logger.info(f"Total pages: {len(pages)}")
    logger.info(f"Errors: {len(errors)}")
    logger.info(f"Output: {docx_path}")
    logger.info(f"Output size: {docx_path.stat().st_size / 1024:.1f} KB")
    logger.info("="*70)


if __name__ == "__main__":
    main()
