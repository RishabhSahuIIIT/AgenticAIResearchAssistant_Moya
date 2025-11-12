from typing import Dict, Any, List
from pathlib import Path
from tools.pdf_tools import PDFParser
from tools.storage_tools import StorageManager

class PDFParserAgent:
    """Agent responsible for parsing PDF files."""
    
    def __init__(self, storage_manager: StorageManager):
        self.name = "PDFParserAgent"
        self.storage = storage_manager
        self.parser = PDFParser()
        
    def parse_papers(self, pdf_folder: str) -> List[Dict[str, Any]]:
        """
        Parse all PDFs in the given folder.
        
        Args:
            pdf_folder: Path to folder containing PDF files
            
        Returns:
            List of parsed paper data
        """
        folder_path = Path(pdf_folder)
        pdf_files = list(folder_path.glob("*.pdf"))
        
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "parse_papers",
            "num_files": len(pdf_files),
            "folder": str(pdf_folder)
        })
        
        parsed_papers = []
        
        for pdf_file in pdf_files:
            self.storage.log_trace("tool_call", {
                "agent": self.name,
                "tool": "PDFParser.extract_text_from_pdf",
                "file": str(pdf_file)
            })
            
            result = self.parser.extract_text_from_pdf(str(pdf_file))
            
            if result["success"]:
                paper_data = {
                    "filename": pdf_file.name,
                    "text": result["full_text"],
                    "metadata": result["metadata"],
                    "num_pages": result["metadata"]["num_pages"],
                    "timestamp": result["timestamp"]
                }
                parsed_papers.append(paper_data)
                
                # Save parsed paper output
                self._save_parsed_paper(paper_data)
                
                self.storage.log_trace("tool_result", {
                    "agent": self.name,
                    "tool": "PDFParser",
                    "file": pdf_file.name,
                    "success": True,
                    "num_pages": result["metadata"]["num_pages"]
                })
            else:
                self.storage.log_trace("tool_result", {
                    "agent": self.name,
                    "tool": "PDFParser",
                    "file": pdf_file.name,
                    "success": False,
                    "error": result["error"]
                })
        
        # Save summary of all parsed papers
        self._save_parsing_summary(parsed_papers, pdf_folder)
        
        return parsed_papers
    
    def _save_parsed_paper(self, paper_data: Dict[str, Any]):
        """Save individual parsed paper output."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full parsed data as JSON
        filename = f"parsed_{paper_data['filename'].replace('.pdf', '')}_{timestamp}.json"
        filepath = self.storage.run_folder / filename
        
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(paper_data, f, indent=2, ensure_ascii=False)
        
        # Save extracted text separately for easy reading
        text_filename = f"text_{paper_data['filename'].replace('.pdf', '')}_{timestamp}.txt"
        text_filepath = self.storage.run_folder / text_filename
        
        with open(text_filepath, 'w', encoding='utf-8') as f:
            f.write(f"Filename: {paper_data['filename']}\n")
            f.write(f"Title: {paper_data['metadata'].get('title', 'Unknown')}\n")
            f.write(f"Author: {paper_data['metadata'].get('author', 'Unknown')}\n")
            f.write(f"Pages: {paper_data['num_pages']}\n")
            f.write(f"Timestamp: {paper_data['timestamp']}\n")
            f.write("\n" + "="*80 + "\n")
            f.write("EXTRACTED TEXT:\n")
            f.write("="*80 + "\n\n")
            f.write(paper_data['text'])
        
        self.storage.log_trace("parsed_paper_saved", {
            "agent": self.name,
            "paper": paper_data['filename'],
            "json_file": filename,
            "text_file": text_filename
        })
    
    def _save_parsing_summary(self, parsed_papers: List[Dict[str, Any]], pdf_folder: str):
        """Save summary of all parsed papers."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        summary = {
            "timestamp": timestamp,
            "pdf_folder": str(pdf_folder),
            "total_papers": len(parsed_papers),
            "papers": [
                {
                    "filename": p["filename"],
                    "title": p["metadata"].get("title", "Unknown"),
                    "author": p["metadata"].get("author", "Unknown"),
                    "num_pages": p["num_pages"],
                    "text_length": len(p["text"])
                }
                for p in parsed_papers
            ]
        }
        
        filename = f"parsing_summary_{timestamp}.json"
        filepath = self.storage.run_folder / filename
        
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.storage.log_trace("parsing_summary_saved", {
            "agent": self.name,
            "summary_file": filename,
            "total_papers": len(parsed_papers)
        })
