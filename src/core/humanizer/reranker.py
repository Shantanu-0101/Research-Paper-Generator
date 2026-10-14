"""
Closed-Loop Multi-Candidate Re-Ranking Engine.
Based on MASH (Multi-stage Alignment for Style Humanization) and AuthorMist research.

Pipeline:
  1. Multi-Candidate Generation: Produces 2 distinct candidate rewrites using
     different prompt strategies designed specifically to evade cutting-edge
     detectors like Originality.ai and Turnitin.
  2. Multi-Metric Scoring: Scores each candidate on:
     - Burstiness CV (Coefficient of Variation of sentence length)
     - Residual AI cliché / tell count
     - Human stylistic markers (em-dashes, parentheticals, short punchy sentences)
  3. Re-Ranking & Selection: Picks the candidate with the highest human composite score.
  4. Closed-Loop Refinement: If any residual AI tells remain, runs a targeted
     feedback pass to fix only those specific sentences.
"""

import re
from typing import Tuple, List, Dict
from src.core.config import settings
from src.core.humanizer.burstiness import _split_into_sentences, measure_burstiness, inject_burstiness
from src.core.humanizer.patterns import PATTERNS


# ── AI Tell Regexes (High-Frequency Markers used by Originality.ai / Turnitin) ──
AI_TELL_PATTERNS = [
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\bin conclusion\b",
    r"\bit is essential to (note|remember|highlight)\b",
    r"\bit is important to (note|remember|highlight)\b",
    r"\bdelves? into\b",
    r"\bserves? as a testament\b",
    r"\btapestry\b",
    r"\bpivotal\b",
    r"\bcrucial\b",
    r"\bunderscores?\b",
    r"\bfosters?\b",
    r"\brealm\b",
    r"\blandscape\b",
    r"\bparadigm shift\b",
    r"\btransformative\b",
    r"\bseamless integration\b",
    r"\bbeacon\b",
    r"\bgroundbreaking\b",
    r"\bvibrant\b",
    r"\bholistic\b",
    r"\binterplay\b",
    r"\bcornerstone\b",
    r"\bparamount\b",
    r"\bnot only .*? but also\b",
    r"\ba testament to\b",
    r"\bnavigat(e|ing) the complexities\b",
    r"\bunprecedented\b",
    r"\bgame-?changer\b",
]

COMPILED_AI_TELLS = [re.compile(pat, re.IGNORECASE) for pat in AI_TELL_PATTERNS]


PROMPT_CANDIDATE_A = """You are an elite academic researcher rewriting text to pass strict AI detectors (Originality.ai and Turnitin) with 100% human authenticity.

Rewrite the text using an EMPIRICAL RESEARCHER VOICE with authentic structural asymmetry:
1. EMPIRICAL HUMAN VOICE:
   - Frame points actively from the researchers' perspective ('We observed that...', 'In our pipeline...', 'Our tests indicate...').
   - Replace generic textbook summaries with concrete technical observations.
2. STRUCTURAL ASYMMETRY:
   - Use em-dashes (—) to insert clarifications or caveats mid-sentence.
   - Use parenthetical notes, e.g. '(often by a noticeable margin)', '(though real-world setups complicate this)'.
   - Insert occasional very short 3-5 word sentences ('Scale is unforgiving.', 'The bottleneck is real.', 'That changes things.').
3. STRICT VOCABULARY SANITIZATION:
   - Strictly forbid: furthermore, moreover, in conclusion, delves into, testament, tapestry, pivotal, crucial, underscores, fosters, realm, landscape, paradigm shift, transformative, seamless integration, beacon, groundbreaking, vibrant, holistic, cornerstone.
   - Use direct Anglo-Saxon action verbs ('shows', 'helps', 'tackles', 'breaks down', 'maps out').

Do NOT add any intro, options, commentary, or markdown code blocks. Output ONLY the raw rewritten text directly.

TEXT TO REWRITE:
{text}
"""


PROMPT_CANDIDATE_B = """You are an expert academic editor rewriting text to evade neural text detectors (Originality.ai and Turnitin).

Rewrite the text using ASYMMETRIC RHYTHM AND CONVERSATIONAL ACADEMIC PHRASING:
1. VARY SENTENCE RHYTHM DRASTICALLY:
   - Start 1-2 sentences with conjunctions ('And while...', 'Yet in practice...', 'But scaling is difficult.').
   - Alternate between a punchy 4-word sentence and a 25-word multi-clause sentence.
   - Use semicolons (;) or em-dashes (—) to break the predictable 'Subject-Verb-Object' LLM cadence.
2. PLAIN DIRECT VOCABULARY:
   - Replace high-register Latinate filler ('emerged as a pivotal mechanism', 'delves into intricate mechanisms') with plain verbs ('helps organize', 'looks at how').
   - Strictly ban: furthermore, moreover, in conclusion, tapestry, realm, landscape, paradigm shift, transformative, testament, underscores, fosters.
3. PRESERVE ACCURACY:
   - Keep every technical concept, citation, fact, number, and equation strictly intact.

Do NOT add any intro, options, commentary, or markdown code blocks. Output ONLY the raw rewritten text directly.

TEXT TO REWRITE:
{text}
"""


PROMPT_CANDIDATE_C = """You are a senior research scientist rewriting text to evade AI detection systems (Turnitin, Originality.ai, CopyLeaks).

Rewrite the text using ANALYTICAL RESEARCH VOICE with deliberate structural imperfection:
1. ANALYTICAL VOICE:
   - Frame findings with measured confidence ('The data point toward...', 'On balance, the evidence favors...', 'A tentative reading suggests...').
   - Occasionally hedge mid-sentence with parenthetical caveats ('(though the sample is small)', '(a caveat worth noting)').
   - Use first-person plural sparingly but strategically ('We find that...', 'Our analysis indicates...').
2. DELIBERATE IMPERFECTIONS (human writers aren't perfectly polished):
   - Start 1-2 sentences with conjunctions ('And yet...', 'But the data resist...').
   - Include at least one rhetorical question ('What accounts for this discrepancy?').
   - Use a semicolon or colon to break at least two sentences.
   - Vary paragraph lengths noticeably — one short (2-3 sentences), one long (6-8 sentences).
3. VOCABULARY SANITIZATION:
   - Strictly ban: furthermore, moreover, in conclusion, delves into, testament, tapestry, pivotal, crucial, underscores, fosters, realm, landscape, paradigm shift, transformative, seamless, beacon, groundbreaking, vibrant, holistic, cornerstone, paramount, unprecedented.
   - Prefer plain verbs: 'shows', 'suggests', 'points to', 'complicates', 'challenges'.

Do NOT add any intro, options, commentary, or markdown code blocks. Output ONLY the raw rewritten text directly.

TEXT TO REWRITE:
{text}
"""


PROMPT_REFINEMENT = """You are an expert editor polishing a text that was flagged by an AI detector.

The text still contains these specific issues:
{issues}

Task:
Rewrite the flagged parts to completely eliminate these issues:
- Replace the flagged phrases with natural conversational academic language.
- Introduce an em-dash (—) or parenthetical aside to disrupt predictable token sequences.
- Keep all facts, data, citations, and meaning 100% intact.
- Return ONLY the final polished text directly.

TEXT:
{text}
"""


def _paragraph_uniformity_penalty(text: str) -> float:
    """
    Penalizes text where all paragraphs have similar sentence counts or
    similar word counts (a strong AI uniformity signal).
    Returns a penalty value >= 0 (higher = worse).
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.split()) > 10]
    if len(paragraphs) < 3:
        return 0.0

    # Sentence count uniformity
    sent_counts = [len(_split_into_sentences(p)) for p in paragraphs]
    if all(c == sent_counts[0] for c in sent_counts):
        return 30.0  # All paragraphs have the same number of sentences

    mean_sc = sum(sent_counts) / len(sent_counts)
    if mean_sc > 0:
        sc_cv = (sum((c - mean_sc) ** 2 for c in sent_counts) / len(sent_counts)) ** 0.5 / mean_sc
        if sc_cv < 0.20:
            return 20.0  # Very uniform paragraph structure

    return 0.0


def _sentence_initial_variety_score(text: str) -> float:
    """
    Rewards text where sentences start with diverse structures.
    Returns a score >= 0 (higher = more variety = more human).
    """
    sentences = _split_into_sentences(text)
    if len(sentences) < 5:
        return 0.0

    article_pronoun = re.compile(r"^(the|a|an|this|that|these|those|it|its|they|their|we|our|he|she|his|her)\b", re.IGNORECASE)
    non_standard = sum(1 for s in sentences if not article_pronoun.match(s.strip()))
    variety_ratio = non_standard / len(sentences)

    # Score: 0 to 40 based on variety ratio
    return min(40.0, variety_ratio * 80.0)


def score_candidate(text: str) -> Dict[str, float]:
    """
    Evaluates a candidate rewrite on objective human linguistic metrics:
      - burstiness_cv: Coefficient of variation of sentence length (target >= 0.55)
      - residual_tells: Count of AI cliche keywords found
      - human_markers: Count of em-dashes, parentheticals, conjunction openers, short sentences
      - paragraph_penalty: Penalty for uniform paragraph structure
      - initial_variety: Reward for diverse sentence openings
      - composite_score: Combined score (higher is more human)
    """
    if not text or not text.strip():
        return {"composite_score": -999, "burstiness_cv": 0.0, "residual_tells": 99, "human_markers": 0, "found_tells": []}

    sentences = _split_into_sentences(text)
    cv = measure_burstiness(sentences) if sentences else 0.0

    # Count residual AI tells
    found_tells = []
    for pat in COMPILED_AI_TELLS:
        matches = pat.findall(text)
        if matches:
            found_tells.extend(matches)
    tell_count = len(found_tells)

    # Count authentic human markers
    human_markers = 0.0
    human_markers += len(re.findall(r"—|--", text)) * 2
    human_markers += len(re.findall(r"\([^\)]+\)", text)) * 1.5
    human_markers += len(re.findall(r";", text)) * 1.5
    short_sentences = sum(1 for s in sentences if len(s.split()) <= 6)
    human_markers += short_sentences * 2.0
    conjunction_openers = sum(1 for s in sentences if re.match(r"^(And|But|Yet|So)\b", s.strip()))
    human_markers += conjunction_openers * 2.0
    # Rhetorical questions
    questions = sum(1 for s in sentences if s.strip().endswith("?"))
    human_markers += questions * 3.0

    # Paragraph-level penalties and bonuses
    para_penalty = _paragraph_uniformity_penalty(text)
    initial_variety = _sentence_initial_variety_score(text)

    # Composite Human Score:
    # Burstiness CV: +120 * CV (increased weight)
    # Human markers: +10 * markers
    # Initial variety: +1 * score
    # Paragraph penalty: -1 * penalty
    # AI tells: -50 * count
    composite = (cv * 120.0) + (human_markers * 10.0) + initial_variety - para_penalty - (tell_count * 50.0)

    return {
        "composite_score": composite,
        "burstiness_cv": cv,
        "residual_tells": tell_count,
        "human_markers": human_markers,
        "found_tells": found_tells,
    }


def generate_and_rerank_candidates(
    text: str,
    style_notes: str = "",
    llm = None,
) -> Tuple[str, Dict]:
    """
    Closed-Loop Multi-Candidate Re-Ranking Pipeline:
      1. Generates 3 distinct candidate rewrites (A, B, C).
      2. Scores all candidates with multi-metric human evaluation.
      3. Selects the highest-scoring candidate.
      4. Closed-loop pass: If the winning candidate still has residual tells,
         refines it targetedly before returning.
    """
    if not text or not text.strip():
        return text, {}

    bursty_input = inject_burstiness(text)

    style_injection = f"\n\nAUTHOR STYLE GUIDELINES:\n{style_notes}" if style_notes else ""

    prompt_a = PROMPT_CANDIDATE_A.format(text=bursty_input) + style_injection
    prompt_b = PROMPT_CANDIDATE_B.format(text=bursty_input) + style_injection
    prompt_c = PROMPT_CANDIDATE_C.format(text=bursty_input) + style_injection

    def _invoke_clean(prompt: str) -> str:
        try:
            res = llm.invoke(prompt)
            content = res.content
            if isinstance(content, list):
                content = "\n".join(
                    p if isinstance(p, str) else p.get("text", str(p)) for p in content
                )
            return content.strip()
        except Exception as e:
            print(f"[reranker] LLM invoke error: {e}")
            return bursty_input

    cand_a = _invoke_clean(prompt_a)
    cand_b = _invoke_clean(prompt_b)
    cand_c = _invoke_clean(prompt_c)

    score_a = score_candidate(cand_a)
    score_b = score_candidate(cand_b)
    score_c = score_candidate(cand_c)

    candidates = [
        ("Candidate A (Empirical Researcher)", cand_a, score_a),
        ("Candidate B (Asymmetric Rhythm)", cand_b, score_b),
        ("Candidate C (Analytical Research)", cand_c, score_c),
    ]

    for label, _, score in candidates:
        print(f"[reranker] {label} score: {score['composite_score']:.1f} (CV: {score['burstiness_cv']:.2f}, tells: {score['residual_tells']}, markers: {score['human_markers']:.1f})")

    winner_label, winner_text, winner_score = max(candidates, key=lambda x: x[2]["composite_score"])
    print(f"[reranker] Selected winner: {winner_label}")

    # Closed-Loop Targeted Refinement (if tells remain)
    if winner_score["residual_tells"] > 0:
        issues_desc = f"Found remaining AI phrases: {', '.join(str(t) for t in winner_score['found_tells'])}"
        print(f"[reranker] Running closed-loop refinement on issues: {issues_desc}")
        refine_prompt = PROMPT_REFINEMENT.format(issues=issues_desc, text=winner_text)
        refined_text = _invoke_clean(refine_prompt)
        refined_score = score_candidate(refined_text)
        print(f"[reranker] Refined score: {refined_score['composite_score']:.1f} (tells: {refined_score['residual_tells']})")

        if refined_score["residual_tells"] <= winner_score["residual_tells"]:
            winner_text = refined_text
            winner_score = refined_score

    return winner_text, winner_score
