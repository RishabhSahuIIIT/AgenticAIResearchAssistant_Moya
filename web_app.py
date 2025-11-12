"""
Web interface for Research Co-pilot - COMPLETE WITH UNIQUE RUNS & FULL LLM DISPLAY
Features:
- Each run creates unique timestamped directory
- Complete LLM responses viewable in UI (loads from files)
- Dynamic parameter comparison
- Full observability
Run with: streamlit run web_app.py
"""

import streamlit as st
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime
import pandas as pd
import shutil

sys.path.append('.')
from research_copilot_interactive import ResearchCopilot, ParameterComparison

st.set_page_config(page_title="Research Co-pilot", layout="wide", page_icon="🔬")

# Initialize session state
if 'param_configs' not in st.session_state:
    st.session_state.param_configs = [
        {"id": 1, "temperature": 0.1, "seed": 42},
        {"id": 2, "temperature": 0.3, "seed": 42},
        {"id": 3, "temperature": 0.5, "seed": 42}
    ]
    st.session_state.next_id = 4

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #00cc66;
    }
    .stage-complete {
        color: #00cc66;
        font-weight: bold;
    }
    .stage-active {
        color: #ff9933;
        font-weight: bold;
        animation: pulse 1.5s ease-in-out infinite;
    }
    .stage-pending {
        color: #666666;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .param-config-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .llm-response-box {
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 15px;
        margin: 10px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 Research Co-pilot - Multi-Agent Paper Analysis")
st.markdown("Analyze research papers and generate comprehensive mini-surveys with full observability")

# Sidebar
st.sidebar.header("⚙️ Configuration")

# Upload PDFs
uploaded_files = st.sidebar.file_uploader(
    "📄 Upload PDF Papers (5-6 papers)",
    type=['pdf'],
    accept_multiple_files=True
)

# Model settings
st.sidebar.markdown("### 🤖 Model Settings")
model = st.sidebar.selectbox("Model", ["llama3.1", "gemma"])
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1, 
                                help="Lower = more focused, Higher = more creative")
seed = st.sidebar.number_input("Seed", value=42, step=1, 
                               help="Fixed seed for reproducibility")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📄 Analysis", 
    "🔬 Parameter Comparison", 
    "📊 Trace Logs",
    "📁 Execution Summaries",
    "📖 Help"
])

def create_run_directory():
    """Create unique timestamped directory for this run"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = Path(f"web_run_{timestamp}")
    run_dir.mkdir(exist_ok=True)
    return run_dir, timestamp

def load_llm_response_from_file(response_file_path):
    """Load complete LLM response from file"""
    try:
        if os.path.exists(response_file_path):
            with open(response_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "File not found"
    except Exception as e:
        return f"Error loading file: {e}"

with tab1:
    st.header("Paper Analysis Pipeline")
    
    if uploaded_files:
        st.success(f"✅ Uploaded {len(uploaded_files)} papers")
        
        # Show uploaded files
        with st.expander("📋 Uploaded Files", expanded=False):
            for f in uploaded_files:
                st.text(f"• {f.name}")
        
        # Create unique run directory
        run_dir, run_timestamp = create_run_directory()
        
        st.info(f"📁 Output directory: `{run_dir}/`")
        
        # Save uploaded files
        upload_dir = run_dir / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        for uploaded_file in uploaded_files:
            uploaded_file.seek(0)  # Reset file pointer
            with open(upload_dir / uploaded_file.name, 'wb') as f:
                f.write(uploaded_file.read())
        
        if st.button("🚀 Run Analysis", type="primary"):
            
            # Create progress containers
            progress_container = st.container()
            console_container = st.expander("📋 Console Output", expanded=True)
            results_container = st.container()
            
            with progress_container:
                st.markdown("### 🔄 Pipeline Progress")
                
                overall_progress = st.progress(0)
                overall_status = st.empty()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    stage1_status = st.empty()
                    stage1_time = st.empty()
                with col2:
                    stage2_status = st.empty()
                    stage2_time = st.empty()
                with col3:
                    stage3_status = st.empty()
                    stage3_time = st.empty()
                with col4:
                    stage4_status = st.empty()
                    stage4_time = st.empty()
                
                stage1_status.markdown("⏳ **Stage 1**: Parsing")
                stage2_status.markdown('<span class="stage-pending">⏸️ Stage 2: Summarization</span>', unsafe_allow_html=True)
                stage3_status.markdown('<span class="stage-pending">⏸️ Stage 3: Synthesis</span>', unsafe_allow_html=True)
                stage4_status.markdown('<span class="stage-pending">⏸️ Stage 4: Survey</span>', unsafe_allow_html=True)
            
            with console_container:
                console_output = st.empty()
                console_log = []
            
            def log_console(message):
                timestamp = datetime.now().strftime("%H:%M:%S")
                console_log.append(f"[{timestamp}] {message}")
                console_output.code("\n".join(console_log[-50:]))
                print(f"[WEB APP] {message}")
            
            try:
                pipeline_start = datetime.now()
                
                # Create unique subdirectories for this run
                summaries_dir = run_dir / "summaries"
                summaries_dir.mkdir(exist_ok=True)
                
                llm_responses_dir = run_dir / "llm_responses"
                llm_responses_dir.mkdir(exist_ok=True)
                
                # Create config with unique paths
                config = {
                    "model": {
                        "name": model, 
                        "temperature": temperature, 
                        "seed": seed, 
                        "max_tokens": 2000
                    },
                    "output": {
                        "trace_file": str(run_dir / "trace.jsonl"),
                        "summaries_dir": str(summaries_dir),
                        "storage_file": str(run_dir / "papers_db.json"),
                        "survey_file": str(run_dir / "survey.md")
                    },
                    "survey": {
                        "max_words": 800, 
                        "include_citations": True
                    }
                }
                
                log_console("=" * 60)
                log_console("🚀 Research Co-pilot Pipeline Starting")
                log_console(f"Run ID: {run_timestamp}")
                log_console(f"Output Directory: {run_dir}")
                log_console(f"Started: {pipeline_start.strftime('%Y-%m-%d %H:%M:%S')}")
                log_console("=" * 60)
                overall_status.text("Initializing pipeline...")
                
                # Create copilot with custom LLM response directory
                copilot = ResearchCopilot(config=config)
                # Override the response directory
                copilot.response_dir = llm_responses_dir
                copilot.trace_logger.response_dir = llm_responses_dir
                
                log_console(f"✅ Configuration: Model={model}, Temp={temperature}, Seed={seed}")
                log_console(f"✅ LLM responses will be saved to: {llm_responses_dir}")
                
                # STAGE 1: PDF Parsing
                log_console("\n" + "=" * 60)
                log_console("📄 STAGE 1: Parsing PDF Files")
                log_console("=" * 60)
                stage1_status.markdown('<span class="stage-active">⚙️ Stage 1: Parsing (Active)</span>', unsafe_allow_html=True)
                overall_status.text("Stage 1/4: Parsing PDFs...")
                overall_progress.progress(0.05)
                
                stage1_start = datetime.now()
                
                pdf_files = sorted(list(Path(upload_dir).glob("*.pdf")))
                log_console(f"Found {len(pdf_files)} PDF files")
                
                parsed_papers = []
                for i, pdf_file in enumerate(pdf_files, 1):
                    log_console(f"  [{i}/{len(pdf_files)}] Parsing: {pdf_file.name}")
                    parsed = copilot.pdf_parser.parse_pdf(str(pdf_file), str(copilot.parsed_dir))
                    parsed_papers.append(parsed)
                    overall_progress.progress(0.05 + (0.20 * i / len(pdf_files)))
                
                stage1_end = datetime.now()
                stage1_duration = (stage1_end - stage1_start).total_seconds()
                
                log_console(f"✅ Stage 1 Complete: {len(parsed_papers)} papers in {stage1_duration:.2f}s")
                stage1_status.markdown('<span class="stage-complete">✅ Stage 1: Parsing</span>', unsafe_allow_html=True)
                stage1_time.markdown(f'<div class="metric-box">⏱️ {stage1_duration:.2f}s</div>', unsafe_allow_html=True)
                
                # STAGE 2: Summarization
                log_console("\n" + "=" * 60)
                log_console("📝 STAGE 2: Generating Structured Summaries")
                log_console("=" * 60)
                stage2_status.markdown('<span class="stage-active">⚙️ Stage 2: Summarization (Active)</span>', unsafe_allow_html=True)
                overall_status.text("Stage 2/4: Generating summaries...")
                overall_progress.progress(0.25)
                
                stage2_start = datetime.now()
                
                summaries = []
                for i, paper in enumerate(parsed_papers, 1):
                    log_console(f"  [{i}/{len(parsed_papers)}] Summarizing: {paper['title']}")
                    summary = copilot.summarizer.summarize(paper["text"], paper["title"])
                    summary["generated_timestamp"] = datetime.now().isoformat()
                    summary["stage"] = "summarization"
                    summaries.append(summary)
                    
                    summary_file = summaries_dir / f"{paper['title']}.json"
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)
                    
                    log_console(f"      ✓ Summary saved: {summary_file.name}")
                    overall_progress.progress(0.25 + (0.30 * i / len(parsed_papers)))
                
                stage2_end = datetime.now()
                stage2_duration = (stage2_end - stage2_start).total_seconds()
                
                log_console(f"✅ Stage 2 Complete: {len(summaries)} summaries in {stage2_duration:.2f}s")
                stage2_status.markdown('<span class="stage-complete">✅ Stage 2: Summarization</span>', unsafe_allow_html=True)
                stage2_time.markdown(f'<div class="metric-box">⏱️ {stage2_duration:.2f}s</div>', unsafe_allow_html=True)
                
                # STAGE 3: Synthesis
                log_console("\n" + "=" * 60)
                log_console("🔄 STAGE 3: Synthesizing Cross-Paper Insights")
                log_console("=" * 60)
                stage3_status.markdown('<span class="stage-active">⚙️ Stage 3: Synthesis (Active)</span>', unsafe_allow_html=True)
                overall_status.text("Stage 3/4: Synthesizing insights...")
                overall_progress.progress(0.55)
                
                stage3_start = datetime.now()
                
                synthesis = copilot.synthesizer.synthesize(summaries)
                synthesis["generated_timestamp"] = datetime.now().isoformat()
                synthesis["stage"] = "synthesis"
                synthesis["num_papers_analyzed"] = len(summaries)
                
                synthesis_file = summaries_dir / "synthesis.json"
                with open(synthesis_file, 'w', encoding='utf-8') as f:
                    json.dump(synthesis, f, indent=2, ensure_ascii=False)
                
                stage3_end = datetime.now()
                stage3_duration = (stage3_end - stage3_start).total_seconds()
                
                log_console(f"✅ Stage 3 Complete: Synthesis in {stage3_duration:.2f}s")
                stage3_status.markdown('<span class="stage-complete">✅ Stage 3: Synthesis</span>', unsafe_allow_html=True)
                stage3_time.markdown(f'<div class="metric-box">⏱️ {stage3_duration:.2f}s</div>', unsafe_allow_html=True)
                overall_progress.progress(0.75)
                
                # STAGE 4: Survey Generation
                log_console("\n" + "=" * 60)
                log_console("📋 STAGE 4: Generating Mini-Survey")
                log_console("=" * 60)
                stage4_status.markdown('<span class="stage-active">⚙️ Stage 4: Survey (Active)</span>', unsafe_allow_html=True)
                overall_status.text("Stage 4/4: Generating survey...")
                overall_progress.progress(0.80)
                
                stage4_start = datetime.now()
                
                survey = copilot.survey_generator.generate_survey(summaries, synthesis)
                
                survey_timestamp = datetime.now().isoformat()
                word_count = len(survey.split())
                pipeline_duration = (datetime.now() - pipeline_start).total_seconds()
                
                survey_with_metadata = f"""---
title: Research Paper Mini-Survey
run_id: {run_timestamp}
generated: {survey_timestamp}
papers_analyzed: {len(summaries)}
word_count: {word_count}
model: {config['model']['name']}
temperature: {config['model']['temperature']}
seed: {config['model']['seed']}
---

{survey}

---
Generated by Research Co-pilot
Run ID: {run_timestamp}
Timestamp: {survey_timestamp}
Pipeline Duration: {pipeline_duration:.2f}s
---
"""
                
                with open(config["output"]["survey_file"], 'w', encoding='utf-8') as f:
                    f.write(survey_with_metadata)
                
                stage4_end = datetime.now()
                stage4_duration = (stage4_end - stage4_start).total_seconds()
                
                log_console(f"✅ Stage 4 Complete: Survey in {stage4_duration:.2f}s")
                stage4_status.markdown('<span class="stage-complete">✅ Stage 4: Survey</span>', unsafe_allow_html=True)
                stage4_time.markdown(f'<div class="metric-box">⏱️ {stage4_duration:.2f}s</div>', unsafe_allow_html=True)
                overall_progress.progress(1.0)
                
                # Final summary
                pipeline_end = datetime.now()
                total_duration = (pipeline_end - pipeline_start).total_seconds()
                
                log_console("\n" + "=" * 60)
                log_console("🎉 PIPELINE COMPLETE!")
                log_console("=" * 60)
                log_console(f"Total Duration: {total_duration:.2f}s")
                log_console(f"Output Directory: {run_dir}")
                log_console("=" * 60)
                
                overall_status.text("✅ Complete!")
                
                # Create execution summary
                execution_summary = {
                    "run_id": run_timestamp,
                    "pipeline_execution": {
                        "start_time": pipeline_start.isoformat(),
                        "end_time": pipeline_end.isoformat(),
                        "total_duration_seconds": total_duration,
                        "stage_durations": {
                            "parsing": stage1_duration,
                            "summarization": stage2_duration,
                            "synthesis": stage3_duration,
                            "survey_generation": stage4_duration
                        }
                    },
                    "configuration": {
                        "model": config["model"]["name"],
                        "temperature": config["model"]["temperature"],
                        "seed": config["model"]["seed"]
                    },
                    "results": {
                        "papers_processed": len(pdf_files),
                        "summaries_generated": len(summaries),
                        "survey_word_count": word_count
                    },
                    "output_files": {
                        "run_directory": str(run_dir),
                        "trace_file": config["output"]["trace_file"],
                        "summaries_dir": config["output"]["summaries_dir"],
                        "synthesis_file": str(synthesis_file),
                        "survey_file": config["output"]["survey_file"],
                        "llm_responses_dir": str(llm_responses_dir)
                    }
                }
                
                execution_summary_file = run_dir / "execution_summary.json"
                with open(execution_summary_file, 'w', encoding='utf-8') as f:
                    json.dump(execution_summary, f, indent=2, ensure_ascii=False)
                
                st.success("✅ Analysis complete!")
                
                # Display results
                with results_container:
                    st.markdown("---")
                    st.markdown("## 📊 Pipeline Metrics")
                    
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    with metric_col1:
                        st.metric("Total Duration", f"{total_duration:.2f}s")
                    with metric_col2:
                        st.metric("Papers Processed", len(pdf_files))
                    with metric_col3:
                        st.metric("Survey Words", word_count)
                    with metric_col4:
                        st.metric("Run ID", run_timestamp)
                    
                    st.markdown("---")
                    st.markdown("## 📄 Results")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📝 Paper Summaries")
                        for summary_file in sorted(summaries_dir.glob("*.json")):
                            if summary_file.name != "synthesis.json":
                                with open(summary_file, 'r') as f:
                                    summary = json.load(f)
                                with st.expander(f"📄 {summary['title']}", expanded=False):
                                    st.markdown(f"**Generated:** {summary.get('generated_timestamp', 'N/A')}")
                                    st.markdown("**Main Contribution:**")
                                    st.write(summary.get('main_contribution', 'N/A'))
                                    st.markdown("**Key Findings:**")
                                    st.write(summary.get('key_findings', 'N/A'))
                    
                    with col2:
                        st.subheader("🔄 Cross-Paper Synthesis")
                        with open(synthesis_file, 'r') as f:
                            synthesis_data = json.load(f)
                        
                        st.markdown(f"**Generated:** {synthesis_data.get('generated_timestamp', 'N/A')}")
                        st.markdown("**Common Themes:**")
                        st.write(synthesis_data.get('common_themes', 'N/A'))
                        st.markdown("**Research Gaps:**")
                        st.write(synthesis_data.get('research_gaps', 'N/A'))
                    
                    st.markdown("---")
                    st.subheader("📋 Mini-Survey")
                    
                    with open(config["output"]["survey_file"], 'r') as f:
                        survey_content = f.read()
                    
                    st.markdown(survey_content)
                    
                    st.markdown("---")
                    st.subheader("🤖 LLM Responses")
                    
                    # Load and display all LLM responses
                    llm_response_files = sorted(llm_responses_dir.glob("*.txt"))
                    
                    if llm_response_files:
                        st.info(f"Found {len(llm_response_files)} LLM interaction(s)")
                        
                        for llm_file in llm_response_files:
                            with st.expander(f"📄 {llm_file.name}", expanded=False):
                                llm_content = load_llm_response_from_file(llm_file)
                                st.markdown('<div class="llm-response-box">', unsafe_allow_html=True)
                                st.code(llm_content, language="text")
                                st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No separate LLM response files (responses may be inline in trace)")
                    
                    # Download buttons
                    st.markdown("---")
                    st.subheader("📥 Downloads")
                    
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.download_button(
                            "📥 Survey",
                            survey_content,
                            file_name=f"survey_{run_timestamp}.md",
                            mime="text/markdown"
                        )
                    with col_d2:
                        st.download_button(
                            "📥 Execution Summary",
                            json.dumps(execution_summary, indent=2),
                            file_name=f"exec_summary_{run_timestamp}.json",
                            mime="application/json"
                        )
                    with col_d3:
                        with open(config["output"]["trace_file"], 'r') as f:
                            st.download_button(
                                "📥 Trace Log",
                                f.read(),
                                file_name=f"trace_{run_timestamp}.jsonl",
                                mime="application/json"
                            )
            
            except Exception as e:
                log_console(f"\n❌ ERROR: {str(e)}")
                st.error(f"Error: {e}")
                overall_status.text("❌ Pipeline failed!")
                import traceback
                log_console(f"\nTraceback:\n{traceback.format_exc()}")

with tab2:
    st.header("🔬 Parameter Comparison")
    st.markdown("Compare different configurations with unique outputs for each")
    
    if uploaded_files:
        st.info("💡 Each comparison run creates separate outputs. Add/remove configurations dynamically.")
        
        control_col1, control_col2, control_col3 = st.columns([2, 2, 6])
        
        with control_col1:
            if st.button("➕ Add Configuration", use_container_width=True):
                st.session_state.param_configs.append({
                    "id": st.session_state.next_id,
                    "temperature": 0.3,
                    "seed": 42
                })
                st.session_state.next_id += 1
                st.rerun()
        
        with control_col2:
            st.markdown(f"**Total: {len(st.session_state.param_configs)}**")
        
        st.markdown("---")
        
        configs_to_remove = []
        
        for config in st.session_state.param_configs:
            with st.container():
                st.markdown(f'<div class="param-config-box">', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([3, 3, 1])
                
                with col1:
                    config["temperature"] = st.number_input(
                        "Temperature", 0.0, 1.0, config["temperature"], 0.1,
                        key=f"temp_{config['id']}"
                    )
                
                with col2:
                    config["seed"] = st.number_input(
                        "Seed", value=config["seed"], step=1,
                        key=f"seed_{config['id']}"
                    )
                
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if len(st.session_state.param_configs) > 1:
                        if st.button("🗑️", key=f"remove_{config['id']}", help="Remove"):
                            configs_to_remove.append(config['id'])
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        if configs_to_remove:
            st.session_state.param_configs = [
                c for c in st.session_state.param_configs 
                if c['id'] not in configs_to_remove
            ]
            st.rerun()
        
        st.markdown("---")
        
        if st.button("🔬 Run Comparison", type="primary", use_container_width=True):
            if len(st.session_state.param_configs) < 2:
                st.error("❌ Need at least 2 configurations")
            else:
                # Create unique comparison directory
                comp_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                comp_dir = Path(f"comparison_{comp_timestamp}")
                comp_dir.mkdir(exist_ok=True)
                
                st.info(f"📁 Comparison outputs: `{comp_dir}/`")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                console_comp = st.expander("📋 Console", expanded=True)
                
                with console_comp:
                    comp_output = st.empty()
                    comp_log = []
                
                def log_comp(msg):
                    comp_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                    comp_output.code("\n".join(comp_log[-30:]))
                
                try:
                    parameter_sets = [
                        {"temperature": c["temperature"], "seed": c["seed"]}
                        for c in st.session_state.param_configs
                    ]
                    
                    log_comp(f"Starting comparison: {len(parameter_sets)} configs")
                    
                    # Save uploaded files for comparison
                    comp_upload_dir = comp_dir / "uploads"
                    comp_upload_dir.mkdir(exist_ok=True)
                    
                    for uploaded_file in uploaded_files:
                        uploaded_file.seek(0)
                        with open(comp_upload_dir / uploaded_file.name, 'wb') as f:
                            f.write(uploaded_file.read())
                    
                    # Run comparison with unique directory
                    base_config = {
                        "model": {"name": model, "max_tokens": 2000},
                        "output": {"summaries_dir": str(comp_dir / "summaries")},
                        "survey": {"max_words": 800, "include_citations": True}
                    }
                    
                    comparator = ParameterComparison(base_config)
                    
                    for i, params in enumerate(parameter_sets, 1):
                        status_text.text(f"Testing {i}/{len(parameter_sets)}")
                        log_comp(f"Config {i}: T={params['temperature']}, S={params['seed']}")
                        progress_bar.progress(i / len(parameter_sets))
                    
                    report = comparator.run_comparison(str(comp_upload_dir), parameter_sets)
                    
                    progress_bar.progress(1.0)
                    status_text.text("✅ Complete!")
                    
                    st.success("✅ Comparison complete!")
                    
                    successful = [r for r in report['results'] if r.get('status') == 'success']
                    
                    if successful:
                        df = pd.DataFrame(successful)
                        st.dataframe(df[['temperature', 'seed', 'word_count', 'citation_count', 'duration']], 
                                   use_container_width=True)
                        
                        st.subheader("🎯 Recommended")
                        rec = report['recommended']
                        st.success(f"**Temperature:** {rec['temperature']} | **Seed:** {rec['seed']}")
                        
                        report_file = comp_dir / "comparison_report.json"
                        with open(report_file, 'w') as f:
                            json.dump(report, f, indent=2)
                        
                        st.download_button(
                            "📥 Download Report",
                            json.dumps(report, indent=2),
                            file_name=f"comparison_{comp_timestamp}.json",
                            mime="application/json"
                        )
                    else:
                        st.error("❌ No successful runs")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    log_comp(f"❌ {e}")
    else:
        st.warning("Upload PDFs first")

with tab3:
    st.header("📊 Trace Logs")
    
    # Find all trace files from runs
    trace_files = list(Path(".").glob("*/trace.jsonl")) + list(Path(".").glob("web_run_*/trace.jsonl"))
    
    if trace_files:
        trace_file = st.selectbox("Select trace file", 
                                 sorted(trace_files, reverse=True),
                                 format_func=lambda x: str(x))
        show_llm = st.checkbox("Show LLM interactions", value=True)
        
        with open(trace_file, 'r') as f:
            entries = [json.loads(line) for line in f]
        
        st.info(f"📊 Total entries: {len(entries)}")
        
        for entry in entries:
            if entry['action'] == 'llm_interaction' and show_llm:
                with st.expander(f"🤖 {entry['agent']} ({entry['timestamp']})", expanded=False):
                    st.write(f"**Model:** {entry['data']['model']}")
                    st.write(f"**Temp:** {entry['data']['temperature']}, **Seed:** {entry['data']['seed']}")
                    st.write(f"**Storage:** {entry['data'].get('response_storage', 'unknown')}")
                    
                    if entry['data'].get('response_storage') == 'file':
                        response_file = entry['data'].get('response_file', '')
                        st.code(f"File: {response_file}")
                        
                        # Load and display full response
                        if os.path.exists(response_file):
                            if st.button(f"📄 Load Full Response", key=f"load_{entry['timestamp']}"):
                                full_response = load_llm_response_from_file(response_file)
                                st.markdown('<div class="llm-response-box">', unsafe_allow_html=True)
                                st.code(full_response, language="text")
                                st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.write("**Response:**")
                        st.text(entry['data'].get('response', 'N/A'))
            elif entry['action'] != 'llm_interaction':
                st.text(f"[{entry['timestamp']}] {entry['agent']}.{entry['action']}")
    else:
        st.warning("No trace files found. Run analysis first.")

with tab4:
    st.header("📁 Execution Summaries")
    
    # Find all execution summaries
    summary_files = list(Path(".").glob("*/execution_summary.json")) + \
                   list(Path(".").glob("web_run_*/execution_summary.json"))
    
    if summary_files:
        selected = st.selectbox("Select summary",
                               sorted(summary_files, reverse=True),
                               format_func=lambda x: f"{x.parent.name} - {x.name}")
        
        with open(selected, 'r') as f:
            exec_summary = json.load(f)
        
        st.subheader("⏱️ Metrics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{exec_summary['pipeline_execution']['total_duration_seconds']:.2f}s")
        with col2:
            st.metric("Papers", exec_summary['results']['papers_processed'])
        with col3:
            st.metric("Words", exec_summary['results']['survey_word_count'])
        
        st.subheader("📊 Stages")
        stages = exec_summary['pipeline_execution']['stage_durations']
        stage_df = pd.DataFrame([
            {"Stage": k, "Duration (s)": v}
            for k, v in stages.items()
        ])
        st.bar_chart(stage_df.set_index("Stage"))
        
        st.json(exec_summary)
    else:
        st.info("No summaries found.")

with tab5:
    st.header("📖 Help")
    
    st.markdown("""
    ## 🎯 Key Updates
    
    ### ✅ Unique Run Directories
    Every analysis run creates a timestamped directory:
    - `web_run_YYYYMMDD_HHMMSS/`
    - All outputs isolated
    - No overwriting
    
    ### ✅ Full LLM Responses Visible
    - Long responses stored in separate files
    - Viewable directly in web interface
    - Load from trace log viewer
    
    ### ✅ Dynamic Parameter Comparison
    - Add unlimited configurations
    - Each comparison gets unique directory
    - Independent outputs
    
    ## 📁 Output Structure
    
    ```
    web_run_20251112_182800/
    ├── uploads/              # Your PDFs
    ├── summaries/           # JSON summaries
    │   ├── parsed_content/  # Parsed text
    │   └── synthesis.json
    ├── llm_responses/       # LLM response files
    ├── trace.jsonl         # Execution trace
    ├── survey.md           # Mini-survey
    └── execution_summary.json
    ```
    
    Each run is completely independent!
    """)

st.sidebar.markdown("---")
st.sidebar.info(f"**Version:** 2.2\n**Features:** Unique Runs + Full LLM Display")
