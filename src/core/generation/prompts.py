SECTION_GUIDANCE = {
    "abstract": "Provide a concise summary of the research problem, methodology, key findings, and contributions in 150-250 words.",
    "introduction": "Set the context, motivate the problem, and state the paper's contribution.",
    "literature review": "Summarize and synthesize related work, grouping similar approaches and noting gaps.",
    "methodology": "Describe the approach/method in a structured, step-by-step academic manner.",
    "results": "Present findings objectively, referencing data/metrics where relevant.",
    "conclusion": "Summarize contributions, implications, and possible future work.",
    "references": "List all cited works in a consistent academic citation format (APA style).",
}


def build_generation_prompt(
    topic: str,
    section: str,
    web_results: list[dict],
    style_notes: str = "",
    style_profile=None,
    keywords: str = "",
    extra_instructions: str = "",
    previous_sections_summary: str = "",
    include_visuals: bool = True,
) -> str:

    if web_results:
        content_block = "\n\n".join(
            f"[{r['title']}]({r['url']})\n{r['content'][:500]}" for r in web_results
        )
        content_instruction = (
            "Use the following real, current sources for factual content. "
            "You may reference them by publication/title if natural, but do NOT invent "
            "author names, years, or citations that are not explicitly given below."
        )
    else:
        content_block = "(no external sources retrieved)"
        content_instruction = (
            "No external sources were retrieved. Write using general domain knowledge, "
            "but do NOT fabricate specific citations, author names, or years. "
            "State claims generally rather than attributing them to invented sources."
        )

    # Use style_profile if provided, fall back to bare style_notes string
    if style_profile is not None:
        style_notes = style_profile.to_prompt_text()

    guidance = SECTION_GUIDANCE.get(section.lower(), "Write in a clear academic style.")
    previous_context_block = (
        f"\nContext from sections already written earlier in this paper "
        f"(stay consistent, don't repeat content or phrasing):\n{previous_sections_summary}\n"
        if previous_sections_summary else ""
    )

    # Calculate dynamic word count target from reference papers
    ratios = {
        "abstract": 0.05,
        "introduction": 0.15,
        "literature review": 0.25,
        "methodology": 0.25,
        "results": 0.20,
        "conclusion": 0.10,
        "references": 0.0,
    }
    ratio = ratios.get(section.lower(), 0.15)
    total_target = getattr(style_profile, "avg_paper_word_count", 2500) if style_profile else 2500
    target_words = int(total_target * ratio)

    # Length guidance based on section type
    length_instruction = ""
    if section.lower() == "abstract":
        length_instruction = "\n## Length Requirement\nWrite a concise abstract of 150-250 words.\n"
    elif section.lower() != "references":
        length_instruction = f"""
## Length & Depth Requirement
This section MUST be comprehensive and academically deep, matching the depth of the reference literature.
Target: at least {target_words} words for this section.
DO NOT write a single unbroken wall of text. Break into 2-4 logical subsections using markdown subheadings (e.g., ### 2.1 Background, ### 2.2 Related Approaches).
For each subsection: write multiple detailed paragraphs with technical depth, specific examples, and analytical commentary grounded in the sources provided.
"""

    # Structural variation instructions (attacks AI uniformity detectors)
    structural_instructions = ""
    if section.lower() not in ("abstract", "references"):
        structural_instructions = """
## Structural Variation (CRITICAL for authentic prose)
1. SENTENCE-INITIAL DIVERSITY: Do NOT start every sentence with the subject. At least 40% of sentences should open with:
   - A subordinate clause ("Although X remains debated, ...", "Because the dataset is sparse, ...")
   - A prepositional phrase ("In the context of sparse data, ...", "From a computational standpoint, ...")
   - An adverb or adverbial phrase ("Interestingly, ...", "In practice, ...")
   - A gerund phrase ("Drawing on prior evaluations, ...", "Considering the constraints, ...")
2. PARAGRAPH STRUCTURE VARIETY: Not every paragraph should start with a topic sentence. Occasionally:
   - Open with a specific observation or data point, THEN generalize
   - Open with a question, THEN answer it
   - Open with a concession ("Admittedly, ...", "Granted, ...")
3. SENTENCE LENGTH VARIATION: Deliberately mix very short sentences (4-8 words) with longer compound-complex sentences (25-35 words). Never write 3 consecutive sentences of similar length.
4. AVOID AI PARAGRAPH TEMPLATE: Do NOT follow the pattern "general claim → 3 pieces of evidence → concluding generalization" in every paragraph. Vary the internal structure.
"""

    visual_instructions = ""
    if include_visuals:
        visual_instructions = f"""
This section MUST include exactly ONE relevant real academic figure, diagram, flowchart, or photograph.
You MUST insert it using this EXACT syntax on its own line:
![Clear descriptive caption here](image_query: "3-5 specific keywords for image search")

Rules for images:
- Place the image placeholder at the most logically relevant point in the text.
- The caption must be academically appropriate.
- Use highly specific search terms that match the content of this section.
- Do not use generic terms like "diagram" or "figure" — be specific (e.g., "knowledge graph meta-path example in healthcare").
- This is mandatory for all sections except Abstract and References.

Examples:
![Knowledge graph schema for drug interactions](image_query: "biomedical knowledge graph schema drug interactions")
![Meta-path traversal example in recommendation system](image_query: "knowledge graph meta-path traversal healthcare recommendation")
"""

    keywords_block = ""
    if keywords:
        keywords_block = f"""
## Keywords (weave these naturally into the text)
{keywords}

Use these keywords as thematic anchors throughout the section. They represent the core concepts the paper must address.
"""

    # Only inject statistics block for quantitative sections
    statistics_block = ""
    if section.lower() in ("results", "methodology"):
        statistics_block = """
## Statistical Analysis Requirement
If this topic involves quantitative data, act as a statistician: perform appropriate statistical sampling,
hypothesis testing, confidence intervals, or significance analysis as per academic standards.
Present sample sizes, p-values, and effect sizes where relevant. Use tables or figures to present statistical results.
"""

    return f"""You are an academic writing assistant. Write the "{section}" section
for a research paper titled: "{topic}".

Section guidance: {guidance}
{previous_context_block}

{length_instruction}

{structural_instructions}

Match this writing style (learned from reference papers, NOT the topic source):
{style_notes}

{keywords_block}

{content_instruction}

{content_block}

{visual_instructions}

{statistics_block}

{f"Additional instructions: {extra_instructions}" if extra_instructions else ""}

Write only the section content, in formal academic prose. Do not include a top-level heading for the section name itself, but DO use subheadings as instructed.
CRITICAL: Vary sentence length and structure naturally. Do NOT stack transition words (however, furthermore, moreover, therefore) in the same paragraph. Do NOT use the words: delves, tapestry, beacon, landscape (figurative), realm, paradigm shift, groundbreaking, holistic, cornerstone, interplay, vibrant, fosters, underscores, pivotal, crucial, testament, unprecedented, transformative, seamless integration. These are AI-detection triggers.
"""


def build_rewrite_prompt(
    topic: str,
    section: str,
    original_text: str,
    issues: list[str],
    style_notes: str,
) -> str:
    issues_block = "\n".join(f"- {issue}" for issue in issues)

    return f"""You are revising the "{section}" section of a research paper titled "{topic}".

Here is the current draft:
---
{original_text}
---

An automated review flagged these specific issues:
{issues_block}

Rewrite the section to fix ONLY these issues. Preserve everything else that
already works well — don't rewrite from scratch, don't change claims that
weren't flagged, and don't introduce new citations or facts not already
present in the original draft.

Match this writing style:
{style_notes}

CRITICAL STRUCTURAL PRESERVATION:
- Preserve any sentence-initial variety (sentences starting with subordinate clauses, adverbs, prepositional phrases)
- Preserve sentence length variation (mix of short punchy sentences and longer compound sentences)
- Preserve paragraph structure variety (not all paragraphs should follow the same template)
- Do NOT use the words: delves, tapestry, beacon, landscape (figurative), realm, paradigm shift, groundbreaking, holistic, cornerstone, interplay, vibrant, fosters, underscores, pivotal, crucial, testament, unprecedented, transformative, seamless integration
- Avoid stacking transition words in one paragraph
- Never invent specific details, anecdotes, or citations to fill gaps

Write only the revised section content, without a top-level heading.
"""
