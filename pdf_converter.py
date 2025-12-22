"""Convert DOCX to PDF using LibreOffice."""

import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFConverter:
    """Convert DOCX to PDF using LibreOffice Headless."""
    
    @staticmethod
    def check_libreoffice_installed() -> bool:
        """Check if LibreOffice is installed."""
        try:
            result = subprocess.run(
                ['soffice', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def convert(docx_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Convert DOCX to PDF using LibreOffice.
        
        Args:
            docx_path: Path to DOCX file
            output_dir: Output directory (default: same as DOCX)
            
        Returns:
            Path to generated PDF, or None if failed
        """
        docx_path = Path(docx_path)
        
        if not docx_path.exists():
            logger.error(f"DOCX file not found: {docx_path}")
            return None
        
        output_dir = output_dir or str(docx_path.parent)
        pdf_path = Path(output_dir) / docx_path.stem
        
        logger.info(f"Converting to PDF: {docx_path}")
        logger.debug(f"Output directory: {output_dir}")
        
        try:
            result = subprocess.run(
                [
                    'soffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', output_dir,
                    str(docx_path)
                ],
                capture_output=True,
                timeout=120,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"LibreOffice conversion failed: {result.stderr}")
                return None
            
            pdf_file = Path(output_dir) / f"{docx_path.stem}.pdf"
            
            if pdf_file.exists():
                logger.info(f"✓ PDF created: {pdf_file}")
                logger.info(f"  Size: {pdf_file.stat().st_size / 1024:.1f} KB")
                return str(pdf_file)
            else:
                logger.error(f"PDF file not found after conversion: {pdf_file}")
                return None
        
        except FileNotFoundError:
            logger.error(
                "LibreOffice not installed. Install with:\n"
                "  Windows: choco install libreoffice\n"
                "  Linux: sudo apt-get install libreoffice\n"
                "  macOS: brew install libreoffice"
            )
            return None
        
        except subprocess.TimeoutExpired:
            logger.error("LibreOffice conversion timed out (>120s)")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error during conversion: {e}")
            return None


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    if not PDFConverter.check_libreoffice_installed():
        logger.error("LibreOffice is not installed or not in PATH")
        exit(1)
    
    logger.info("LibreOffice is installed ✓")
