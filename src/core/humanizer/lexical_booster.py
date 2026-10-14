"""
Lexical Booster — pure Python, no LLM or API calls.

Two attack vectors against AI detectors (Originality.ai, Turnitin):

1. PERPLEXITY BOOSTING:
   AI models always choose the highest-probability token for a given context.
   Detectors (especially Originality.ai's BERT model) flag text where consecutive
   tokens are statistically predictable. This module replaces AI-preferred
   high-register Latinate words with lower-probability Anglo-Saxon alternatives
   that a human writer would naturally use, raising the perplexity score.

2. LEXICAL DIVERSITY ENFORCEMENT (TTR — Type-Token Ratio):
   AI tends to reuse the same vocabulary repeatedly within a paragraph.
   Human writing naturally varies word choice. This module tracks term frequency
   per paragraph and rotates synonyms when a word is overused.
"""

import re
import random
from typing import Optional


# ── Perplexity Boosting: AI word -> list of human alternatives ────────────────
# Key: high-probability AI token (regex pattern)
# Value: list of lower-probability human alternatives (picked randomly)
#
# Design rationale:
#   - AI always picks "demonstrates" → human says "shows" or "makes clear"
#   - AI always picks "significant" → human says "real" or "notable"
#   - We also inject rare-but-natural academic vocab (viz., qua, sensu stricto)
#     that human researchers genuinely use but LLMs rarely produce as top-1 token

PERPLEXITY_SWAPS: list[tuple[str, list[str]]] = [
    # Over-formal verbs → plain active verbs
    (r"\bdemonstrates\b", ["shows", "makes clear", "confirms", "reveals"]),
    (r"\bdemonstrate\b", ["show", "make clear", "confirm", "reveal"]),
    (r"\bdemonstrated\b", ["showed", "confirmed", "revealed", "made clear"]),
    (r"\butilizes\b", ["uses", "relies on", "applies"]),
    (r"\butilize\b", ["use", "rely on", "apply"]),
    (r"\butilized\b", ["used", "applied", "relied on"]),
    (r"\butilization\b", ["use", "application", "deployment"]),
    (r"\bfacilitates\b", ["helps", "aids in", "supports"]),
    (r"\bfacilitate\b", ["help", "aid in", "support"]),
    (r"\bfacilitated\b", ["helped", "aided in", "enabled"]),
    (r"\benables\b", ["lets", "allows", "makes it possible"]),
    (r"\benable\b", ["let", "allow", "make it possible"]),
    (r"\benabled\b", ["let", "allowed", "made it possible"]),
    (r"\benhances\b", ["improves", "boosts", "strengthens"]),
    (r"\benhance\b", ["improve", "boost", "strengthen"]),
    (r"\benhanced\b", ["improved", "boosted", "strengthened"]),
    (r"\bachieve\b", ["reach", "attain", "secure", "obtain"]),
    (r"\bachieves\b", ["reaches", "attains", "secures"]),
    (r"\bachieved\b", ["reached", "attained", "secured", "obtained"]),
    (r"\bimplements\b", ["uses", "applies", "runs"]),
    (r"\bimplement\b", ["use", "apply", "run", "deploy"]),
    (r"\bimplemented\b", ["used", "applied", "ran", "deployed"]),
    (r"\bexhibits\b", ["shows", "displays", "has"]),
    (r"\bexhibit\b", ["show", "display", "have"]),
    (r"\bexhibited\b", ["showed", "displayed", "had"]),

    # AI inflation words → academic-appropriate alternatives
    (r"\bsignificantly\b", ["notably", "meaningfully", "considerably", "appreciably", "markedly"]),
    (r"\bsignificant\b", ["notable", "meaningful", "considerable", "marked", "appreciable"]),
    (r"\bsubstantially\b", ["largely", "considerably", "appreciably", "markedly"]),
    (r"\bsubstantial\b", ["considerable", "appreciable", "marked", "sizable"]),
    (r"\boptimal\b", ["best", "ideal", "most effective"]),
    (r"\boptimize\b", ["improve", "tune", "refine", "fine-tune"]),
    (r"\boptimized\b", ["improved", "tuned", "refined"]),
    (r"\bnovel\b", ["new", "fresh", "different", "original"]),
    (r"\brobust\b", ["strong", "reliable", "solid", "stable"]),
    (r"\bcomprehensive\b", ["thorough", "detailed", "full", "wide-ranging"]),
    (r"\bsophisticated\b", ["advanced", "complex", "refined", "detailed"]),
    (r"\befficiently\b", ["fast", "quickly"]),
    (r"\befficient\b", ["fast", "streamlined", "quick"]),
    (r"\baccurately\b", ["correctly", "precisely", "exactly"]),
    (r"\baccurate\b", ["correct", "precise", "right", "exact"]),
    (r"\bprecisely\b", ["exactly", "accurately"]),
    (r"\bprecise\b", ["exact", "accurate", "fine-grained"]),
    (r"\beffectively\b", ["usefully", "practically", "successfully"]),
    (r"\beffective\b", ["useful", "practical", "successful", "capable"]),
    (r"\bextensively\b", ["widely", "broadly", "thoroughly"]),
    (r"\bextensive\b", ["wide", "broad", "large-scale", "thorough"]),
    (r"\bspecific\b", ["particular", "exact", "defined"]),
    (r"\bprimary\b", ["main", "key", "central", "top"]),
    (r"\binitially\b", ["first", "early", "at first", "to start"]),
    (r"\binitial\b", ["first", "early", "starting"]),
    (r"\bsubsequently\b", ["later", "next", "after that", "then"]),
    (r"\bsubsequent\b", ["later", "next", "following"]),
    (r"\bprior to\b", ["before", "ahead of"]),
    (r"\bin order to\b", ["to", "so as to"]),
    (r"\bwith respect to\b", ["for", "regarding", "on", "about"]),
    (r"\bin terms of\b", ["for", "in", "regarding", "on"]),
    (r"\bin the context of\b", ["in", "within", "for"]),
    (r"\bregarding\b", ["about", "on", "for", "concerning"]),
    (r"\bwith regard to\b", ["about", "on", "for"]),
    (r"\bpertaining to\b", ["about", "for", "related to"]),

    # High-register academic → human phrasing
    (r"\bnevertheless\b", ["still", "even so", "but", "yet"]),
    (r"\bnonetheless\b", ["still", "even so", "that said", "yet"]),
    (r"\bhenceforth\b", ["from here on", "going forward", "after this"]),
    (r"\bhereinafter\b", ["from here", "below", "after this"]),
    (r"\bthus\b", ["so", "this means", "as a result"]),
    (r"\bhence\b", ["so", "therefore", "that's why"]),
    (r"\bthereby\b", ["so", "thus", "which means"]),
    (r"\bwhereby\b", ["where", "through which", "by which"]),
    (r"\bproposed\b", ["put forward", "introduced", "laid out", "described"]),
    (r"\bpresented\b", ["showed", "laid out", "described", "offered"]),
    (r"\bindicated\b", ["showed", "pointed to", "suggested", "found"]),
    (r"\bobserved\b", ["saw", "found", "noted", "noticed"]),
    (r"\bidentified\b", ["found", "spotted", "picked out", "detected"]),
    (r"\bexamined\b", ["looked at", "studied", "reviewed", "checked"]),
    (r"\binvestigated\b", ["studied", "looked into", "explored", "checked"]),

    # Connector phrases AI overuses
    (r"\bin addition\b", ["also", "on top of that", "plus", "and"]),
    (r"\bfurthermore\b", ["also", "and", "on top of that", "what's more"]),
    (r"\bmoreover\b", ["also", "plus", "on top of that", "and"]),
    (r"\bin conclusion\b", ["overall", "in the end", "to wrap up", "finally"]),
    (r"\bin summary\b", ["to sum up", "in short", "overall", "briefly"]),
    (r"\bto summarize\b", ["in short", "to sum up", "briefly"]),
    (r"\bit should be noted\b", ["note that", "worth noting", "importantly"]),
    (r"\bit is worth noting\b", ["worth noting", "notably", "and"]),
    (r"\bnotably\b", ["interestingly", "importantly", "in particular"]),
    (r"\bas a result\b", ["so", "this means", "which led to", "because of this"]),
    (r"\bconsequently\b", ["so", "as a result", "this means", "which led to"]),

    # Additional Turnitin-flagged vocabulary
    (r"\belucidate\b", ["clarify", "explain", "spell out", "shed light on"]),
    (r"\belucidates\b", ["clarifies", "explains", "sheds light on"]),
    (r"\belucidated\b", ["clarified", "explained", "shed light on"]),
    (r"\bmultifaceted\b", ["complex", "many-sided", "varied", "layered"]),
    (r"\bparadigm\b", ["framework", "model", "approach", "template"]),
    (r"\bmeticulous\b", ["careful", "thorough", "detailed", "painstaking"]),
    (r"\bmeticulously\b", ["carefully", "thoroughly", "painstakingly"]),
    (r"\bintricate\b", ["complex", "detailed", "involved", "nuanced"]),
    (r"\bintricacies\b", ["complexities", "details", "nuances"]),
    (r"\bpivotal\b", ["central", "key", "decisive", "critical"]),
    (r"\bcrucial\b", ["important", "key", "central", "essential"]),
    (r"\bfostering\b", ["encouraging", "supporting", "promoting"]),
    (r"\bfosters\b", ["encourages", "supports", "promotes"]),
    (r"\bfoster\b", ["encourage", "support", "promote"]),
    (r"\bunderscores\b", ["highlights", "points to", "reinforces"]),
    (r"\bunderscore\b", ["highlight", "point to", "reinforce"]),
    (r"\bunderscored\b", ["highlighted", "pointed to", "reinforced"]),
    (r"\bshowcases\b", ["illustrates", "presents", "displays"]),
    (r"\bshowcase\b", ["illustrate", "present", "display"]),
    (r"\bshowcased\b", ["illustrated", "presented", "displayed"]),
    (r"\bgarner\b", ["earn", "attract", "win", "draw"]),
    (r"\bgarners\b", ["earns", "attracts", "wins", "draws"]),
    (r"\bgarnered\b", ["earned", "attracted", "won", "drew"]),
    (r"\bdelves\b", ["examines", "explores", "digs into"]),
    (r"\bdelve\b", ["examine", "explore", "dig into"]),
    (r"\bdelved\b", ["examined", "explored", "dug into"]),
    (r"\btransformative\b", ["far-reaching", "sweeping", "major"]),
    (r"\bgroundbreaking\b", ["pioneering", "original", "first-of-its-kind"]),
    (r"\bunprecedented\b", ["rare", "unusual", "extraordinary", "first-of-its-kind"]),
    (r"\bseamless\b", ["smooth", "fluid", "uninterrupted"]),
    (r"\bholistic\b", ["comprehensive", "integrated", "whole-system"]),
    (r"\bcornerstone\b", ["foundation", "basis", "anchor"]),
    (r"\btapestry\b", ["mix", "blend", "combination", "mosaic"]),
    (r"\bbeacon\b", ["signal", "example", "marker"]),
    (r"\blandscape\b", ["field", "area", "space", "domain"]),
    (r"\brealm\b", ["area", "domain", "field", "sphere"]),
    (r"\binterplay\b", ["interaction", "relationship", "interrelation", "dynamic"]),
    (r"\bvibrant\b", ["active", "dynamic", "lively", "thriving"]),
    (r"\bparamount\b", ["primary", "chief", "top", "foremost"]),
    (r"\btestament\b", ["proof", "evidence", "sign", "indicator"]),
]

# Academic low-frequency vocabulary injections
# Words real researchers use but LLMs rarely produce as top-1 tokens
ACADEMIC_RARE_INJECTIONS: list[tuple[str, str]] = [
    ("that is to say", "viz."),
    ("in itself", "per se"),
    ("among other things", "inter alia"),
    ("in this regard", "on this score"),
    ("it must be said", "to be candid"),
    ("it turns out that", "as it happens"),
    ("by the same token", "by parity of reasoning"),
    ("on the whole", "on balance"),
    ("in broad terms", "broadly construed"),
    ("strictly speaking", "sensu stricto"),
]

# Compile all patterns once
_COMPILED_SWAPS = [
    (re.compile(pat, re.IGNORECASE), replacements)
    for pat, replacements in PERPLEXITY_SWAPS
]


# ── Lexical Diversity: Academic domain synonym groups ─────────────────────────
# When a word is used more than OVERUSE_THRESHOLD times per paragraph,
# rotate through these synonym groups.

OVERUSE_THRESHOLD = 2  # flag after N occurrences per paragraph

SYNONYM_GROUPS: list[list[str]] = [
    # Accuracy / performance metrics
    ["accuracy", "precision", "correctness", "quality"],
    ["results", "findings", "outcomes", "outputs", "data"],
    ["performance", "efficiency", "speed", "throughput"],
    ["model", "system", "framework"],
    ["approach", "method", "technique", "strategy"],
    ["dataset", "training set", "corpus", "collection"],
    ["training", "learning", "optimization", "fitting"],
    ["evaluation", "assessment", "testing", "measurement", "validation"],
    ["experiment", "test", "trial", "study"],
    ["baseline", "reference", "benchmark", "standard", "comparison"],
    ["improvement", "gain", "boost", "increase", "enhancement"],
    ["reduction", "decrease", "drop", "fall", "decline"],
    ["comparison", "contrast", "difference", "gap", "distinction"],
    ["feature", "property", "attribute", "characteristic", "aspect"],
    ["task", "problem", "challenge", "objective", "goal"],
    ["network", "architecture", "structure"],
    ["layer", "module", "component", "block", "unit"],
    ["algorithm", "procedure", "process"],
    ["classification", "detection", "prediction", "identification"],
    ["generalization", "transfer", "adaptation", "robustness"],
    ["error", "loss", "mistake", "discrepancy", "deviation"],
    ["analysis", "study", "examination", "investigation", "review"],
    ["paper", "study", "work", "research", "article"],
]

# Build reverse lookup: word -> group index
_WORD_TO_GROUP: dict[str, int] = {}
for _gidx, _group in enumerate(SYNONYM_GROUPS):
    for _word in _group:
        _WORD_TO_GROUP[_word.lower()] = _gidx


def _inject_academic_rare(text: str, probability: float = 0.06) -> str:
    """
    Injects low-frequency academic vocabulary that real researchers use
    but LLMs almost never produce as their top-1 token choice. This raises
    the perplexity score specifically on Turnitin's token prediction model.
    """
    result = text
    for common_phrase, rare_phrase in ACADEMIC_RARE_INJECTIONS:
        if common_phrase in result.lower() and random.random() < probability:
            pattern = re.compile(re.escape(common_phrase), re.IGNORECASE)
            result = pattern.sub(rare_phrase, result, count=1)
    return result


def boost_perplexity(text: str, swap_probability: float = 0.45) -> str:
    """
    Replaces high-probability AI word choices with lower-probability
    human alternatives to raise perplexity score on AI detectors.
    Also injects rare academic vocabulary for Turnitin evasion.
    """
    if not text or not text.strip():
        return text

    result = text
    for pattern, replacements in _COMPILED_SWAPS:
        def _replacer(m: re.Match) -> str:
            if random.random() > swap_probability:
                return m.group(0)
            chosen = random.choice(replacements)
            original = m.group(0)
            if original[0].isupper():
                return chosen[0].upper() + chosen[1:]
            return chosen

        result = pattern.sub(_replacer, result)

    # Inject rare academic vocabulary
    result = _inject_academic_rare(result, probability=0.06)

    return result


def enforce_lexical_diversity(text: str) -> str:
    """
    Tracks word frequency per paragraph and rotates synonyms when a word
    is overused (more than OVERUSE_THRESHOLD times per paragraph).

    Raises the Type-Token Ratio (TTR), a metric measured by Originality.ai.

    Args:
        text: Input text (may contain multiple paragraphs separated by blank lines).

    Returns:
        Text with synonym rotation applied to overused academic terms.
    """
    if not text or not text.strip():
        return text

    paragraphs = text.split("\n\n")
    result_paragraphs = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            result_paragraphs.append(para)
            continue

        result_paragraphs.append(_diversify_paragraph(stripped))

    return "\n\n".join(result_paragraphs)


def _diversify_paragraph(para: str) -> str:
    """Apply synonym rotation within a single paragraph."""
    # Count word frequencies (case-insensitive)
    words_lower = re.findall(r"\b[a-zA-Z]+\b", para.lower())
    freq: dict[str, int] = {}
    for w in words_lower:
        freq[w] = freq.get(w, 0) + 1

    # Find words that are overused AND have a synonym group
    overused = {
        w for w, count in freq.items()
        if count > OVERUSE_THRESHOLD and w in _WORD_TO_GROUP
    }

    if not overused:
        return para

    result = para
    for word in overused:
        group_idx = _WORD_TO_GROUP[word]
        synonyms = [s for s in SYNONYM_GROUPS[group_idx] if s.lower() != word.lower()]
        if not synonyms:
            continue

        # Replace all but the first occurrence with alternating synonyms
        occurrences = list(re.finditer(rf"\b{re.escape(word)}\b", result, re.IGNORECASE))
        if len(occurrences) <= 1:
            continue

        # Keep first occurrence, replace the rest (rotating through synonyms)
        syn_idx = 0
        # Walk backwards to preserve offsets
        for occ in reversed(occurrences[1:]):
            replacement = synonyms[syn_idx % len(synonyms)]
            original = occ.group(0)
            # Preserve capitalisation
            if original[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            result = result[:occ.start()] + replacement + result[occ.end():]
            syn_idx += 1

    return result


def apply_all(text: str, swap_probability: float = 0.6) -> str:
    """
    Convenience function: runs both perplexity boosting AND lexical diversity
    enforcement in sequence.

    Args:
        text: Input text.
        swap_probability: How aggressively to swap AI words (default 0.6 = 60%).

    Returns:
        Processed text with raised perplexity and improved TTR.
    """
    text = boost_perplexity(text, swap_probability=swap_probability)
    text = enforce_lexical_diversity(text)
    return text
