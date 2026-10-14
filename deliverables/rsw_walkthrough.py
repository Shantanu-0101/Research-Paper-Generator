"""
===============================================================================
 Research Style Writer (RSW)
 Complete Pipeline Walkthrough
===============================================================================

 This script walks through every stage of the pipeline:

   1.  Configuration & Environment Setup
   2.  PDF Ingestion & Text Extraction
   3.  Text Chunking
   4.  Writing Style Analysis
   5.  Web Search (Tavily API)
   6.  Prompt Construction
   7.  LLM-Based Section Generation
   8.  Automated Evaluation & Iterative Refinement
   9.  Multi-Pass Humanization Pipeline
   10. Academic Image Search & Insertion
   11. PDF / DOCX Export
   12. Full End-to-End Paper Generation

 Prerequisites:
   - Python 3.10+
   - pip install -r requirements.txt
   - A .env file with API keys (see src/core/config.py for required keys)
   - 3-8 reference PDF papers in a folder

 Project: Research Style Writer (RSW) — Mini Project
===============================================================================
"""

import sys
import os

# Ensure the project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 1: Configuration & Environment Setup                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("=" * 70)
print("STEP 1: Configuration & Environment Setup")
print("=" * 70)

from src.core.config import settings

# The Settings dataclass reads all API keys and parameters from .env
print(f"LLM Provider       : {settings.llm_provider}")
print(f"Embedding Provider  : {settings.embedding_provider}")
print(f"Embedding Model     : {settings.embedding_model_name}")
print(f"Chunk Size          : {settings.chunk_size}")
print(f"Chunk Overlap       : {settings.chunk_overlap}")
print(f"Top-K Retrieval     : {settings.top_k}")
print(f"Min Reference Files : {settings.min_files}")
print(f"Max Reference Files : {settings.max_files}")

try:
    settings.validate()
    print("\nConfiguration validated successfully.")
except ValueError as e:
    print(f"\nConfiguration error: {e}")
    print("Please set up your .env file with the required API keys.")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 2: PDF Ingestion & Text Extraction                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 2: PDF Ingestion & Text Extraction")
print("=" * 70)

from src.core.ingestion.pdf_loader import extract_text_from_pdf

# The PDF loader uses PyMuPDF (fitz) for extraction.
# If a page has corrupted fonts (high '?' ratio), it falls back to
# Gemini Vision (VLM) for OCR-based extraction.

# Demo: extract from a sample PDF if available
sample_pdf_dir = os.path.join(PROJECT_ROOT, "data", "uploads")
sample_pdfs = [f for f in os.listdir(sample_pdf_dir) if f.endswith(".pdf")] if os.path.isdir(sample_pdf_dir) else []

if sample_pdfs:
    sample_path = os.path.join(sample_pdf_dir, sample_pdfs[0])
    with open(sample_path, "rb") as f:
        pages = extract_text_from_pdf(f.read(), sample_pdfs[0])
    print(f"Extracted {len(pages)} pages from '{sample_pdfs[0]}'")
    if pages:
        print(f"  Page 1 preview ({len(pages[0]['text'].split())} words):")
        print(f"  {pages[0]['text'][:200]}...")
else:
    print("No sample PDFs found in data/uploads/.")
    print("In the Streamlit app, users upload 3-8 reference PDFs.")
    # Create a synthetic example for demonstration
    pages = [
        {"text": "Machine learning has transformed natural language processing. "
                 "Recent advances in transformer architectures have enabled "
                 "unprecedented capabilities in text generation and understanding. "
                 "This paper examines the implications of these developments.",
         "source": "demo_paper.pdf", "page": 1},
        {"text": "The methodology employs a multi-stage pipeline combining "
                 "retrieval-augmented generation with style-aware text synthesis. "
                 "We leverage pre-trained language models fine-tuned for academic "
                 "writing to produce coherent, well-structured research prose.",
         "source": "demo_paper.pdf", "page": 2},
    ]
    print(f"Using {len(pages)} synthetic demo pages for walkthrough.")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 3: Text Chunking                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 3: Text Chunking")
print("=" * 70)

from src.core.ingestion.chunker import chunk_pages

# Uses LangChain's RecursiveCharacterTextSplitter to break pages into
# overlapping chunks for style analysis and vector indexing.
chunks = chunk_pages(pages)
print(f"Input pages : {len(pages)}")
print(f"Output chunks: {len(chunks)}")
print(f"Chunk size   : {settings.chunk_size} chars, overlap: {settings.chunk_overlap} chars")
if chunks:
    print(f"\nFirst chunk preview:")
    print(f"  Source: {chunks[0]['source']}, Page: {chunks[0]['page']}")
    print(f"  Text: {chunks[0]['text'][:150]}...")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 4: Writing Style Analysis                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 4: Writing Style Analysis")
print("=" * 70)

from src.core.style.style_analyzer import analyze_style

# StyleProfile extracts 12 quantitative features from the reference papers:
#   - avg_sentence_length, sentence_length_std
#   - lexical_diversity (type-token ratio)
#   - top_transition_words (with frequency counts)
#   - passive_voice_ratio
#   - avg_paper_word_count
#   - avg_paragraph_length, paragraph_length_std
#   - sentence_initial_variety (% not starting with article/pronoun)
#   - questions_per_1000_words
#   - first_person_ratio (we/our/us usage)
#   - avg_paragraphs_per_section

style_profile = analyze_style(chunks)

print(f"Avg sentence length    : {style_profile.avg_sentence_length:.1f} words")
print(f"Sentence length StdDev : {style_profile.sentence_length_std:.1f}")
print(f"Lexical diversity      : {style_profile.lexical_diversity:.3f}")
print(f"Passive voice ratio    : {style_profile.passive_voice_ratio:.2f}")
print(f"Avg paper word count   : {style_profile.avg_paper_word_count}")
print(f"Avg paragraph length   : {style_profile.avg_paragraph_length:.0f} words")
print(f"Sentence-initial variety: {style_profile.sentence_initial_variety:.3f}")
print(f"First-person ratio     : {style_profile.first_person_ratio:.4f}")
print(f"Questions per 1000w    : {style_profile.questions_per_1000_words:.2f}")

print(f"\nTop transition words:")
for word, count in style_profile.top_transition_words[:5]:
    print(f"  {word}: {count}")

print(f"\nStyle prompt text (fed to LLM):")
print(f"  {style_profile.to_prompt_text()[:300]}...")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 5: Web Search (Tavily API)                                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 5: Web Search (Tavily API)")
print("=" * 70)

from src.core.retrieval.web_search import search_topic_content

# Tavily provides real-time web search results with extracted content.
# Each section gets its own web search to gather domain-specific context.

DEMO_TOPIC = "Knowledge Graphs for Healthcare Recommendation Systems"
DEMO_SECTION = "Introduction"

try:
    web_results = search_topic_content(DEMO_TOPIC, "", DEMO_SECTION)
    print(f"Retrieved {len(web_results)} web results for '{DEMO_SECTION}'")
    for i, r in enumerate(web_results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"    Title: {r['title'][:80]}")
        print(f"    URL  : {r['url'][:80]}")
        print(f"    Text : {r['content'][:120]}...")
except Exception as e:
    print(f"Web search unavailable: {e}")
    print("Set TAVILY_API_KEY in .env to enable live web search.")
    web_results = []


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 6: Prompt Construction                                              ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 6: Prompt Construction")
print("=" * 70)

from src.core.generation.prompts import build_generation_prompt

# The prompt builder assembles a structured prompt containing:
#   - Section-specific guidance (from SECTION_GUIDANCE dict)
#   - Dynamic word count targets (proportional to reference paper length)
#   - Structural variation instructions (sentence diversity, burstiness)
#   - Style notes from the analyzed reference papers
#   - Keywords to weave into the text
#   - Web search results as grounding content
#   - Image placeholder instructions
#   - AI-tell ban list (19 flagged words/phrases)

DEMO_KEYWORDS = "Knowledge Graph, Meta-path, LLM, Recommendation"

prompt = build_generation_prompt(
    topic=DEMO_TOPIC,
    section=DEMO_SECTION,
    web_results=web_results,
    style_profile=style_profile,
    keywords=DEMO_KEYWORDS,
    include_visuals=True,
)

print(f"Prompt length: {len(prompt)} characters")
print(f"\nPrompt structure (first 500 chars):")
print(prompt[:500])
print("...")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 7: LLM-Based Section Generation                                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 7: LLM-Based Section Generation")
print("=" * 70)

from src.core.llm.llm_factory import get_llm

# The LLM factory supports multiple providers:
#   - xAI (Grok-2)
#   - Groq
#   - Google Gemini
#   - OpenRouter
# Selection is controlled by LLM_PROVIDER in .env

print(f"Active LLM provider: {settings.llm_provider}")

try:
    llm = get_llm()
    print(f"LLM initialized successfully.")

    # Generate a section (with retry logic — 3 attempts)
    response = llm.invoke(prompt)
    generated_text = response.content if response.content else ""
    word_count = len(generated_text.split())
    print(f"\nGenerated section: {word_count} words")
    print(f"Preview (first 300 chars):")
    print(generated_text[:300])
    print("...")
except Exception as e:
    print(f"LLM generation unavailable: {e}")
    generated_text = (
        "Knowledge graphs have emerged as a useful tool for organizing and reasoning "
        "over structured biomedical data. In healthcare recommendation systems, these "
        "graphs capture relationships between diseases, drugs, symptoms, and treatments. "
        "Meta-path-based approaches traverse typed paths through the graph to discover "
        "meaningful patterns. Recent work combines LLM capabilities with graph-based "
        "retrieval to produce more accurate and explainable recommendations."
    )
    print(f"Using demo text ({len(generated_text.split())} words) for remaining steps.")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 8: Automated Evaluation & Iterative Refinement                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 8: Automated Evaluation & Iterative Refinement")
print("=" * 70)

from src.core.generation.evaluator import evaluate_section

# The evaluator runs 5 automated quality checks:
#   1. Fabricated citation detection (flags in-text citations when no sources exist)
#   2. Transition word overuse (max per paragraph)
#   3. Cross-section repetition (5-gram overlap detection)
#   4. Style drift (sentence length deviation from reference papers)
#   5. Length check (proportional to reference paper word count)

evaluation = evaluate_section(
    text=generated_text,
    sources_used=[{"title": "demo", "url": "https://example.com"}],
    style_profile=style_profile,
    previous_sections_summary="",
    section_name=DEMO_SECTION,
)

print(f"Evaluation passed: {evaluation.passed}")
if evaluation.issues:
    print("Issues found:")
    for issue in evaluation.issues:
        print(f"  - {issue}")
else:
    print("No issues detected.")

# In the full pipeline, if evaluation fails, the section is rewritten
# using build_rewrite_prompt() which targets only the flagged issues.
# This loop runs up to max_attempts (default: 3).
print("\nRewrite loop: generate -> evaluate -> rewrite (if issues) -> re-evaluate")
print("Max attempts: 3 (configurable)")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 9: Multi-Pass Humanization Pipeline                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 9: Multi-Pass Humanization Pipeline")
print("=" * 70)

# The humanizer is the core innovation — a 5-pass pipeline that removes
# AI writing patterns to reduce detection scores.
#
# Pass 1 — Pre-LLM Structural Work (pure Python, no API):
#   a. Burstiness Injection: randomises sentence lengths (target CV > 0.45)
#   b. Sentence Restructurer: clause reordering, sentence-initial diversity
#   c. Paragraph Mixer: paragraph-level structural variation
#
# Pass 2 — LLM Rewrite via Multi-Candidate Re-Ranking:
#   - 3 candidates generated with different personas:
#     1. Empirical Researcher (data-first voice)
#     2. Asymmetric Rhythm (varied cadence)
#     3. Analytical Research Voice (methodical tone)
#   - Each candidate scored on burstiness_cv, residual AI tells, composite
#   - Best candidate selected
#
# Pass 3 — Post-LLM Processing (pure Python):
#   a. Lexical Booster: perplexity-raising word swaps (45% probability)
#   b. Lexical Diversity: synonym rotation for TTR improvement
#   c. Human Artifacts: hedges, parentheticals, cross-references, discourse markers
#
# Pass 4 — Quality Gate:
#   - Composite score >= 80, Burstiness CV >= 0.45, Variety >= 0.35
#   - If below threshold, iterate Pass 2-3 again (max 2 additional iterations)
#
# Pass 5 — Final Burstiness Enforcement:
#   - Clean up any uniformity the LLM re-introduced

from src.core.humanizer.burstiness import inject_burstiness, measure_burstiness, _split_into_sentences
from src.core.humanizer.sentence_restructurer import restructure_sentences, measure_sentence_initial_variety
from src.core.humanizer.paragraph_mixer import mix_paragraphs
from src.core.humanizer.lexical_booster import boost_perplexity, enforce_lexical_diversity
from src.core.humanizer.human_artifacts import inject_human_artifacts
from src.core.humanizer.reranker import score_candidate

# Demonstrate each sub-step on the generated text:

# Pass 1a: Burstiness
sentences_before = _split_into_sentences(generated_text)
cv_before = measure_burstiness(sentences_before)
text_after_burst = inject_burstiness(generated_text)
sentences_after = _split_into_sentences(text_after_burst)
cv_after = measure_burstiness(sentences_after)
print(f"Pass 1a — Burstiness injection:")
print(f"  CV before: {cv_before:.3f} -> CV after: {cv_after:.3f}")
print(f"  (Target: >= 0.45; human writing typically > 0.5)")

# Pass 1b: Sentence restructuring
variety_before = measure_sentence_initial_variety(text_after_burst)
text_after_restr = restructure_sentences(text_after_burst)
variety_after = measure_sentence_initial_variety(text_after_restr)
print(f"\nPass 1b — Sentence restructuring:")
print(f"  Variety before: {variety_before:.3f} -> after: {variety_after:.3f}")
print(f"  (Target: >= 0.35; measures % of sentences NOT starting with article/pronoun)")

# Pass 1c: Paragraph mixing
text_after_mix = mix_paragraphs(text_after_restr)
print(f"\nPass 1c — Paragraph mixing applied")

# Pass 3 (demo without LLM — showing pure Python post-processing):
text_after_lex = boost_perplexity(text_after_mix, swap_probability=0.45)
text_after_div = enforce_lexical_diversity(text_after_lex)
text_after_artifacts = inject_human_artifacts(
    text_after_div,
    hedge_probability=0.12,
    parenthetical_probability=0.18,
    cross_ref_probability=0.10,
    emphatic_probability=0.08,
    citation_connector_probability=0.12,
)
print(f"\nPass 3 — Post-LLM processing:")
print(f"  Lexical boost + diversity + human artifacts applied")

# Quality score
final_score = score_candidate(text_after_artifacts)
final_variety = measure_sentence_initial_variety(text_after_artifacts)
print(f"\nQuality gate metrics:")
print(f"  Composite score : {final_score['composite_score']:.1f} (target: >= 80)")
print(f"  Burstiness CV   : {final_score['burstiness_cv']:.3f} (target: >= 0.45)")
print(f"  Residual AI tells: {final_score['residual_tells']} (target: 0)")
print(f"  Sentence variety : {final_variety:.3f} (target: >= 0.35)")

# Full humanization (calls the complete 5-pass pipeline)
print("\n--- Full pipeline demo (humanize_section) ---")
from src.core.humanizer.humanizer import humanize_section

demo_result = {
    "text": generated_text,
    "sources": [],
    "attempts": 1,
    "passed": True,
    "remaining_issues": [],
}

try:
    humanized_result = humanize_section(
        demo_result,
        style_notes=style_profile.to_prompt_text(),
        max_passes=2,  # Deep humanization
    )
    h_metrics = humanized_result.get("humanization_metrics", {})
    print(f"Humanization complete:")
    print(f"  Burstiness CV   : {h_metrics.get('burstiness_cv', 0):.3f}")
    print(f"  Residual tells  : {h_metrics.get('residual_tells', 0)}")
    print(f"  Composite score : {h_metrics.get('composite_score', 0):.1f}")
    print(f"  Variety          : {h_metrics.get('sentence_initial_variety', 0):.3f}")
    print(f"  Passes           : {h_metrics.get('passes', 0)}")
except Exception as e:
    print(f"Full humanization requires LLM access: {e}")
    print("The pre-LLM and post-LLM steps demonstrated above run without an API.")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 10: Academic Image Search & Insertion                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 10: Academic Image Search & Insertion")
print("=" * 70)

from src.core.illustration.image_search import get_academic_illustration
from src.core.generation.generator import _build_image_query

# The image pipeline searches for relevant academic figures:
#   1. Builds a targeted query from topic + keywords + section modifiers
#   2. Searches Tavily, Unsplash, Wikimedia, and Europe PMC
#   3. Filters by size (min 200x200) and file type
#   4. Downloads and caches locally in data/images/
#   5. Deduplicates across sections via used_image_paths set
#   6. Cache key includes both topic AND keywords to prevent reuse across topics

query = _build_image_query(
    topic=DEMO_TOPIC,
    section="Methodology",
    keywords=DEMO_KEYWORDS,
)
print(f"Image search query: '{query}'")
print(f"\nImage sources searched:")
print(f"  1. Tavily (web image search)")
print(f"  2. Unsplash (free academic photos)")
print(f"  3. Wikimedia Commons (open diagrams)")
print(f"  4. Europe PMC (biomedical figures)")

try:
    img_data = get_academic_illustration(query)
    if img_data:
        print(f"\nFound image:")
        print(f"  Source: {img_data.get('source_name', 'Unknown')}")
        print(f"  URL   : {img_data.get('source_url', 'N/A')[:80]}")
        print(f"  Local : {img_data.get('local_path', 'N/A')}")
    else:
        print("\nNo suitable image found for this query.")
except Exception as e:
    print(f"Image search unavailable: {e}")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 11: PDF / DOCX Export                                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 11: PDF / DOCX Export")
print("=" * 70)

from src.core.export.pdf_export import generate_pdf
from src.core.export.docx_export import generate_docx

# The export module generates downloadable files from the generated sections.
# - PDF: uses fpdf2 with DejaVu Sans fonts for Unicode support
# - DOCX: uses python-docx with proper heading styles

demo_sections = [
    ("Introduction", generated_text),
    ("Methodology", "This section describes the methodology used in the study."),
]

# Generate PDF
pdf_bytes = generate_pdf(DEMO_TOPIC, demo_sections)
print(f"PDF generated: {len(pdf_bytes):,} bytes")

# Generate DOCX
docx_bytes = generate_docx(DEMO_TOPIC, demo_sections)
print(f"DOCX generated: {len(docx_bytes):,} bytes")

# Save demo exports
export_dir = os.path.join(PROJECT_ROOT, "deliverables", "generation")
os.makedirs(export_dir, exist_ok=True)

demo_pdf_path = os.path.join(export_dir, "demo_output.pdf")
with open(demo_pdf_path, "wb") as f:
    f.write(pdf_bytes)
print(f"\nDemo PDF saved to: {demo_pdf_path}")

demo_docx_path = os.path.join(export_dir, "demo_output.docx")
with open(demo_docx_path, "wb") as f:
    f.write(docx_bytes)
print(f"Demo DOCX saved to: {demo_docx_path}")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  STEP 12: Full End-to-End Paper Generation                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("STEP 12: Full End-to-End Paper Generation")
print("=" * 70)

from src.core.generation.generator import generate_full_paper

# generate_full_paper() is a generator that yields (section_name, result)
# for each section. It:
#   1. Searches web per section (deduplicating URLs across sections)
#   2. Generates, evaluates, and rewrites each section
#   3. Maintains running summaries for cross-section coherence
#   4. Manages image cache and deduplication across sections
#   5. Builds APA-style references from all sources used
#
# The Streamlit app wraps this with humanize_section() per section.

print("Full paper generation flow:")
print("  for section_name, result in generate_full_paper(topic, style_profile, ...):")
print("      # result contains: text, sources, attempts, passed, remaining_issues")
print("      humanized = humanize_section(result, style_notes, max_passes=2)")
print("      # Display and collect for export")
print("")
print("Sections generated in order:")
for s in ["Abstract", "Introduction", "Literature Review",
          "Methodology", "Results", "Conclusion", "References"]:
    print(f"  - {s}")

print("\n" + "=" * 70)
print("WALKTHROUGH COMPLETE")
print("=" * 70)
print("""
To run the full Streamlit application:
  cd <project_root>
  streamlit run app.py

The app provides:
  - File upload for 3-8 reference PDFs
  - Style analysis of uploaded papers
  - Topic + keywords input
  - Single section or full paper generation
  - Humanization with configurable strength (Standard/Deep/Maximum)
  - PDF and DOCX export
""")
