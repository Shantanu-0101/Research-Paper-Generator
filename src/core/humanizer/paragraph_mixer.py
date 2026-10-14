"""
Paragraph Mixer — pure Python, no LLM or API calls.

AI text exhibits paragraph-level uniformity: every paragraph follows the same
topic-sentence → evidence → conclusion template, with similar lengths and
identical transition patterns. Turnitin and Originality.ai flag this uniformity
at the segment level.

This module varies paragraph structure to break that signal:
  1. Paragraph Opening Variation — injects questions, concessions, data-first openings
  2. Paragraph Length Variation — splits long or merges short paragraphs to raise CV
  3. Structural Transition Injection — adds bridging sentences between paragraphs
"""

import re
import random
from typing import Optional


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _word_count(text: str) -> int:
    return len(text.split())


# --- Paragraph Opening Injections ---

_QUESTION_OPENERS = [
    "What does this imply for the broader research question?",
    "How does this compare with established findings?",
    "Why does this distinction matter in practice?",
    "What mechanisms might explain these results?",
    "Can these patterns be generalized beyond the current setting?",
    "Where does this leave the open questions in the field?",
    "Is this pattern consistent across different experimental conditions?",
    "What would happen if these assumptions were relaxed?",
    "How robust are these findings under alternative specifications?",
    "Does this hold when we account for confounding variables?",
]

_CONCESSION_OPENERS = [
    "Admittedly, the evidence here is not entirely conclusive.",
    "Granted, this interpretation rests on several assumptions.",
    "To be sure, there are valid objections to this reading of the data.",
    "It would be premature to claim full generalizability at this stage.",
    "One should acknowledge the limitations of the current analysis.",
    "It is worth noting that alternative explanations remain plausible.",
    "While these results are encouraging, caution is warranted.",
    "There are, of course, caveats that deserve attention.",
]

_BRIDGING_SENTENCES = [
    "With that context in place, the following analysis sharpens the picture.",
    "The preceding observations set the stage for a closer look at the data.",
    "Equipped with these definitions, we can now examine the empirical side.",
    "That background motivates the approach described next.",
    "Keeping these constraints in mind, consider the following results.",
    "These preliminary points inform how we interpret the next set of findings.",
    "Against that backdrop, the empirical analysis proceeds as follows.",
    "Having established the theoretical grounding, the discussion now turns to specifics.",
]


def vary_paragraph_openings(text: str, question_prob: float = 0.12, concession_prob: float = 0.10) -> str:
    """
    Injects question-based or concession-based openings into some paragraphs
    to break the AI pattern of always starting with a topic sentence.
    """
    paragraphs = text.split("\n\n")
    result = []

    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!") or _word_count(stripped) < 20:
            result.append(para)
            continue

        # Don't modify the first paragraph (it's the section opener)
        if i == 0:
            result.append(para)
            continue

        roll = random.random()
        if roll < question_prob:
            question = random.choice(_QUESTION_OPENERS)
            result.append(f"{question} {stripped}")
        elif roll < question_prob + concession_prob:
            concession = random.choice(_CONCESSION_OPENERS)
            sentences = _split_sentences(stripped)
            if len(sentences) >= 2:
                result.append(f"{concession} {' '.join(sentences)}")
            else:
                result.append(f"{concession} {stripped}")
        else:
            result.append(para)

    return "\n\n".join(result)


def vary_paragraph_lengths(text: str, target_cv: float = 0.35) -> str:
    """
    Ensures paragraph lengths are varied enough (CV >= target_cv).
    Splits overlong paragraphs and merges very short adjacent ones.
    """
    paragraphs = text.split("\n\n")

    # Separate content paragraphs from structural elements (headings, images)
    indexed_paras = []
    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        is_content = bool(stripped) and not stripped.startswith("#") and not stripped.startswith("!") and _word_count(stripped) > 10
        indexed_paras.append({"text": para, "is_content": is_content, "wc": _word_count(stripped) if is_content else 0})

    content_wcs = [p["wc"] for p in indexed_paras if p["is_content"]]
    if len(content_wcs) < 3:
        return text

    mean_wc = sum(content_wcs) / len(content_wcs)
    if mean_wc == 0:
        return text
    variance = sum((w - mean_wc) ** 2 for w in content_wcs) / len(content_wcs)
    current_cv = (variance ** 0.5) / mean_wc

    if current_cv >= target_cv:
        return text

    # Try to split the longest content paragraph
    result = []
    split_done = False
    for p in indexed_paras:
        if not split_done and p["is_content"] and p["wc"] > mean_wc * 1.5:
            sentences = _split_sentences(p["text"].strip())
            if len(sentences) >= 4:
                mid = len(sentences) // 2
                first_half = " ".join(sentences[:mid])
                second_half = " ".join(sentences[mid:])
                result.append(first_half)
                result.append(second_half)
                split_done = True
                continue
        result.append(p["text"])

    # Try to merge adjacent short paragraphs if no split was possible
    if not split_done:
        merged_result = []
        i = 0
        merge_done = False
        while i < len(result):
            if (
                not merge_done
                and i + 1 < len(result)
                and _word_count(result[i]) < mean_wc * 0.5
                and _word_count(result[i + 1]) < mean_wc * 0.5
                and not result[i].strip().startswith("#")
                and not result[i + 1].strip().startswith("#")
                and not result[i].strip().startswith("!")
                and not result[i + 1].strip().startswith("!")
            ):
                merged = result[i].strip() + " " + result[i + 1].strip()
                merged_result.append(merged)
                i += 2
                merge_done = True
                continue
            merged_result.append(result[i])
            i += 1
        return "\n\n".join(merged_result)

    return "\n\n".join(result)


def inject_bridging_sentences(text: str, probability: float = 0.10) -> str:
    """
    Adds transitional bridging sentences between some paragraphs to create
    more natural discourse flow (instead of abrupt jumps between topics).
    """
    paragraphs = text.split("\n\n")
    if len(paragraphs) < 3:
        return text

    result = [paragraphs[0]]

    for i in range(1, len(paragraphs)):
        para = paragraphs[i].strip()
        prev = paragraphs[i - 1].strip()

        if (
            para and prev
            and not para.startswith("#") and not para.startswith("!")
            and not prev.startswith("#") and not prev.startswith("!")
            and _word_count(para) > 20 and _word_count(prev) > 20
            and random.random() < probability
        ):
            bridge = random.choice(_BRIDGING_SENTENCES)
            result.append(f"{bridge}\n\n{paragraphs[i]}")
        else:
            result.append(paragraphs[i])

    return "\n\n".join(result)


def mix_paragraphs(text: str) -> str:
    """
    Main entry point. Applies all paragraph-level transforms:
      1. Paragraph opening variation (questions, concessions)
      2. Paragraph length variation (split/merge for CV)
      3. Bridging sentence injection
    """
    if not text or not text.strip():
        return text

    text = vary_paragraph_openings(text, question_prob=0.10, concession_prob=0.08)
    text = vary_paragraph_lengths(text, target_cv=0.35)
    text = inject_bridging_sentences(text, probability=0.08)

    return text
