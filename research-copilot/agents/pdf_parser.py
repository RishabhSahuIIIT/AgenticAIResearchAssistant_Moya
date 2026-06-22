import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from tools.pdf_tools import PDFParser
from tools.storage_tools import StorageManager
from agents.base_agent import BaseAgent


class PDFParserAgent(BaseAgent):
    """Agent responsible for parsing PDF files and persisting extracted text.

    If cache_dir is provided, parsed results are stored there keyed by PDF stem.
    On the next run, if the cached file is newer than the PDF, extraction is
    skipped and the cached data is returned instead — useful when re-running
    with changed prompts without re-paying the PyMuPDF extraction cost.
    """

    def __init__(self, storage_manager: StorageManager, cache_dir: Optional[Path] = None):
        super().__init__("PDFParserAgent", storage_manager)
        self.parser = PDFParser()
        self.cache_dir = cache_dir

    def parse_papers(self, pdf_folder: str) -> List[Dict[str, Any]]:
        """
        Parse all PDFs in the given folder.

        Validates the folder before processing: checks existence, that it is a
        directory, and that it contains at least one .pdf file.

        Args:
            pdf_folder: Path to a directory containing .pdf files

        Returns:
            List of parsed paper dicts; empty list if validation fails or all PDFs error
        """
        folder_path = Path(pdf_folder)

        if not folder_path.exists():
            print(f"  ✗ Folder not found: {pdf_folder}")
            self.storage.log_trace("parse_error", {"reason": "folder_not_found", "path": str(pdf_folder)})
            return []
        if not folder_path.is_dir():
            print(f"  ✗ Path is not a directory: {pdf_folder}")
            self.storage.log_trace("parse_error", {"reason": "not_a_directory", "path": str(pdf_folder)})
            return []

        pdf_files = list(folder_path.glob("*.pdf"))
        if not pdf_files:
            print(f"  ✗ No PDF files found in: {pdf_folder}")
            self.storage.log_trace("parse_error", {"reason": "no_pdf_files", "path": str(pdf_folder)})
            return []

        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "parse_papers",
            "num_files": len(pdf_files),
            "folder": str(pdf_folder),
        })

        parsed_papers = []
        for pdf_file in pdf_files:
            cached = self._load_from_cache(pdf_file)
            if cached is not None:
                print(f"  ↩ Using cached parse for '{pdf_file.name}' (PDF unchanged)")
                self.storage.log_trace("tool_result", {
                    "agent": self.name,
                    "tool": "PDFParser",
                    "file": pdf_file.name,
                    "success": True,
                    "source": "cache",
                    "num_pages": cached.get("num_pages"),
                })
                parsed_papers.append(cached)
                self.storage.save_parsed_paper(cached)
                continue

            self.storage.log_trace("tool_call", {
                "agent": self.name,
                "tool": "PDFParser.extract_text_from_pdf",
                "file": str(pdf_file),
            })

            result = self.parser.extract_text_from_pdf(str(pdf_file))

            if result["success"]:
                paper_data = {
                    "filename": pdf_file.name,
                    "text": result["full_text"],
                    "metadata": result["metadata"],
                    "num_pages": result["metadata"]["num_pages"],
                    "timestamp": result["timestamp"],
                }
                parsed_papers.append(paper_data)
                self.storage.save_parsed_paper(paper_data)
                self._save_to_cache(pdf_file.stem, paper_data)
                self.storage.log_trace("tool_result", {
                    "agent": self.name,
                    "tool": "PDFParser",
                    "file": pdf_file.name,
                    "success": True,
                    "source": "extracted",
                    "num_pages": result["metadata"]["num_pages"],
                })
            else:
                self.storage.log_trace("tool_result", {
                    "agent": self.name,
                    "tool": "PDFParser",
                    "file": pdf_file.name,
                    "success": False,
                    "error": result["error"],
                })

        self.storage.save_parsing_summary(parsed_papers, pdf_folder)
        return parsed_papers

    def _load_from_cache(self, pdf_file: Path) -> Optional[Dict[str, Any]]:
        """Return cached parse data if cache is present and newer than the PDF, else None."""
        if self.cache_dir is None:
            return None
        cache_path = self.cache_dir / f"parsed_{pdf_file.stem}.json"
        if not cache_path.exists():
            return None
        if pdf_file.stat().st_mtime > cache_path.stat().st_mtime:
            return None  # PDF was modified after the cache was written
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    def _save_to_cache(self, pdf_stem: str, paper_data: Dict[str, Any]) -> None:
        """Persist parsed paper data to the cache directory."""
        if self.cache_dir is None:
            return
        cache_path = self.cache_dir / f"parsed_{pdf_stem}.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(paper_data, f, indent=2, ensure_ascii=False)
