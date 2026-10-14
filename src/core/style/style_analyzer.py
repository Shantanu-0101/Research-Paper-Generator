import re
import statistics
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class StyleProfile:

    avg_sentence_length: float
    sentence_length_std: float
    lexical_diversity: float
    top_transition_words: list[tuple[str, int]]
    passive_voice_ratio: float
    avg_paper_word_count: int = 2500
    avg_paragraph_length: float = 80.0
    paragraph_length_std: float = 30.0
    sentence_initial_variety: float = 0.5
    questions_per_1000_words: float = 0.0
    first_person_ratio: float = 0.0
    avg_paragraphs_per_section: float = 5.0

    def to_prompt_text(self) -> str:
        transitions = ", ".join(w for w, _ in self.top_transition_words) or "minimal, varied"

        voice_desc = "Use first-person plural (we/our) frequently" if self.first_person_ratio > 0.02 else "Use third-person or impersonal voice predominantly"

        para_desc = (
            f"Average paragraph length: ~{self.avg_paragraph_length:.0f} words "
            f"(variation: ±{self.paragraph_length_std:.0f} words). "
            f"Aim for ~{self.avg_paragraphs_per_section:.0f} paragraphs per section."
        )

        variety_desc = (
            "High sentence-initial variety — frequently start sentences with subordinate clauses, "
            "adverbs, prepositional phrases, or gerunds, not just the subject."
            if self.sentence_initial_variety > 0.45
            else "Moderate sentence-initial variety — occasionally vary sentence openings."
        )

        question_desc = ""
        if self.questions_per_1000_words > 0.5:
            question_desc = " Occasionally use rhetorical questions (the reference papers do)."

        return (
            f"Average sentence length: {self.avg_sentence_length:.0f} words "
            f"(typical variation: ±{self.sentence_length_std:.0f} words — "
            f"{'mix short and long sentences' if self.sentence_length_std > 8 else 'fairly uniform sentence length'}). "
            f"Vocabulary richness: {'high, varied wording' if self.lexical_diversity > 0.5 else 'moderate, some repeated terms'}. "
            f"Frequently used transition/hedging words: {transitions}. "
            f"Passive voice usage: {'frequent' if self.passive_voice_ratio > 0.3 else 'occasional'}. "
            f"{voice_desc}. "
            f"{para_desc} "
            f"{variety_desc}"
            f"{question_desc}"
        )


TRANSITION_WORDS = [
    "however", "furthermore", "moreover", "therefore", "thus", "consequently",
    "additionally", "nevertheless", "specifically", "notably", "importantly",
]

# Heuristic passive-voice detector: "is/was/were/been/being" + a word ending in -ed.
# Not linguistically perfect (misses irregular past participles like "written",
# catches false positives like "interested"), but good enough as a style signal.
PASSIVE_PATTERN = re.compile(r"\b(is|was|were|been|being|are)\s+\w+ed\b", re.IGNORECASE)


_ARTICLE_PRONOUN_STARTS = re.compile(
    r"^(the|a|an|this|that|these|those|it|its|they|their|we|our|he|she|his|her)\b",
    re.IGNORECASE,
)

_FIRST_PERSON_PATTERN = re.compile(r"\b(we|our|us)\b", re.IGNORECASE)

_QUESTION_PATTERN = re.compile(r"\?\s")


def analyze_style(chunks: list[dict]) -> StyleProfile:
    full_text = " ".join(c["text"] for c in chunks)

    source_files = {c.get("metadata", {}).get("source", "unknown") for c in chunks}
    num_papers = len(source_files) if source_files and "unknown" not in source_files else 5
    num_papers = max(1, num_papers)

    words = re.findall(r"\b\w+\b", full_text.lower())
    total_words = len(words)
    avg_paper_words = total_words // num_papers

    sentences = [s for s in re.split(r'(?<=[.!?])\s+', full_text) if s.strip()]
    sentence_lengths = [len(s.split()) for s in sentences]

    avg_len = statistics.mean(sentence_lengths) if sentence_lengths else 0
    len_std = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0

    lexical_diversity = len(set(words)) / len(words) if words else 0

    word_counts = Counter(words)
    found_transitions = [(w, word_counts[w]) for w in TRANSITION_WORDS if word_counts[w] > 0]
    found_transitions.sort(key=lambda x: -x[1])

    passive_matches = len(PASSIVE_PATTERN.findall(full_text))
    passive_voice_ratio = passive_matches / len(sentences) if sentences else 0

    # --- New features ---

    # Paragraph-level statistics
    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip() and len(p.split()) > 10]
    para_lengths = [len(p.split()) for p in paragraphs]
    avg_para_len = statistics.mean(para_lengths) if para_lengths else 80.0
    para_len_std = statistics.stdev(para_lengths) if len(para_lengths) > 1 else 30.0

    # Sentence-initial variety: % of sentences NOT starting with article/pronoun
    if sentences:
        non_standard_starts = sum(
            1 for s in sentences if not _ARTICLE_PRONOUN_STARTS.match(s.strip())
        )
        sentence_initial_variety = non_standard_starts / len(sentences)
    else:
        sentence_initial_variety = 0.5

    # Questions per 1000 words
    question_count = len(_QUESTION_PATTERN.findall(full_text))
    questions_per_1k = (question_count / total_words * 1000) if total_words > 0 else 0.0

    # First-person ratio (we/our/us per total words)
    first_person_count = len(_FIRST_PERSON_PATTERN.findall(full_text))
    first_person_ratio = first_person_count / total_words if total_words > 0 else 0.0

    # Average paragraphs per section (estimate: count paragraphs between headings)
    heading_pattern = re.compile(r"^#{1,4}\s", re.MULTILINE)
    sections = heading_pattern.split(full_text)
    section_para_counts = []
    for sec in sections:
        sec_paras = [p for p in sec.split("\n\n") if p.strip() and len(p.split()) > 10]
        if sec_paras:
            section_para_counts.append(len(sec_paras))
    avg_paras_per_section = statistics.mean(section_para_counts) if section_para_counts else 5.0

    return StyleProfile(
        avg_sentence_length=avg_len,
        sentence_length_std=len_std,
        lexical_diversity=lexical_diversity,
        top_transition_words=found_transitions[:5],
        passive_voice_ratio=passive_voice_ratio,
        avg_paper_word_count=avg_paper_words,
        avg_paragraph_length=avg_para_len,
        paragraph_length_std=para_len_std,
        sentence_initial_variety=sentence_initial_variety,
        questions_per_1000_words=questions_per_1k,
        first_person_ratio=first_person_ratio,
        avg_paragraphs_per_section=avg_paras_per_section,
    )
