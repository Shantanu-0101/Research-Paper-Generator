"""
Sentence Restructurer — pure Python, no LLM or API calls.

Attacks Turnitin's sentence structure analysis by breaking the Subject-Verb-Object
uniformity that AI text exhibits. Human writers naturally front-load subordinate
clauses, start sentences with adverbs or prepositional phrases, and vary their
openings. AI almost never does.

Three transforms:
  1. Clause reordering — moves trailing subordinate clauses to the front
  2. Sentence-initial diversification — breaks runs of same-type openings
  3. Occasional voice variation — adjusts passive/active balance
"""

import re
import random
from typing import Optional


# --- Clause Reordering ---

_SUBORDINATE_TAIL_PATTERNS = [
    (re.compile(r",\s*(although\s+.+)$", re.IGNORECASE), "Although"),
    (re.compile(r",\s*(because\s+.+)$", re.IGNORECASE), "Because"),
    (re.compile(r",\s*(since\s+.+)$", re.IGNORECASE), "Since"),
    (re.compile(r",\s*(while\s+.+)$", re.IGNORECASE), "While"),
    (re.compile(r",\s*(even though\s+.+)$", re.IGNORECASE), "Even though"),
    (re.compile(r",\s*(whereas\s+.+)$", re.IGNORECASE), "Whereas"),
    (re.compile(r",\s*(unless\s+.+)$", re.IGNORECASE), "Unless"),
    (re.compile(r",\s*(though\s+.+)$", re.IGNORECASE), "Though"),
    (re.compile(r",\s*(provided that\s+.+)$", re.IGNORECASE), "Provided that"),
    (re.compile(r",\s*(given that\s+.+)$", re.IGNORECASE), "Given that"),
]

# --- Sentence-Initial Categories ---

_ARTICLE_START = re.compile(r"^(the|a|an)\s", re.IGNORECASE)
_PRONOUN_START = re.compile(r"^(it|this|that|these|those|they|we|he|she)\s", re.IGNORECASE)
_ADVERB_START = re.compile(
    r"^(however|interestingly|notably|importantly|crucially|conversely|"
    r"similarly|consequently|accordingly|admittedly|indeed|perhaps|"
    r"arguably|surprisingly|fortunately|unfortunately|curiously|"
    r"specifically|alternatively|generally|typically|essentially|"
    r"in practice|in particular|in contrast|by contrast|for instance|"
    r"to that end|at the same time|on the other hand|in other words)\b",
    re.IGNORECASE,
)
_PREP_START = re.compile(
    r"^(in|on|at|for|from|with|by|of|to|across|among|between|through|within|"
    r"under|over|during|after|before|against|beyond|despite|without)\s",
    re.IGNORECASE,
)
_CONJUNCTION_START = re.compile(r"^(and|but|yet|so|or|nor)\s", re.IGNORECASE)
_GERUND_START = re.compile(r"^[A-Z][a-z]+ing\s", re.IGNORECASE)


def _classify_sentence_start(sentence: str) -> str:
    s = sentence.strip()
    if _adverb_match(s):
        return "adverb"
    if _GERUND_START.match(s):
        return "gerund"
    if _CONJUNCTION_START.match(s):
        return "conjunction"
    if _PREP_START.match(s):
        return "preposition"
    if _ARTICLE_START.match(s):
        return "article"
    if _PRONOUN_START.match(s):
        return "pronoun"
    return "other"


def _adverb_match(s: str) -> bool:
    return bool(_ADVERB_START.match(s))


# Adverbial openers to inject for diversity
_ADVERBIAL_OPENERS = [
    "Interestingly,",
    "In practice,",
    "From a broader perspective,",
    "Along these lines,",
    "On closer inspection,",
    "In a related vein,",
    "From a computational standpoint,",
    "At a higher level,",
    "In the broader context,",
    "Looking at this differently,",
    "On a practical note,",
    "To put this in perspective,",
    "In operational terms,",
    "Seen from another angle,",
    "Taking a step back,",
    "At a fundamental level,",
    "In quantitative terms,",
    "Viewed through this lens,",
    "Empirically speaking,",
    "On the methodological side,",
]

# Gerund-phrase openers
_GERUND_OPENERS = [
    "Drawing on these observations,",
    "Considering the constraints involved,",
    "Building on this foundation,",
    "Turning to the empirical side,",
    "Looking across the literature,",
    "Extending this line of reasoning,",
    "Examining the underlying patterns,",
    "Accounting for these variations,",
    "Setting aside minor discrepancies,",
    "Revisiting the core question,",
    "Weighing the available evidence,",
    "Probing deeper into the mechanism,",
]

# Prepositional phrase openers
_PREPOSITIONAL_OPENERS = [
    "In the context of these findings,",
    "Under these conditions,",
    "Across the tested configurations,",
    "Within this framework,",
    "Beyond the immediate results,",
    "Among the factors considered,",
    "Despite the limitations,",
    "Throughout the evaluation,",
    "For these particular cases,",
    "Between the compared approaches,",
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def reorder_clauses(text: str, probability: float = 0.30) -> str:
    """
    Moves trailing subordinate clauses to the front of sentences.
    "X improves Y, although Z remains" → "Although Z remains, X improves Y."
    """
    paragraphs = text.split("\n\n")
    result = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!") or len(stripped.split()) < 15:
            result.append(para)
            continue

        sentences = _split_sentences(stripped)
        new_sentences = []

        for sent in sentences:
            if random.random() > probability or len(sent.split()) < 12:
                new_sentences.append(sent)
                continue

            reordered = False
            for pattern, conjunction in _SUBORDINATE_TAIL_PATTERNS:
                match = pattern.search(sent)
                if match:
                    subordinate = match.group(1).strip().rstrip(".")
                    main_clause = sent[:match.start()].strip()
                    # Capitalize the subordinate, lowercase the main clause start
                    sub_cap = subordinate[0].upper() + subordinate[1:]
                    main_lower = main_clause[0].lower() + main_clause[1:]
                    new_sent = f"{sub_cap}, {main_lower}."
                    new_sentences.append(new_sent)
                    reordered = True
                    break

            if not reordered:
                new_sentences.append(sent)

        result.append(" ".join(new_sentences))

    return "\n\n".join(result)


def diversify_sentence_starts(text: str, max_consecutive_same: int = 2) -> str:
    """
    Breaks runs of 3+ consecutive sentences starting the same way
    by injecting an adverbial, gerund, or prepositional opener.
    """
    paragraphs = text.split("\n\n")
    result = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!") or len(stripped.split()) < 20:
            result.append(para)
            continue

        sentences = _split_sentences(stripped)
        if len(sentences) < 3:
            result.append(para)
            continue

        classifications = [_classify_sentence_start(s) for s in sentences]
        new_sentences = list(sentences)

        i = 0
        while i < len(new_sentences):
            # Check for a run of max_consecutive_same+1 or more of the same type
            if i >= max_consecutive_same:
                recent_types = [_classify_sentence_start(new_sentences[j]) for j in range(i - max_consecutive_same, i + 1)]
                if len(set(recent_types)) == 1 and recent_types[0] in ("article", "pronoun", "other"):
                    new_sentences[i] = _add_opener(new_sentences[i])
            i += 1

        result.append(" ".join(new_sentences))

    return "\n\n".join(result)


def _add_opener(sentence: str) -> str:
    """Prepends a diversifying opener to a sentence."""
    opener_pool = random.choice([_ADVERBIAL_OPENERS, _GERUND_OPENERS, _PREPOSITIONAL_OPENERS])
    opener = random.choice(opener_pool)

    s = sentence.strip()
    if not s:
        return s

    # Lowercase the original sentence start
    new_start = s[0].lower() + s[1:]
    return f"{opener} {new_start}"


def measure_sentence_initial_variety(text: str) -> float:
    """
    Returns the fraction of sentences that do NOT start with an article or pronoun.
    Higher is better (more human-like). Target: >= 0.40
    """
    sentences = _split_sentences(text)
    if not sentences:
        return 0.5

    non_standard = sum(
        1 for s in sentences
        if not _ARTICLE_START.match(s.strip()) and not _PRONOUN_START.match(s.strip())
    )
    return non_standard / len(sentences)


def restructure_sentences(text: str, clause_reorder_prob: float = 0.25) -> str:
    """
    Main entry point. Applies all sentence restructuring transforms:
      1. Clause reordering (trailing subordinates → front)
      2. Sentence-initial diversification (break same-type runs)
    """
    if not text or not text.strip():
        return text

    text = reorder_clauses(text, probability=clause_reorder_prob)
    text = diversify_sentence_starts(text, max_consecutive_same=2)

    return text
