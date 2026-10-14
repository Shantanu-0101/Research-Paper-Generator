"""
Humanizer module -- removes AI writing patterns from generated text.

Multi-Pass Pipeline (configurable depth):
  Pass 1 (Pre-LLM Structural Work):
    a. Burstiness Injection — randomises sentence lengths
    b. Sentence Restructurer — clause reordering, sentence-initial diversity
    c. Paragraph Mixer — paragraph-level structural variation
  Pass 2 (LLM Rewrite):
    Closed-Loop Multi-Candidate Re-Ranking (3 candidates, Gemini)
  Pass 3 (Post-LLM Processing):
    a. Lexical Booster — perplexity raising word swaps
    b. Lexical Diversity — synonym rotation for TTR
    c. Human Artifacts — hedges, parentheticals, cross-references, discourse markers
  Pass 4 (Quality Gate):
    Score the output; if below threshold, iterate Pass 2-3 again (max 2 iterations)
  Pass 5 (Final Enforcement):
    Final burstiness window enforcement to clean up anything the LLM re-uniformed
"""

import re
from src.core.config import settings
from src.core.humanizer.patterns import get_patterns_as_text
from src.core.humanizer.burstiness import inject_burstiness, measure_burstiness, _split_into_sentences
from src.core.humanizer.sentence_restructurer import restructure_sentences, measure_sentence_initial_variety
from src.core.humanizer.paragraph_mixer import mix_paragraphs
from src.core.humanizer.lexical_booster import boost_perplexity, enforce_lexical_diversity
from src.core.humanizer.human_artifacts import inject_human_artifacts
from src.core.humanizer.reranker import score_candidate
from src.core.llm.llm_factory import get_humanizer_llm


HUMANIZER_SYSTEM_PROMPT = """You are an expert human academic editor.
Your single objective is to rewrite AI-generated text so it passes AI detectors (Turnitin, CopyLeaks, Originality.ai) with a 0% AI score, while keeping every fact, citation, equation, number, and technical detail strictly intact.

## CRITICAL 0% AI SCORE REWRITING RULES

1. **REPLACE HIGH-REGISTER LATINATE AI BUZZWORDS WITH PLAIN DIRECT ANGLO-SAXON VERBS**:
   - 'emerged as a pivotal mechanism for' -> 'helps' or 'is useful for'
   - 'delves into the intricate mechanisms' -> 'examines how' or 'looks at'
   - 'serves as a testament to the power of' -> 'shows the real power of'
   - 'represents a paradigm shift in the realm of' -> 'marks a big change in'
   - 'underscores its transformative potential' -> 'shows how useful it is'
   - 'paramount challenge / persistent challenge' -> 'major hurdle' or 'hard problem'
   - 'unprecedented accuracy' -> 'high accuracy' or 'strong results'
   - Delete all occurrences of: 'furthermore', 'moreover', 'in conclusion', 'tapestry', 'fosters', 'realm', 'landscape', 'beacon', 'groundbreaking', 'vibrant', 'holistic', 'interplay', 'cornerstone'.

2. **INJECT SHORT 3-5 WORD PUNCHY SENTENCES (BURSTINESS)**:
   - Insert short direct statements like "That takes work.", "But scale hurts.", "Still, challenges remain.", "This is key." between longer compound clauses.
   - Mix 4-word sentences with 25-word compound clauses. Never write three consecutive sentences of similar length.

3. **ACTIVE PERSONAL RESEARCHER VOICE**:
   - Use direct active verbs ('we build', 'we find', 'shows') instead of passive academic puffery ('is observed to be utilized by', 'serves to demonstrate').

4. **OUTPUT STRICTNESS**:
   - Do NOT output preamble, intro greetings, options, bullet points, or markdown backticks.
   - Return ONLY the clean, final humanized text.

## The 26 specific AI tells to eliminate:

{patterns}
"""


# Quality gate thresholds
_MIN_COMPOSITE_SCORE = 80.0
_MIN_BURSTINESS_CV = 0.45
_MIN_INITIAL_VARIETY = 0.35


def build_humanizer_prompt(text: str, style_notes: str = "") -> str:
    patterns_text = get_patterns_as_text()
    system = HUMANIZER_SYSTEM_PROMPT.format(patterns=patterns_text)

    parts = [system]

    if style_notes:
        parts.append(f"\n## Match this writing style\n{style_notes}\n")

    parts.append(f"\n## Text to humanize\n{text}")

    return "\n".join(parts)


def humanize_text(text: str, style_notes: str = "", max_passes: int = 2) -> str:
    """
    Full multi-pass humanization pipeline.

    Pass 1: Pre-LLM structural work (pure Python)
    Pass 2: LLM rewrite via 3-Candidate Re-Ranking
    Pass 3: Post-LLM processing (pure Python)
    Pass 4: Quality gate — iterate if score is below threshold
    Pass 5: Final burstiness enforcement

    Args:
        text: The AI-generated text to humanize.
        style_notes: Optional style profile text.
        max_passes: Maximum number of LLM rewrite iterations (1=Standard, 2=Deep, 3=Maximum).

    Returns:
        The humanized text.
    """
    if not text or not text.strip():
        return text

    # ═══ Pass 1: Pre-LLM Structural Work (no API, instant) ═══
    print("[humanizer] Pass 1: Pre-LLM structural work...")

    # 1a. Burstiness injection
    sentences_before = _split_into_sentences(text)
    cv_before = measure_burstiness(sentences_before)
    processed = inject_burstiness(text)
    sentences_after = _split_into_sentences(processed)
    cv_after = measure_burstiness(sentences_after)
    print(f"[humanizer]   Burstiness CV: {cv_before:.3f} -> {cv_after:.3f}")

    # 1b. Sentence restructuring (clause reordering, sentence-initial diversity)
    variety_before = measure_sentence_initial_variety(processed)
    processed = restructure_sentences(processed)
    variety_after = measure_sentence_initial_variety(processed)
    print(f"[humanizer]   Sentence-initial variety: {variety_before:.3f} -> {variety_after:.3f}")

    # 1c. Paragraph mixing (opening variation, length variation, bridging)
    processed = mix_paragraphs(processed)
    print("[humanizer]   Paragraph structure varied.")

    # ═══ Pass 2+3: LLM Rewrite + Post-LLM Processing (iterative) ═══
    llm = _get_humanizer_llm()

    for iteration in range(max_passes):
        print(f"[humanizer] Pass 2 (iteration {iteration + 1}/{max_passes}): LLM rewrite...")

        # 2. Closed-Loop Multi-Candidate Re-Ranking
        from src.core.humanizer.reranker import generate_and_rerank_candidates
        try:
            best_text, stats = generate_and_rerank_candidates(processed, style_notes, llm=llm)
            processed = best_text
        except Exception as e:
            print(f"[humanizer]   Re-ranking error: {e}")
            # Try fallback LLM
            processed = _try_fallback_rewrite(processed, style_notes, llm)

        # 3. Post-LLM Processing (pure Python)
        print(f"[humanizer] Pass 3 (iteration {iteration + 1}): Post-LLM processing...")
        processed = boost_perplexity(processed, swap_probability=0.45)
        processed = enforce_lexical_diversity(processed)
        processed = inject_human_artifacts(
            processed,
            hedge_probability=0.12,
            parenthetical_probability=0.18,
            cross_ref_probability=0.10,
            emphatic_probability=0.08,
            citation_connector_probability=0.12,
        )

        # 4. Quality Gate
        score = score_candidate(processed)
        cv = score["burstiness_cv"]
        tells = score["residual_tells"]
        composite = score["composite_score"]
        variety = measure_sentence_initial_variety(processed)

        print(f"[humanizer] Quality gate: composite={composite:.1f}, CV={cv:.3f}, tells={tells}, variety={variety:.3f}")

        if composite >= _MIN_COMPOSITE_SCORE and cv >= _MIN_BURSTINESS_CV and variety >= _MIN_INITIAL_VARIETY:
            print(f"[humanizer] Quality gate PASSED at iteration {iteration + 1}")
            break
        elif iteration < max_passes - 1:
            print(f"[humanizer] Quality gate FAILED — running another iteration...")
        else:
            print(f"[humanizer] Quality gate not fully met after {max_passes} iterations — proceeding with best effort")

    # ═══ Pass 5: Final Burstiness Enforcement ═══
    print("[humanizer] Pass 5: Final burstiness enforcement...")
    processed = inject_burstiness(processed)

    final_sentences = _split_into_sentences(processed)
    final_cv = measure_burstiness(final_sentences)
    final_variety = measure_sentence_initial_variety(processed)
    print(f"[humanizer] Final: CV={final_cv:.3f}, variety={final_variety:.3f}, words={len(processed.split())}")

    return processed


def _get_humanizer_llm():
    """Gets the LLM for humanization with cascading fallbacks."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    gemini_candidates = [
        settings.gemini_model,
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
    ]
    seen_models = set()
    model_queue = [m for m in gemini_candidates if not (m in seen_models or seen_models.add(m))]

    if settings.google_api_key and settings.google_api_key not in ("", "GOOGLE_API_KEY"):
        for model_name in model_queue:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=settings.google_api_key,
                )
                print(f"[humanizer] Selected LLM: {model_name}")
                return llm
            except Exception as e:
                print(f"[humanizer] Model {model_name} failed: {e}")

    return get_humanizer_llm()


def _try_fallback_rewrite(text: str, style_notes: str, primary_llm):
    """Fallback rewrite if the primary re-ranking pipeline fails."""
    from src.core.humanizer.reranker import generate_and_rerank_candidates
    from langchain_google_genai import ChatGoogleGenerativeAI
    from src.core.llm.llm_factory import get_llm

    # Try alternate Gemini models
    fallback_models = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest"]
    for model_name in fallback_models:
        if settings.google_api_key and settings.google_api_key not in ("", "GOOGLE_API_KEY"):
            try:
                fallback_llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=settings.google_api_key,
                )
                best_text, _ = generate_and_rerank_candidates(text, style_notes, llm=fallback_llm)
                return best_text
            except Exception as e:
                print(f"[humanizer] Fallback {model_name} failed: {e}")

    # Last resort: use main generator LLM
    try:
        main_llm = get_llm(temperature=0.85)
        best_text, _ = generate_and_rerank_candidates(text, style_notes, llm=main_llm)
        return best_text
    except Exception as e:
        print(f"[humanizer] All fallbacks failed: {e}")
        return text


def humanize_section(section_result: dict, style_notes: str = "", max_passes: int = 2) -> dict:
    """
    Humanize a generated section's text in place while strictly preserving
    all embedded images and figures.

    Args:
        section_result: A dict with 'text', 'sources', 'passed', etc.
        style_notes: Optional style profile text.
        max_passes: Humanization depth (1=Standard, 2=Deep, 3=Maximum).

    Returns:
        The same dict with 'text' replaced by the humanized version.
    """
    raw_text = section_result.get("text", "")
    if not raw_text or not raw_text.strip():
        return section_result

    # 1. Extract any existing image tags
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    images = image_pattern.findall(raw_text)

    # 2. Strip images so LLM only receives clean prose
    clean_text = image_pattern.sub("", raw_text).strip()

    # 3. Full multi-pass humanization pipeline
    humanized_text = humanize_text(clean_text, style_notes, max_passes=max_passes)

    # 4. Re-inject preserved images
    if images:
        paragraphs = [p.strip() for p in humanized_text.split("\n\n") if p.strip()]
        for caption, path_or_spec in images:
            tag = f"![{caption}]({path_or_spec})"
            if len(paragraphs) >= 3:
                paragraphs.insert(2, tag)
            else:
                paragraphs.append(tag)
        humanized_text = "\n\n".join(paragraphs)

    # 5. Attach humanization metrics to the result
    final_score = score_candidate(humanized_text)
    final_variety = measure_sentence_initial_variety(humanized_text)

    section_result["text"] = humanized_text
    section_result["humanization_metrics"] = {
        "burstiness_cv": final_score["burstiness_cv"],
        "residual_tells": final_score["residual_tells"],
        "composite_score": final_score["composite_score"],
        "sentence_initial_variety": final_variety,
        "passes": max_passes,
    }
    return section_result
