"""
Research Co-pilot - Interactive Version (FIXED)
Features:
- LLM responses stored in trace
- Parameter comparison tool
- Terminal-based interface
- Web app support
- Fixed PDF parsing with fallback
- Auto-create config if missing
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TraceLogger:
    """Enhanced trace logger with LLM response storage"""
    
    def __init__(self, trace_file: str):
        self.trace_file = trace_file
        with open(trace_file, 'w') as f:
            f.write("")
    
    def log(self, agent_name: str, action: str, data: Dict[str, Any]):
        """Log action with timestamp"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": action,
            "data": data
        }
        
        with open(self.trace_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        logger.info(f"[{agent_name}] {action}")
    
    def log_llm_interaction(self, agent_name: str, prompt: str, response: str, 
                           model: str, temperature: float, seed: int):
        """Log complete LLM interaction"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": "llm_interaction",
            "data": {
                "model": model,
                "temperature": temperature,
                "seed": seed,
                "prompt_length": len(prompt),
                "response_length": len(response),
                "prompt_hash": hashlib.md5(prompt.encode()).hexdigest(),
                "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "response": response,
                "response_preview": response[:200] + "..." if len(response) > 200 else response
            }
        }
        
        with open(self.trace_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


class PDFParser:
    """Enhanced PDF parser with fallback mechanism"""
    
    def __init__(self, trace_logger: TraceLogger, save_parsed: bool = True):
        self.trace_logger = trace_logger
        self.agent_name = "PDFParser"
        self.save_parsed = save_parsed
        
        self.parsers = []
        try:
            import pymupdf
            self.parsers.append("pymupdf")
        except ImportError:
            pass
        
        try:
            import pdfplumber
            self.parsers.append("pdfplumber")
        except ImportError:
            pass
        
        try:
            import PyPDF2
            self.parsers.append("PyPDF2")
        except ImportError:
            pass
        
        if not self.parsers:
            raise ImportError("No PDF parser available. Install: pip install pymupdf pdfplumber PyPDF2")
        
        logger.info(f"Available parsers: {self.parsers}")
    
    def parse_pdf(self, pdf_path: str, output_dir: str = None) -> Dict[str, Any]:
        """Extract text from PDF with fallback"""
        self.trace_logger.log(self.agent_name, "parse_start", {
            "file": pdf_path,
            "available_parsers": self.parsers
        })
        
        result = None
        last_error = None
        
        # Try parsers in order until one succeeds
        for parser_name in self.parsers:
            try:
                if parser_name == "pymupdf":
                    result = self._parse_with_pymupdf(pdf_path)
                elif parser_name == "pdfplumber":
                    result = self._parse_with_pdfplumber(pdf_path)
                elif parser_name == "PyPDF2":
                    result = self._parse_with_pypdf2(pdf_path)
                
                if result and len(result.get("text", "")) > 0:
                    logger.info(f"Successfully parsed with {parser_name}")
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"{parser_name} failed: {e}, trying next parser...")
                continue
        
        if not result or len(result.get("text", "")) == 0:
            self.trace_logger.log(self.agent_name, "parse_error", {
                "error": f"All parsers failed. Last error: {last_error}"
            })
            raise Exception(f"Failed to parse PDF. Last error: {last_error}")
        
        # Fix spacing issues
        result["text"] = self._fix_spacing(result["text"])
        result["text_length"] = len(result["text"])
        
        # Save parsed content
        if self.save_parsed and output_dir:
            try:
                parsed_file = Path(output_dir) / f"{result['title']}_parsed.txt"
                with open(parsed_file, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {result['title']}\n")
                    f.write(f"Source: {pdf_path}\n")
                    f.write(f"Pages: {result['num_pages']}\n")
                    f.write(f"Parser: {result.get('parser', 'unknown')}\n")
                    f.write(f"{'='*80}\n\n")
                    f.write(result['text'])
                result["parsed_file"] = str(parsed_file)
            except Exception as e:
                logger.warning(f"Failed to save parsed content: {e}")
        
        self.trace_logger.log(self.agent_name, "parse_complete", {
            "title": result['title'],
            "pages": result['num_pages'],
            "text_length": result['text_length'],
            "parser": result.get('parser', 'unknown')
        })
        
        return result
    
    def _fix_spacing(self, text: str) -> str:
        """Fix spacing issues"""
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r',([A-Za-z])', r', \1', text)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\n\n+', '\n\n', text)
        return text
    
    def _parse_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """Parse with PyMuPDF - FIXED VERSION"""
        import pymupdf
        
        title = Path(pdf_path).stem
        full_text = ""
        
        doc = pymupdf.open(pdf_path)
        num_pages = len(doc)  # Store count before iteration
        
        for page_num in range(num_pages):
            page = doc[page_num]
            page_text = page.get_text("text")
            
            if page_text:
                full_text += page_text + "\n"
        
        doc.close()
        
        return {
            "file_path": pdf_path,
            "title": title,
            "num_pages": num_pages,
            "text": full_text,
            "text_length": len(full_text),
            "parser": "pymupdf"
        }
    
    def _parse_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Parse with pdfplumber"""
        import pdfplumber
        
        title = Path(pdf_path).stem
        full_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=3, y_tolerance=3, layout=True)
                if page_text:
                    full_text += page_text + "\n"
        
        return {
            "file_path": pdf_path,
            "title": title,
            "num_pages": num_pages,
            "text": full_text,
            "text_length": len(full_text),
            "parser": "pdfplumber"
        }
    
    def _parse_with_pypdf2(self, pdf_path: str) -> Dict[str, Any]:
        """Parse with PyPDF2"""
        import PyPDF2
        
        title = Path(pdf_path).stem
        full_text = ""
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        return {
            "file_path": pdf_path,
            "title": title,
            "num_pages": num_pages,
            "text": full_text,
            "text_length": len(full_text),
            "parser": "PyPDF2"
        }


class SummarizerAgent:
    """Summarizer with LLM response logging"""
    
    def __init__(self, config: Dict, trace_logger: TraceLogger):
        self.config = config
        self.trace_logger = trace_logger
        self.agent_name = "SummarizerAgent"
        self.model = config["model"]["name"]
        self.temperature = config["model"]["temperature"]
        self.seed = config["model"]["seed"]
    
    def summarize(self, paper_text: str, title: str) -> Dict[str, str]:
        """Create structured summary"""
        try:
            import ollama
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")
        
        text_sample = paper_text[:15000]
        
        system_prompt = "You are a research paper analysis expert."
        user_prompt = f"""Analyze this paper and provide a detailed summary.

Title: {title}

Paper Content:
{text_sample}

Provide:
1. Main Contribution - Primary research contribution
2. Methodology - Methods/approaches used
3. Key Findings - Main results
4. Limitations - Limitations or challenges
5. Future Work - Future directions suggested

Be specific and extract from the paper."""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options={"temperature": self.temperature, "seed": self.seed, "num_predict": 1500}
            )
            
            response_text = response['message']['content']
            
            # Log LLM interaction
            self.trace_logger.log_llm_interaction(
                self.agent_name,
                user_prompt,
                response_text,
                self.model,
                self.temperature,
                self.seed
            )
            
            summary = self._extract_summary_flexibly(response_text, title)
            
            if not summary.get("main_contribution") or summary["main_contribution"] == "Not specified":
                summary = self._create_general_summary(response_text, title)
            
            return summary
        except Exception as e:
            self.trace_logger.log(self.agent_name, "error", {"error": str(e)})
            return self._emergency_summary(paper_text, title)
    
    def _extract_summary_flexibly(self, response: str, title: str) -> Dict[str, str]:
        """Extract summary flexibly"""
        summary = {"title": title, "main_contribution": "", "methodology": "",
                   "key_findings": "", "limitations": "", "future_work": ""}
        
        patterns = {
            "main_contribution": r"(?:1\.|Main Contribution)[:\-\s]*(.+?)(?=\n\n|\n(?:2\.|Methodology)|$)",
            "methodology": r"(?:2\.|Methodology)[:\-\s]*(.+?)(?=\n\n|\n(?:3\.|Key)|$)",
            "key_findings": r"(?:3\.|Key Findings)[:\-\s]*(.+?)(?=\n\n|\n(?:4\.|Limitations)|$)",
            "limitations": r"(?:4\.|Limitations)[:\-\s]*(.+?)(?=\n\n|\n(?:5\.|Future)|$)",
            "future_work": r"(?:5\.|Future Work)[:\-\s]*(.+?)$"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                content = re.sub(r'\s+', ' ', match.group(1).strip())
                if len(content) > 20:
                    summary[field] = content
        
        return summary
    
    def _create_general_summary(self, response: str, title: str) -> Dict[str, str]:
        """Create summary from general text"""
        sentences = re.split(r'(?<=[.!?])\s+', response)
        n = len(sentences)
        return {
            "title": title,
            "main_contribution": ' '.join(sentences[:max(2, n//5)]),
            "methodology": ' '.join(sentences[n//5:2*n//5]) if n > 5 else "See main contribution",
            "key_findings": ' '.join(sentences[2*n//5:3*n//5]) if n > 5 else "See main contribution",
            "limitations": ' '.join(sentences[3*n//5:4*n//5]) if n > 10 else "Not stated",
            "future_work": ' '.join(sentences[4*n//5:]) if n > 10 else "Not stated"
        }
    
    def _emergency_summary(self, paper_text: str, title: str) -> Dict[str, str]:
        """Emergency fallback"""
        summary_text = ' '.join(paper_text.split('\n\n')[:5])[:1000]
        return {
            "title": title,
            "main_contribution": summary_text,
            "methodology": "Error extracting",
            "key_findings": "Error extracting",
            "limitations": "Error extracting",
            "future_work": "Error extracting"
        }


class SynthesisAgent:
    """Synthesizer with LLM logging"""
    
    def __init__(self, config: Dict, trace_logger: TraceLogger):
        self.config = config
        self.trace_logger = trace_logger
        self.agent_name = "SynthesisAgent"
        self.model = config["model"]["name"]
        self.temperature = config["model"]["temperature"]
        self.seed = config["model"]["seed"]
    
    def synthesize(self, summaries: List[Dict]) -> Dict[str, str]:
        """Synthesize cross-paper insights"""
        import ollama
        
        papers_context = ""
        for i, summary in enumerate(summaries, 1):
            papers_context += f"\n=== Paper {i}: {summary.get('title', 'Unknown')} ===\n"
            papers_context += f"Contribution: {summary.get('main_contribution', 'N/A')}\n"
            papers_context += f"Methodology: {summary.get('methodology', 'N/A')}\n"
            papers_context += f"Findings: {summary.get('key_findings', 'N/A')}\n"
        
        prompt = f"""Analyze these {len(summaries)} papers and synthesize:

{papers_context}

Provide:
1. Common Themes - Themes across papers
2. Methodological Trends - Methodological patterns
3. Research Gaps - Unexplored areas
4. Contradictions - Conflicting findings"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research synthesis expert."},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": self.temperature, "seed": self.seed, "num_predict": 1200}
            )
            
            response_text = response['message']['content']
            
            # Log LLM interaction
            self.trace_logger.log_llm_interaction(
                self.agent_name, prompt, response_text,
                self.model, self.temperature, self.seed
            )
            
            return self._parse_synthesis(response_text)
        except Exception as e:
            return {"common_themes": f"Error: {e}", "methodological_trends": "Error",
                    "research_gaps": "Error", "contradictions": "Error"}
    
    def _parse_synthesis(self, response: str) -> Dict[str, str]:
        """Parse synthesis"""
        synthesis = {"common_themes": "", "methodological_trends": "",
                     "research_gaps": "", "contradictions": ""}
        patterns = {
            "common_themes": r"(?:1\.|Common Themes?)[:\-\s]*(.+?)(?=\n\n|\n(?:2\.)|$)",
            "methodological_trends": r"(?:2\.|Methodological)[:\-\s]*(.+?)(?=\n\n|\n(?:3\.)|$)",
            "research_gaps": r"(?:3\.|Research Gaps?)[:\-\s]*(.+?)(?=\n\n|\n(?:4\.)|$)",
            "contradictions": r"(?:4\.|Contradictions?)[:\-\s]*(.+?)$"
        }
        for field, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                synthesis[field] = re.sub(r'\s+', ' ', match.group(1).strip())
        return synthesis


class SurveyGeneratorAgent:
    """Survey generator with LLM logging"""
    
    def __init__(self, config: Dict, trace_logger: TraceLogger):
        self.config = config
        self.trace_logger = trace_logger
        self.agent_name = "SurveyGeneratorAgent"
        self.model = config["model"]["name"]
        self.temperature = config["model"]["temperature"]
        self.seed = config["model"]["seed"]
        self.max_words = config["survey"]["max_words"]
    
    def generate_survey(self, summaries: List[Dict], synthesis: Dict) -> str:
        """Generate mini-survey"""
        import ollama
        
        papers_list = ""
        for i, summary in enumerate(summaries, 1):
            papers_list += f"[{i}] {summary.get('title', 'Unknown')}\n"
            papers_list += f"    {summary.get('main_contribution', 'N/A')[:200]}...\n\n"
        
        prompt = f"""Write a mini-survey (≤{self.max_words} words):

Papers:
{papers_list}

Synthesis: {synthesis.get('common_themes', 'N/A')}

Structure:
1. Introduction
2. Main Approaches (with citations [N])
3. Key Findings (with citations)
4. Research Gaps
5. Conclusion

Use inline citations like [1], [2]."""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Academic writer. ≤{self.max_words} words."},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": self.temperature, "seed": self.seed, "num_predict": 1500}
            )
            
            survey_body = response['message']['content']
            
            # Log LLM interaction
            self.trace_logger.log_llm_interaction(
                self.agent_name, prompt, survey_body,
                self.model, self.temperature, self.seed
            )
            
            references = "\n\n## References\n\n"
            for i, summary in enumerate(summaries, 1):
                references += f"[{i}] {summary.get('title', 'Unknown')}\n"
            
            return survey_body + references
        except Exception as e:
            return f"Error: {e}"


class ParameterComparison:
    """Parameter comparison and optimization tool"""
    
    def __init__(self, base_config: Dict):
        self.base_config = base_config
        self.results = []
    
    def run_comparison(self, pdf_folder: str, parameter_sets: List[Dict]) -> Dict[str, Any]:
        """Run pipeline with different parameter sets"""
        print(f"\n{'='*60}")
        print("Parameter Comparison Tool")
        print(f"{'='*60}\n")
        
        for i, params in enumerate(parameter_sets, 1):
            print(f"Running configuration {i}/{len(parameter_sets)}...")
            print(f"  Temperature: {params['temperature']}, Seed: {params['seed']}")
            
            config = self.base_config.copy()
            config["model"]["temperature"] = params["temperature"]
            config["model"]["seed"] = params["seed"]
            config["output"]["trace_file"] = f"trace_temp{params['temperature']}_seed{params['seed']}.jsonl"
            config["output"]["survey_file"] = f"survey_temp{params['temperature']}_seed{params['seed']}.md"
            
            start_time = datetime.now()
            try:
                copilot = ResearchCopilot(config=config)
                copilot.process_papers(pdf_folder, verbose=False)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                metrics = self._analyze_results(config)
                metrics["temperature"] = params["temperature"]
                metrics["seed"] = params["seed"]
                metrics["duration"] = duration
                metrics["status"] = "success"
                
                self.results.append(metrics)
                print(f"  ✓ Completed in {duration:.2f}s")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                self.results.append({
                    "temperature": params["temperature"],
                    "seed": params["seed"],
                    "status": "error",
                    "error": str(e)
                })
        
        return self._generate_report()
    
    def _analyze_results(self, config: Dict) -> Dict[str, Any]:
        """Analyze quality metrics"""
        with open(config["output"]["survey_file"], 'r') as f:
            survey = f.read()
        
        summaries_dir = Path(config["output"]["summaries_dir"])
        summaries = []
        for summary_file in summaries_dir.glob("*.json"):
            if summary_file.name != "synthesis.json":
                with open(summary_file, 'r') as f:
                    summaries.append(json.load(f))
        
        word_count = len(survey.split())
        citation_count = len(re.findall(r'\[\d+\]', survey))
        avg_summary_length = sum(len(s.get('main_contribution', '').split()) for s in summaries) / len(summaries) if summaries else 0
        
        return {
            "word_count": word_count,
            "citation_count": citation_count,
            "avg_summary_length": avg_summary_length,
            "num_papers": len(summaries)
        }
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comparison report"""
        print(f"\n{'='*60}")
        print("Parameter Comparison Results")
        print(f"{'='*60}\n")
        
        successful = [r for r in self.results if r.get("status") == "success"]
        
        if not successful:
            print("No successful runs to compare.")
            return {"results": self.results}
        
        print(f"{'Temp':<8} {'Seed':<8} {'Words':<8} {'Citations':<10} {'Avg Summary':<12} {'Time(s)':<10}")
        print("-" * 66)
        
        for result in successful:
            print(f"{result['temperature']:<8} {result['seed']:<8} {result['word_count']:<8} "
                  f"{result['citation_count']:<10} {result['avg_summary_length']:<12.1f} {result['duration']:<10.2f}")
        
        best = max(successful, key=lambda x: (x['citation_count'], -abs(x['word_count'] - 800)))
        
        print(f"\n{'='*60}")
        print("Recommended Configuration:")
        print(f"  Temperature: {best['temperature']}")
        print(f"  Seed: {best['seed']}")
        print(f"  Reason: Best citation coverage ({best['citation_count']} citations)")
        print(f"{'='*60}\n")
        
        return {
            "results": self.results,
            "recommended": {
                "temperature": best['temperature'],
                "seed": best['seed']
            }
        }


class ResearchCopilot:
    """Main orchestrator with auto-config creation"""
    
    def __init__(self, config_path: str = "config.json", config: Dict = None):
        if config:
            self.config = config
        else:
            # Auto-create config if missing
            if not os.path.exists(config_path):
                print(f"⚠️  Config file not found. Creating default: {config_path}")
                default_config = {
                    "model": {
                        "name": "llama3.1",
                        "temperature": 0.3,
                        "seed": 42,
                        "max_tokens": 2000
                    },
                    "output": {
                        "trace_file": "trace.jsonl",
                        "summaries_dir": "summaries",
                        "storage_file": "papers_db.json",
                        "survey_file": "mini_survey.md"
                    },
                    "survey": {
                        "max_words": 800,
                        "include_citations": True
                    }
                }
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                print(f"✅ Created {config_path}")
            
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        
        self.trace_logger = TraceLogger(self.config["output"]["trace_file"])
        
        Path(self.config["output"]["summaries_dir"]).mkdir(exist_ok=True)
        self.parsed_dir = Path(self.config["output"]["summaries_dir"]) / "parsed_content"
        self.parsed_dir.mkdir(exist_ok=True)
        
        self.pdf_parser = PDFParser(self.trace_logger, save_parsed=True)
        self.summarizer = SummarizerAgent(self.config, self.trace_logger)
        self.synthesizer = SynthesisAgent(self.config, self.trace_logger)
        self.survey_generator = SurveyGeneratorAgent(self.config, self.trace_logger)
    
    def process_papers(self, pdf_folder: str, verbose: bool = True):
        """Execute pipeline"""
        if verbose:
            print(f"\n{'='*60}\nResearch Co-pilot Pipeline\n{'='*60}\n")
        
        # Parse
        if verbose:
            print("📄 STEP 1: Parsing PDFs...")
        pdf_files = sorted(list(Path(pdf_folder).glob("*.pdf")))
        if not pdf_files:
            raise ValueError(f"No PDFs in {pdf_folder}")
        
        parsed_papers = []
        for i, pdf_file in enumerate(pdf_files, 1):
            if verbose:
                print(f"  [{i}/{len(pdf_files)}] {pdf_file.name}")
            parsed = self.pdf_parser.parse_pdf(str(pdf_file), str(self.parsed_dir))
            parsed_papers.append(parsed)
        
        # Summarize
        if verbose:
            print(f"\n📝 STEP 2: Generating summaries...")
        summaries = []
        for i, paper in enumerate(parsed_papers, 1):
            if verbose:
                print(f"  [{i}/{len(parsed_papers)}] {paper['title']}")
            summary = self.summarizer.summarize(paper["text"], paper["title"])
            summaries.append(summary)
            
            summary_file = Path(self.config["output"]["summaries_dir"]) / f"{paper['title']}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Synthesize
        if verbose:
            print(f"\n🔄 STEP 3: Synthesizing insights...")
        synthesis = self.synthesizer.synthesize(summaries)
        
        synthesis_file = Path(self.config["output"]["summaries_dir"]) / "synthesis.json"
        with open(synthesis_file, 'w', encoding='utf-8') as f:
            json.dump(synthesis, f, indent=2, ensure_ascii=False)
        
        # Survey
        if verbose:
            print(f"\n📋 STEP 4: Generating survey...")
        survey = self.survey_generator.generate_survey(summaries, synthesis)
        
        with open(self.config["output"]["survey_file"], 'w', encoding='utf-8') as f:
            f.write(survey)
        
        if verbose:
            print(f"\n{'='*60}\n✅ Pipeline Complete!\n{'='*60}\n")


def main_interactive():
    """Interactive terminal interface"""
    print("""
╔════════════════════════════════════════════════════════════╗
║         Research Co-pilot - Interactive Mode               ║
║              Multi-Agent Paper Analysis System             ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n" + "="*60)
        print("Main Menu")
        print("="*60)
        print("1. Run Analysis Pipeline")
        print("2. Compare Parameters")
        print("3. View Trace Logs")
        print("4. Exit")
        print("="*60)
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            pdf_folder = input("Enter PDF folder path: ").strip()
            if not os.path.exists(pdf_folder):
                print(f"❌ Folder not found: {pdf_folder}")
                continue
            
            try:
                copilot = ResearchCopilot()
                copilot.process_papers(pdf_folder)
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.exception("Pipeline error")
        
        elif choice == "2":
            pdf_folder = input("Enter PDF folder path: ").strip()
            if not os.path.exists(pdf_folder):
                print(f"❌ Folder not found: {pdf_folder}")
                continue
            
            print("\nEnter parameter sets to compare:")
            print("Format: temp1,seed1 temp2,seed2 ...")
            print("Example: 0.1,42 0.3,42 0.5,42")
            params_input = input("Parameters: ").strip()
            
            try:
                parameter_sets = []
                for pair in params_input.split():
                    temp, seed = pair.split(',')
                    parameter_sets.append({"temperature": float(temp), "seed": int(seed)})
                
                with open("config.json", 'r') as f:
                    base_config = json.load(f)
                
                comparator = ParameterComparison(base_config)
                report = comparator.run_comparison(pdf_folder, parameter_sets)
                
                with open("parameter_comparison_report.json", 'w') as f:
                    json.dump(report, f, indent=2)
                print("\n✓ Report saved to: parameter_comparison_report.json")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.exception("Comparison error")
        
        elif choice == "3":
            trace_file = input("Enter trace file path (default: trace.jsonl): ").strip() or "trace.jsonl"
            if not os.path.exists(trace_file):
                print(f"❌ File not found: {trace_file}")
                continue
            
            print(f"\n{'='*60}")
            print(f"Trace Log: {trace_file}")
            print(f"{'='*60}\n")
            
            with open(trace_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry['action'] == 'llm_interaction':
                        print(f"[{entry['timestamp']}] {entry['agent']} - LLM Call")
                        print(f"  Model: {entry['data']['model']}")
                        print(f"  Temp: {entry['data']['temperature']}, Seed: {entry['data']['seed']}")
                        print(f"  Response: {entry['data']['response_preview']}")
                        print()
                    else:
                        print(f"[{entry['timestamp']}] {entry['agent']}.{entry['action']}")
        
        elif choice == "4":
            print("\nGoodbye!")
            break
        
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            main_interactive()
        else:
            copilot = ResearchCopilot()
            copilot.process_papers(sys.argv[1])
    else:
        main_interactive()
