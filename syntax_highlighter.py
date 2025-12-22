"""Syntax highlighting for code blocks in DOCX."""

import logging
from typing import List, Tuple

try:
    from pygments import highlight, lex
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.token import Token
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

from docx.shared import RGBColor, Pt

logger = logging.getLogger(__name__)


TOKEN_COLORS = {
    Token.Keyword: RGBColor(0, 0, 255),
    Token.Keyword.Reserved: RGBColor(0, 0, 255),
    Token.Name.Builtin: RGBColor(128, 0, 128),
    Token.Name.Class: RGBColor(0, 128, 128),
    Token.Name.Function: RGBColor(0, 0, 128),
    Token.String: RGBColor(200, 0, 0),
    Token.String.Double: RGBColor(200, 0, 0),
    Token.String.Single: RGBColor(200, 0, 0),
    Token.Comment: RGBColor(0, 128, 0),
    Token.Comment.Single: RGBColor(0, 128, 0),
    Token.Number: RGBColor(128, 64, 0),
    Token.Operator: RGBColor(0, 0, 0),
    Token.Text: RGBColor(0, 0, 0),
}


def get_token_color(token_type) -> RGBColor:
    """Get color for token type, with fallback."""
    if token_type in TOKEN_COLORS:
        return TOKEN_COLORS[token_type]
    
    parent = token_type.parent
    while parent:
        if parent in TOKEN_COLORS:
            return TOKEN_COLORS[parent]
        parent = parent.parent
    
    return RGBColor(0, 0, 0)


def tokenize_code(code: str, language: str = None) -> List[Tuple[str, RGBColor]]:
    """
    Tokenize code and return list of (text, color) tuples.
    
    Args:
        code: Source code
        language: Programming language (python, json, etc)
        
    Returns:
        List of (text, color) tuples for rendering
    """
    if not PYGMENTS_AVAILABLE:
        return [(code, RGBColor(0, 0, 0))]
    
    try:
        if language:
            try:
                lexer = get_lexer_by_name(language)
            except:
                lexer = guess_lexer(code)
        else:
            lexer = guess_lexer(code)
        
        tokens = list(lex(code, lexer))
        result = []
        
        for token_type, token_value in tokens:
            if token_value.strip():
                color = get_token_color(token_type)
                result.append((token_value, color))
        
        return result if result else [(code, RGBColor(0, 0, 0))]
    
    except Exception as e:
        logger.debug(f"Syntax highlighting failed: {e}. Falling back to plain text.")
        return [(code, RGBColor(0, 0, 0))]


def add_highlighted_code_to_paragraph(paragraph, code: str, language: str = None):
    """
    Add syntax-highlighted code to a paragraph.
    
    Args:
        paragraph: python-docx paragraph object
        code: Source code
        language: Programming language
    """
    tokens = tokenize_code(code, language)
    
    for text, color in tokens:
        run = paragraph.add_run(text)
        run.font.name = 'Courier New'
        run.font.size = Pt(9)
        run.font.color.rgb = color
