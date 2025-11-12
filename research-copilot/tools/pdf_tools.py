import pymupdf
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

class PDFParser:
    """Tool for parsing PDF research papers."""
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> Dict[str, any]:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            doc = pymupdf.open(pdf_path)
            
            full_text = []
            page_texts = []
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                page_texts.append({
                    "page_number": page_num + 1,
                    "text": text
                })
                full_text.append(text)
            
            metadata = {
                "filename": Path(pdf_path).name,
                "num_pages": len(doc),
                "title": doc.metadata.get("title", "Unknown"),
                "author": doc.metadata.get("author", "Unknown"),
                "subject": doc.metadata.get("subject", ""),
            }
            
            doc.close()
            
            return {
                "success": True,
                "full_text": "\n\n".join(full_text),
                "pages": page_texts,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def extract_sections(text: str) -> Dict[str, str]:
        """
        Attempt to extract common paper sections (heuristic-based).
        
        Args:
            text: Full text of the paper
            
        Returns:
            Dictionary with extracted sections
        """
        sections = {}
        common_headers = [
            "abstract",
            "introduction",
            "related work",
            "methodology",
            "method",
            "approach",
            "results",
            "evaluation",
            "discussion",
            "conclusion",
            "future work",
            "references"
        ]
        
        text_lower = text.lower()
        
        for header in common_headers:
            # Simple heuristic: find section headers
            if header in text_lower:
                sections[header] = "detected"
        
        return sections
# PDF extraction tools
