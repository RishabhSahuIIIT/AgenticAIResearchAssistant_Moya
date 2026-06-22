"""Prompt templates for all pipeline agents.

Keeping prompts here (rather than inline in agents) lets you iterate on
wording without touching agent logic, and makes prompt changes visible as
clean diffs.
"""


def summarizer_prompt(title: str, text: str) -> str:
    """Build the summarization prompt for a paper that fits in one context window."""
    return f"""You are a research paper analyzer. Analyze the following research paper and provide a structured summary.

Paper Title: {title}
Paper Text:
{text}

Provide a structured summary with the following sections:
1. Title and Authors
2. Main Research Question/Problem
3. Key Contributions
4. Methodology/Approach
5. Main Results/Findings
6. Limitations
7. Future Work

Format your response as clear, concise bullet points for each section."""


def chunk_summary_prompt(title: str, text: str, chunk_index: int, total_chunks: int) -> str:
    """Prompt for extracting key information from one chunk of a longer paper.

    Instructs the model NOT to draw conclusions — more content is coming in later chunks.
    """
    return f"""You are analyzing part {chunk_index + 1} of {total_chunks} of a research paper.

Paper Title: {title}
Content (part {chunk_index + 1} of {total_chunks}):
{text}

Extract all key information present in THIS section only. Do NOT draw final conclusions,
state overall limitations, or suggest future work — the paper is not complete yet.
Note every methodology, finding, or contribution mentioned in this section, even partially."""


def chunk_combine_prompt(title: str, partial_summaries: str) -> str:
    """Prompt for reducing ordered chunk summaries into one final structured summary."""
    return f"""You are synthesizing partial summaries of consecutive sections of a single research paper into one coherent summary.

Paper Title: {title}
Partial summaries (in document order):
{partial_summaries}

Produce ONE structured summary of the complete paper covering:
1. Title and Authors
2. Main Research Question/Problem
3. Key Contributions
4. Methodology/Approach
5. Main Results/Findings
6. Limitations
7. Future Work

Resolve overlaps between sections, discard any incomplete thoughts that are completed in a later section, and write as if summarizing the full paper in one pass.
Format your response as clear, concise bullet points for each section."""


def synthesizer_prompt(combined_summaries: str) -> str:
    """Build the cross-paper synthesis prompt."""
    return f"""You are a research analyst. Based on the following paper summaries, identify:

1. Common themes and trends across papers
2. Key methodologies used
3. Main findings and contributions
4. Research gaps and unexplored areas
5. Contradictions or conflicting results
6. Potential future research directions

Paper Summaries:
{combined_summaries}

Provide a comprehensive synthesis organized into these sections."""


def survey_writer_prompt(combined_content: str, word_limit: int) -> str:
    """Build the mini-survey writing prompt."""
    return f"""You are a technical writer creating a mini-survey paper. Write a comprehensive survey (maximum {word_limit} words) based on the following research papers.

{combined_content}

Requirements:
1. Start with an introduction to the topic
2. Discuss key themes and methodologies
3. Present main findings across papers
4. Identify research gaps
5. Conclude with future directions
6. Use inline citations like [1], [2], etc. when referencing papers
7. Keep it under {word_limit} words
8. Write in academic style

Write the mini-survey now:"""
