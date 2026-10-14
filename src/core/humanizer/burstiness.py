"""
Burstiness Injector — pure Python, no LLM or API calls.

AI text has uniformly medium sentence lengths (15-25 words each), which
detectors flag as low "burstiness". Human writing mixes very short sentences
with long sprawling ones.

This module directly manipulates sentence structure to raise burstiness score
before the text is passed to the LLM humanizer.

UPGRADE: Now includes WINDOW-BASED enforcement. Turnitin scores text in
overlapping 5-10 sentence segments, not as a single document. We now ensure
each 7-sentence sliding window meets the target CV independently.
"""

import re
import random
from typing import Optional


# Sentence splitter — handles common abbreviations to avoid false splits
_ABBREVS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "rev", "gen", "sgt",
    "cpl", "pvt", "capt", "lt", "col", "maj", "brig", "est", "approx",
    "dept", "fig", "vs", "etc", "al", "et", "vol", "no", "e.g", "i.e",
    "cf", "op", "cit", "ca", "pp", "ibid", "loc", "avg",
}

_SPLIT_PATTERN = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z])'
)

_COMMA_SPLIT_CONJUNCTIONS = [
    ", which ", ", where ", ", while ", ", and ", ", but ",
    ", so ", ", yet ", ", because ", ", although ", ", since ",
]

_MERGE_CONJUNCTIONS = [" and ", " while ", " as ", " where "]

# Short punchy sentences organized by semantic category for context-aware injection
_PUNCHY_BY_CATEGORY = {
    "causal": [
        "That explains the gap.",
        "The cause is structural.",
        "This drives the trend.",
        "One factor stands out.",
        "The mechanism is clear.",
        "Root causes differ here.",
        "Correlation is not enough.",
        "The chain is traceable.",
    ],
    "contrastive": [
        "But practice diverges.",
        "Yet exceptions exist.",
        "Still, the reverse holds.",
        "Not always, though.",
        "The contrast is sharp.",
        "Expectations fall short.",
        "Theory says otherwise.",
        "Results push back.",
        "That cuts both ways.",
    ],
    "emphatic": [
        "That matters.",
        "This is key.",
        "The effect persists.",
        "Worth underscoring.",
        "The signal is strong.",
        "Hard to overstate.",
        "The stakes are high.",
        "Precision matters here.",
        "Not a minor point.",
    ],
    "observational": [
        "The pattern holds.",
        "Data backs this up.",
        "Results confirm it.",
        "The trend is clear.",
        "A consistent finding.",
        "Replication bears this out.",
        "Convergent evidence here.",
        "The numbers agree.",
        "Empirically grounded.",
    ],
    "methodological": [
        "Simple in theory.",
        "Practice is messier.",
        "Scale complicates this.",
        "Not trivially solved.",
        "Implementation is harder.",
        "The devil is in details.",
        "Setup matters greatly.",
        "Reproducibility varies.",
    ],
    "concessive": [
        "Granted, gaps remain.",
        "Fair caveats exist.",
        "The picture is partial.",
        "Some noise persists.",
        "Limitations apply.",
        "Not without caveats.",
        "Scope is bounded.",
        "Generalizability is open.",
    ],
}

# Flat list for backward compatibility
_PUNCHY_INSERTS = [s for group in _PUNCHY_BY_CATEGORY.values() for s in group]


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences, respecting abbreviations."""
    # Mark abbreviation positions so we don't split there
    protected = text
    for abbrev in _ABBREVS:
        protected = re.sub(
            rf'\b({re.escape(abbrev)})\.(\s)',
            lambda m: m.group(1) + "@@DOT@@" + m.group(2),
            protected,
            flags=re.IGNORECASE
        )

    raw_sentences = _SPLIT_PATTERN.split(protected)
    # Restore protected dots
    sentences = [s.replace("@@DOT@@", ".") for s in raw_sentences]
    return [s.strip() for s in sentences if s.strip()]


def _word_count(s: str) -> int:
    return len(s.split())


def _try_split_at_comma(sentence: str) -> Optional[list[str]]:
    """Try to split a long sentence at a natural comma-junction."""
    for conjunction in _COMMA_SPLIT_CONJUNCTIONS:
        idx = sentence.find(conjunction)
        if idx > 20:  # don't split too early
            left = sentence[:idx].rstrip(",").strip()
            right = sentence[idx + len(conjunction):].strip()
            # Capitalise the right side
            if right and len(right.split()) >= 5:
                right = right[0].upper() + right[1:]
                return [left + ".", right]
    return None


def _try_merge_sentences(s1: str, s2: str) -> Optional[str]:
    """Attempt to merge two short sentences with a natural connector."""
    # Lowercase the start of s2 to join smoothly
    s2_lower = s2[0].lower() + s2[1:] if s2 else s2
    # Remove trailing period from s1
    s1_body = s1.rstrip(".")
    connector = random.choice(_MERGE_CONJUNCTIONS).strip()
    return f"{s1_body} {connector} {s2_lower}"


def measure_burstiness(sentences: list[str]) -> float:
    """
    Compute burstiness as coefficient of variation of sentence lengths.
    CV = std_dev / mean. Higher is more human-like.
    Human text typically has CV > 0.5; AI text is often < 0.3.
    """
    if len(sentences) < 2:
        return 0.0
    lengths = [_word_count(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std_dev = variance ** 0.5
    return std_dev / mean


def _window_cv(sentences: list[str], start: int, window: int) -> float:
    """Compute CV for a specific window of sentences."""
    window_sents = sentences[start:start + window]
    return measure_burstiness(window_sents)


def _enforce_window_burstiness(
    sentences: list[str],
    window_size: int = 7,
    target_cv: float = 0.45,
) -> list[str]:
    """
    Turnitin analyses text in overlapping ~5-10 sentence SEGMENTS, not globally.
    This function ensures each sliding window of `window_size` sentences meets
    the target CV, by:
      1. Injecting a punchy short sentence within low-CV windows.
      2. Splitting the longest sentence in the window if a split point exists.

    This directly attacks Turnitin's segment-level averaging.
    """
    if len(sentences) < window_size:
        return sentences

    result = list(sentences)
    insertions = 0
    max_insertions = max(1, len(sentences) // 4)
    i = 0

    while i <= len(result) - window_size and insertions < max_insertions:
        cv = _window_cv(result, i, window_size)
        if cv < target_cv:
            # Check if this window already has short sentences
            window_lengths = [
                (_word_count(result[i + j]), i + j) for j in range(window_size)
            ]
            short_count = sum(1 for wc, _ in window_lengths if wc <= 7)

            if short_count == 0:
                # Strategy 1: inject a punchy short sentence after the longest
                longest_idx = max(window_lengths, key=lambda x: x[0])[1]
                insert_pos = longest_idx + 1
                punchy = random.choice(_PUNCHY_INSERTS)
                result.insert(insert_pos, punchy)
                insertions += 1
                i += 1
                continue
            else:
                # Strategy 2: try to split the longest sentence
                wc, long_idx = max(window_lengths, key=lambda x: x[0])
                if wc >= 20:
                    parts = _try_split_at_comma(result[long_idx])
                    if parts:
                        result[long_idx:long_idx + 1] = parts
                        continue

        i += max(1, window_size // 2)  # advance by half-window (overlapping)

    return result


def _enforce_paragraph_burstiness(sentences: list[str], target_cv: float = 0.40) -> list[str]:
    """
    Ensures each paragraph independently has enough burstiness.
    Turnitin scores paragraphs as segments — if a single paragraph is flat,
    it flags the entire surrounding region.
    """
    if len(sentences) < 3:
        return sentences

    cv = measure_burstiness(sentences)
    if cv >= target_cv:
        return sentences

    result = list(sentences)
    attempts = 0

    while measure_burstiness(result) < target_cv and attempts < 3:
        lengths = [(_word_count(result[i]), i) for i in range(len(result))]
        short_count = sum(1 for wc, _ in lengths if wc <= 6)

        if short_count == 0:
            longest_idx = max(lengths, key=lambda x: x[0])[1]
            category = random.choice(list(_PUNCHY_BY_CATEGORY.keys()))
            punchy = random.choice(_PUNCHY_BY_CATEGORY[category])
            insert_pos = min(longest_idx + 1, len(result))
            result.insert(insert_pos, punchy)
        else:
            wc, long_idx = max(lengths, key=lambda x: x[0])
            if wc >= 22:
                parts = _try_split_at_comma(result[long_idx])
                if parts:
                    result[long_idx:long_idx + 1] = parts

        attempts += 1

    return result


def inject_burstiness(text: str, target_cv: float = 0.55, seed: Optional[int] = None) -> str:
    """
    Main entry point. Injects sentence-length variation into AI text.

    Pipeline:
      1. Per-paragraph split/merge transforms (raises global CV)
      2. Paragraph-level CV enforcement (each paragraph meets target independently)
      3. Window-based enforcement (raises per-segment CV for Turnitin)
    """
    if seed is not None:
        random.seed(seed)

    paragraphs = text.split("\n\n")
    result_paragraphs = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            result_paragraphs.append(para)
            continue

        if stripped.startswith("#") or stripped.startswith("!") or _word_count(stripped) < 20:
            result_paragraphs.append(para)
            continue

        sentences = _split_into_sentences(stripped)
        if len(sentences) < 2:
            result_paragraphs.append(para)
            continue

        current_cv = measure_burstiness(sentences)

        # Pass 1: Standard burstiness transforms (split/merge)
        if current_cv < target_cv:
            sentences = _apply_burstiness_transforms(sentences)

        # Pass 2: Paragraph-level CV enforcement
        sentences = _enforce_paragraph_burstiness(sentences, target_cv=0.40)

        # Pass 3: Window-based enforcement (targets Turnitin segment analysis)
        if len(sentences) >= 7:
            sentences = _enforce_window_burstiness(
                sentences, window_size=7, target_cv=0.45
            )

        result_paragraphs.append(" ".join(sentences))

    return "\n\n".join(result_paragraphs)


def _apply_burstiness_transforms(sentences: list[str]) -> list[str]:
    """Apply randomised split/merge transformations to a sentence list."""
    result = list(sentences)
    n = len(result)

    # --- Pass 1: Split some long sentences (>= 25 words) at commas ---
    new_result = []
    for sent in result:
        wc = _word_count(sent)
        if wc >= 25 and random.random() < 0.65:
            parts = _try_split_at_comma(sent)
            if parts:
                new_result.extend(parts)
                continue
        new_result.append(sent)
    result = new_result

    # --- Pass 2: Merge some adjacent short sentences (< 10 words each) ---
    new_result = []
    i = 0
    while i < len(result):
        if (
            i + 1 < len(result)
            and _word_count(result[i]) <= 10
            and _word_count(result[i + 1]) <= 10
            and random.random() < 0.55
        ):
            merged = _try_merge_sentences(result[i], result[i + 1])
            if merged:
                new_result.append(merged)
                i += 2
                continue
        new_result.append(result[i])
        i += 1
    result = new_result

    # --- Pass 3: Insert occasional 1-sentence "punchy" splits from very long sentences ---
    final = []
    for sent in result:
        wc = _word_count(sent)
        if wc >= 35 and random.random() < 0.5:
            parts = _try_split_at_comma(sent)
            if parts and len(parts) == 2:
                # Make the second part really short if possible
                sub_parts = _try_split_at_comma(parts[1])
                if sub_parts:
                    final.extend([parts[0]] + sub_parts)
                    continue
        final.append(sent)

    return final
