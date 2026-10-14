"""
Human Artifacts Injector — pure Python, no LLM or API calls.

AI-generated text is statistically "too clean" — it flows without interruption,
never self-corrects, never adds asides, never loses its thread. This is a strong
signal for Originality.ai's BERT classifier, which measures semantic coherence
uniformity.

This module injects the imperfections that human academic writers naturally produce:
  - Hedging mid-sentence ("or at least, that is what the data suggests")
  - Self-corrections ("correction: X, not Y")
  - Parenthetical asides ("(which is surprising given the small sample size)")
  - Forward references ("we discuss limitations below")
  - Emphatic short insertions ("this is key.", "and that matters.")
  - Transition variety (enforces rotation across 6 semantic categories)
  - Citation-aware phrasing ("as shown in Table 1", "consistent with the methodology")

These are placed at paragraph boundaries and within long compound sentences
so they disrupt the uniform semantic flow without changing meaning.
"""

import re
import random
from typing import Optional


# ── Hedging phrases — mid-sentence uncertainty markers ───────────────────────
HEDGES = [
    "or at least that's what the data suggests",
    "though this depends on the setup",
    "which may vary across domains",
    "at least in the cases we tested",
    "though this isn't always the case",
    "at least under these conditions",
    "in most configurations we tried",
    "though results can vary",
    "which holds true in practice",
    "or so the evidence suggests",
    "though the magnitude varies",
    "at least to a first approximation",
    "though edge cases complicate the picture",
    "subject to the usual caveats",
    "give or take some variation",
    "which warrants further investigation",
    "although the sample size tempers certainty",
    "pending replication with larger datasets",
    "while the evidence is suggestive rather than conclusive",
    "with the caveat that confounds may play a role",
    "bearing in mind the scope of the current study",
    "at least within the parameter ranges tested here",
    "though the effect size is modest",
    "which deserves a closer look in future work",
    "as a tentative observation",
]

# ── Self-corrections — quick editorial fixes mid-sentence
SELF_CORRECTIONS = [
    " (or rather, across all evaluated configurations)",
    " (more precisely, on the held-out test set)",
    " (strictly speaking, on the validation split)",
    " (to be precise, under controlled conditions)",
    " (we should say: across the majority of trials)",
    " (more accurately, in the training phase)",
]

# ── Parenthetical asides — conversational academic insertions ─────────────────
PARENTHETICALS = [
    "(which is notable given the small sample size)",
    "(a result consistent with prior work in this area)",
    "(though the margin narrows at larger scales)",
    "(an observation worth keeping in mind)",
    "(particularly in low-resource settings)",
    "(we revisit this point in the next section)",
    "(something we did not initially expect)",
    "(the difference is small but consistent)",
    "(this is perhaps unsurprising in retrospect)",
    "(especially when training data is limited)",
    "(a pattern that holds across most tested scenarios)",
    "(worth noting for practitioners)",
    "(the effect is modest but reproducible)",
    "(results varied slightly depending on hyperparameters)",
    "(a caveat that deserves explicit mention)",
    "(not an artifact of the experimental setup, as far as we can tell)",
    "(a question we return to in the discussion)",
    "(the variance is high enough to warrant caution)",
    "(a finding at odds with several earlier reports)",
    "(though the difference may not survive Bonferroni correction)",
    "(perhaps reflecting the sensitivity of the metric chosen)",
    "(which suggests a ceiling effect in certain configurations)",
    "(consistent across three independent runs)",
    "(though one reviewer noted a possible confound here)",
    "(the exact magnitude depends on preprocessing choices)",
    "(a point on which the literature is divided)",
    "(an area ripe for follow-up investigation)",
    "(the trend is visible even in the raw, unprocessed data)",
    "(which dovetails with the theoretical prediction)",
    "(worth flagging for anyone replicating this work)",
]

# ── Forward/backward references — section-relative, no fake table/figure refs ──
CROSS_REFERENCES = [
    "We return to this in the discussion.",
    "This is addressed in more detail below.",
    "We expand on this in the next section.",
    "This connects to a point raised earlier.",
    "Consistent with our earlier observation,",
    "Building on the result above,",
    "As noted in the preceding analysis,",
    "The implications carry forward to the next section.",
    "We revisit this question when discussing limitations.",
    "This dovetails with the observation made above.",
    "A related consideration appears in the methodology section.",
    "The relevance of this finding becomes clearer below.",
    "We defer a fuller treatment to the discussion.",
    "This echoes a pattern seen in the earlier results.",
    "The thread picks up again in the conclusion.",
    "A caveat noted above bears repeating here.",
    "The connection to the broader argument is spelled out next.",
    "We unpack this further when we discuss practical implications.",
    "This raises a question we address shortly.",
    "The preceding analysis sets the stage for what follows.",
]

# ── Punchy emphatic starters for paragraph transitions ───────────────────────
EMPHATIC_STARTERS = [
    "This matters.",
    "And that is the key point.",
    "Here is what that means in practice.",
    "The implication is straightforward.",
    "That said, it is not without caveats.",
    "Still, the result holds up.",
    "Worth highlighting here.",
    "The takeaway is clear.",
    "The upshot is practical.",
    "A word of caution, though.",
    "But there is a catch.",
    "So what changes?",
    "The contrast is instructive.",
    "Put differently: the bottleneck is elsewhere.",
    "One qualification is in order.",
    "The evidence converges.",
]

# ── Transition word rotation (6 semantic categories) ─────────────────────────
# Each category is semantically distinct. We track which category was last used
# and force the next paragraph opener into a different category.

TRANSITION_CATEGORIES = {
    "causal":      ["However,", "Although", "Despite this,", "While", "Even so,", "That said,"],
    "additive":    ["And", "Also,", "In addition,", "Beyond this,", "On top of that,"],
    "contrastive": ["Yet", "Still,", "By contrast,", "At the same time,", "Conversely,"],
    "sequential":  ["First,", "Then,", "Next,", "Finally,", "After that,", "From here,"],
    "emphatic":    ["Notably,", "Critically,", "Importantly,", "Of particular interest,"],
    "human":       ["Here is the thing:", "Worth noting here:", "This is key:", "Interestingly,"],
}

# AI-overused transition openers to replace
_OVERUSED_TRANSITIONS = re.compile(
    r"^(Furthermore[,.]|Moreover[,.]|In conclusion[,.]|In summary[,.]"
    r"|To summarize[,.]|It is important to note|It should be noted|"
    r"|It is worth noting|Notably[,.]|Additionally[,.])",
    re.IGNORECASE | re.MULTILINE,
)

# Discourse-aware connector phrases (no fake table/figure refs)
CITATION_CONNECTORS = [
    "As noted in the methodology section,",
    "Building on the experimental setup described above,",
    "In line with prior findings,",
    "Consistent with the pattern observed earlier,",
    "Consistent with the theoretical framework outlined above,",
    "Extending the reasoning from the previous section,",
    "Drawing on the definitions introduced earlier,",
    "In keeping with the results reported above,",
    "Following the approach outlined previously,",
    "To situate these findings within the larger argument,",
    "Picking up a thread from the literature review,",
    "Echoing a concern raised in the introduction,",
    "To be sure,",
    "Granted,",
    "One might object that",
    "It bears emphasis that",
    "On a related note,",
    "For the sake of completeness,",
    "Lest this be overstated,",
    "In fairness to alternative interpretations,",
]


def inject_human_artifacts(
    text: str,
    hedge_probability: float = 0.15,
    parenthetical_probability: float = 0.20,
    cross_ref_probability: float = 0.12,
    emphatic_probability: float = 0.10,
    citation_connector_probability: float = 0.15,
    seed: Optional[int] = None,
) -> str:
    """
    Main entry point. Injects human writing imperfections at paragraph
    and sentence boundaries to disrupt AI-like semantic uniformity.

    Args:
        text: Input text to process.
        hedge_probability: Probability of injecting a hedge at end of a long sentence.
        parenthetical_probability: Probability of adding a parenthetical after a sentence.
        cross_ref_probability: Probability of adding a cross-reference after a paragraph.
        emphatic_probability: Probability of inserting a punchy emphatic sentence.
        citation_connector_probability: Probability of adding a citation-aware opener.
        seed: Optional random seed.

    Returns:
        Text with human-like imperfections injected.
    """
    if not text or not text.strip():
        return text

    if seed is not None:
        random.seed(seed)

    paragraphs = text.split("\n\n")
    result_paragraphs = []
    last_transition_category: Optional[str] = None

    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if not stripped:
            result_paragraphs.append(para)
            continue

        # Skip headings, images, very short paragraphs
        if stripped.startswith("#") or stripped.startswith("!") or len(stripped.split()) < 15:
            result_paragraphs.append(para)
            continue

        processed = stripped

        # Step 1: Replace overused transition openers with rotated alternatives
        processed, last_transition_category = _rotate_transition(
            processed, last_transition_category
        )

        # Step 2: Inject citation-aware paragraph opener (some paragraphs)
        if i > 0 and random.random() < citation_connector_probability:
            connector = random.choice(CITATION_CONNECTORS)
            # Only add if paragraph doesn't already start with a connector
            first_word = processed.split()[0].lower() if processed.split() else ""
            if first_word not in {"consistent", "as", "building", "in", "furthermore", "moreover"}:
                processed = connector + " " + processed[0].lower() + processed[1:]

        # Step 3: Inject parenthetical asides after some sentences
        processed = _inject_parentheticals(processed, parenthetical_probability)

        # Step 4: Inject hedges at end of some longer sentences
        processed = _inject_hedges(processed, hedge_probability)

        # Step 5: Inject emphatic punchy sentence between long paragraphs
        if random.random() < emphatic_probability and len(processed.split()) > 60:
            emphatic = random.choice(EMPHATIC_STARTERS)
            # Insert after roughly the first half of the paragraph
            sentences = _simple_sentence_split(processed)
            mid = max(1, len(sentences) // 2)
            sentences.insert(mid, emphatic)
            processed = " ".join(sentences)

        # Step 6: Inject cross-reference at end of some paragraphs
        if random.random() < cross_ref_probability:
            cross_ref = random.choice(CROSS_REFERENCES)
            processed = processed.rstrip(".") + ". " + cross_ref

        result_paragraphs.append(processed)

    return "\n\n".join(result_paragraphs)


def enforce_transition_diversity(text: str) -> str:
    """
    Standalone function: scans all paragraph openers and replaces overused
    AI transition words with a rotating set from 6 semantic categories.

    Can be called independently without the full artifact injection pipeline.
    """
    if not text or not text.strip():
        return text

    paragraphs = text.split("\n\n")
    result_paragraphs = []
    last_category: Optional[str] = None

    for para in paragraphs:
        stripped = para.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            result_paragraphs.append(para)
            continue
        processed, last_category = _rotate_transition(stripped, last_category)
        result_paragraphs.append(processed)

    return "\n\n".join(result_paragraphs)


def _rotate_transition(para: str, last_category: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Replaces overused AI transition openers with alternatives from a category
    different from the last used category.
    """
    match = _OVERUSED_TRANSITIONS.match(para)
    if not match:
        return para, last_category

    # Choose a category that's different from the last one used
    all_cats = list(TRANSITION_CATEGORIES.keys())
    available = [c for c in all_cats if c != last_category]
    chosen_category = random.choice(available)
    chosen_transition = random.choice(TRANSITION_CATEGORIES[chosen_category])

    # Replace the matched opener
    rest = para[match.end():].strip()
    if rest:
        # Ensure the rest of the sentence is properly capitalised
        rest = rest[0].upper() + rest[1:] if rest else rest
        new_para = chosen_transition + " " + rest
    else:
        new_para = chosen_transition

    return new_para, chosen_category


def _inject_parentheticals(para: str, probability: float) -> str:
    """Inject parenthetical asides after some sentences."""
    sentences = _simple_sentence_split(para)
    result = []
    for sent in sentences:
        result.append(sent)
        word_count = len(sent.split())
        # Only inject after medium-to-long sentences (not tiny fragments)
        if word_count >= 12 and random.random() < probability:
            aside = random.choice(PARENTHETICALS)
            # Inject by modifying last sentence: append parenthetical before the period
            if result[-1].endswith("."):
                result[-1] = result[-1][:-1] + " " + aside + "."
            else:
                result[-1] = result[-1] + " " + aside
    return " ".join(result)


def _inject_hedges(para: str, probability: float) -> str:
    """Inject hedging phrases at the end of some longer sentences."""
    sentences = _simple_sentence_split(para)
    result = []
    for sent in sentences:
        word_count = len(sent.split())
        if word_count >= 18 and random.random() < probability:
            hedge = random.choice(HEDGES)
            # Insert the hedge just before the final period
            if sent.endswith("."):
                sent = sent[:-1] + ", " + hedge + "."
            else:
                sent = sent + ", " + hedge
        result.append(sent)
    return " ".join(result)


def _simple_sentence_split(text: str) -> list[str]:
    """Fast sentence splitter for artifact injection (no abbreviation handling needed)."""
    # Split on period/exclamation/question followed by space and uppercase
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [p.strip() for p in parts if p.strip()]
