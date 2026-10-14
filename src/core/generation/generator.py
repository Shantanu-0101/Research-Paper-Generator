import re
import os
import hashlib
import json
from pathlib import Path
from src.core.generation.prompts import build_generation_prompt
from src.core.style.style_analyzer import StyleProfile
from src.core.llm.llm_factory import get_llm
from src.core.generation.evaluator import evaluate_section
from src.core.retrieval.web_search import search_topic_content
from src.core.illustration.image_search import get_academic_illustration
from src.core.humanizer.burstiness import measure_burstiness, _split_into_sentences
from src.core.humanizer.reranker import score_candidate
from src.core.humanizer.sentence_restructurer import measure_sentence_initial_variety

DEFAULT_SECTIONS = ["Abstract", "Introduction", "Literature Review", "Methodology", "Results", "Conclusion", "References"]

# Per-topic image cache to reuse images for the same topic across generations
IMAGE_CACHE_DIR = Path("data/image_cache")
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_topic_cache_key(topic: str, keywords: str = "") -> str:
    """Generate a stable cache key from topic + keywords combined."""
    combined = f"{topic.lower().strip()}|{keywords.lower().strip()}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def _load_topic_image_cache(topic: str, keywords: str = "") -> dict:
    """Load previously used images for this topic+keywords pair."""
    cache_file = IMAGE_CACHE_DIR / f"{_get_topic_cache_key(topic, keywords)}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def _save_topic_image_cache(topic: str, keywords: str = "", cache: dict = None):
    """Save used images for this topic+keywords pair for future reuse."""
    if cache is None:
        return
    cache_file = IMAGE_CACHE_DIR / f"{_get_topic_cache_key(topic, keywords)}.json"
    try:
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2)
    except:
        pass


_SECTION_SEARCH_MODIFIERS = {
    "introduction": "overview concept diagram",
    "literature review": "survey comparison taxonomy",
    "methodology": "framework architecture pipeline",
    "results": "results analysis performance chart",
    "conclusion": "summary implications future directions",
}


def _build_image_query(topic: str, section: str, keywords: str = "", caption_hint: str = "") -> str:
    """Build a specific, relevant image search query using topic + keywords + section context."""
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()][:3]
    kw_part = " ".join(kw_list)
    modifier = _SECTION_SEARCH_MODIFIERS.get(section.lower(), "")

    if caption_hint and len(caption_hint) > 10:
        return f"{caption_hint} {kw_part}".strip()

    parts = [topic]
    if kw_part:
        parts.append(kw_part)
    if modifier:
        parts.append(modifier)
    return " ".join(parts)


def _generate_fallback_section(topic: str, section: str, web_results: list[dict]) -> str:
    """
    Guaranteed fallback: builds a section from web search snippets when the LLM
    fails completely. Never returns empty text.
    """
    parts = [f"This section addresses {section.lower()} aspects of the research on {topic}."]

    if web_results:
        for r in web_results[:3]:
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            if content:
                parts.append(f"According to {title}, {content}")

    parts.append(f"Further research and detailed analysis are recommended for a comprehensive understanding of {section.lower()} in the context of {topic}.")

    return "\n\n".join(parts)


def _process_visual_placeholders(text: str, topic: str, section: str, keywords: str = "", topic_image_cache: dict = None, used_image_paths: set = None) -> tuple[str, list[dict]]:
    """
    Image processor with relevance-first search and deduplication:
    - Builds specific queries from topic + keywords + section context
    - Reuses cached images ONLY for identical topic+keywords (cache key includes both)
    - Prevents duplicate images across sections via used_image_paths
    - Falls back gracefully
    """
    if topic_image_cache is None:
        topic_image_cache = {}
    if used_image_paths is None:
        used_image_paths = set()

    pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    image_sources = []
    section_key = section.lower()

    def replace_match(match):
        caption = match.group(1)
        spec = match.group(2)

        # Check cache — but only reuse if not already used by another section in this run
        if section_key in topic_image_cache:
            cached_path = topic_image_cache[section_key]
            if os.path.exists(cached_path) and cached_path not in used_image_paths:
                used_image_paths.add(cached_path)
                image_sources.append({
                    "title": "Reused Image from Previous Generation",
                    "url": "#"
                })
                return f"![{caption}]({cached_path})"

        # Extract the LLM's caption hint for a targeted search query
        caption_hint = ""
        if "image_query:" in spec:
            caption_hint = spec.replace("image_query:", "").strip(' "\'')
        elif spec.strip():
            caption_hint = spec.strip(' "\'')

        query = _build_image_query(topic, section, keywords, caption_hint)
        img_data = get_academic_illustration(query, used_paths=used_image_paths)
        if img_data and os.path.exists(img_data["local_path"]):
            topic_image_cache[section_key] = img_data["local_path"]
            used_image_paths.add(img_data["local_path"])
            image_sources.append({
                "title": f"Image Source: {img_data.get('source_name', 'Web Search')}",
                "url": img_data.get("source_url", "#")
            })
            return f"![{caption}]({img_data['local_path']})"
        return ""

    processed_text = pattern.sub(replace_match, text)

    # Force at least one image per major section if none was inserted
    if section.lower() not in ["references", "abstract"] and not any("![" in line for line in processed_text.split('\n') if line.strip()):
        auto_caption = f"{section} — {topic}"
        img_path = None
        img_source_entry = None

        # Check cache — but skip if this image is already used in another section
        if section_key in topic_image_cache and os.path.exists(topic_image_cache[section_key]) and topic_image_cache[section_key] not in used_image_paths:
            img_path = topic_image_cache[section_key]
            used_image_paths.add(img_path)
            img_source_entry = {
                "title": "Topic Cached Academic Illustration",
                "url": "#"
            }
        else:
            fallback_query = _build_image_query(topic, section, keywords)
            img_data = get_academic_illustration(fallback_query, used_paths=used_image_paths)
            if img_data and os.path.exists(img_data["local_path"]):
                img_path = img_data["local_path"]
                topic_image_cache[section_key] = img_path
                used_image_paths.add(img_path)
                img_source_entry = {
                    "title": f"Image Source: {img_data.get('source_name', 'Web Search')}",
                    "url": img_data.get("source_url", "#")
                }

        if img_path:
            tag = f"![{auto_caption}]({img_path})"
            paragraphs = [p.strip() for p in processed_text.split("\n\n") if p.strip()]
            if len(paragraphs) >= 3:
                paragraphs.insert(2, tag)
            else:
                paragraphs.append(tag)
            processed_text = "\n\n".join(paragraphs)
            if img_source_entry:
                image_sources.append(img_source_entry)

    return processed_text, image_sources


def generate_section(
    topic: str,
    section: str,
    style_profile: StyleProfile,
    web_results: list[dict] = None,
    keywords: str = "",
    extra_instructions: str = "",
    previous_sections_summary: str = "",
    include_visuals: bool = True,
    topic_image_cache: dict = None,
    used_image_paths: set = None,
) -> dict:
    if web_results is None:
        web_results = search_topic_content(topic, "", section)

    prompt = build_generation_prompt(
        topic=topic,
        section=section,
        web_results=web_results,
        style_notes=style_profile.to_prompt_text(),
        style_profile=style_profile,
        keywords=keywords,
        extra_instructions=extra_instructions,
        previous_sections_summary=previous_sections_summary,
        include_visuals=include_visuals,
    )

    llm = get_llm()
    generated_text = ""
    for retry in range(3):
        try:
            response = llm.invoke(prompt)
            text = response.content if response.content else ""
            if text and len(text.strip()) > 80:
                generated_text = text
                break
            print(f"Section '{section}' returned empty/short text, retry {retry + 1}/3")
        except Exception as e:
            print(f"Section '{section}' generation error: {e}, retry {retry + 1} of 3")

    # Strong fallback: if all retries failed, generate a minimal section
    if not generated_text or len(generated_text.strip()) < 80:
        generated_text = _generate_fallback_section(topic, section, web_results)

    sources_used = [{"title": r["title"], "url": r["url"]} for r in web_results]

    if include_visuals and section.lower() != "references":
        generated_text, img_sources = _process_visual_placeholders(
            generated_text, topic, section, keywords=keywords,
            topic_image_cache=topic_image_cache, used_image_paths=used_image_paths,
        )
        sources_used.extend(img_sources)

    return {"text": generated_text, "sources": sources_used}


def generate_reviewed_section(
    topic: str,
    section: str,
    style_profile: StyleProfile,
    web_results: list[dict] = None,
    keywords: str = "",
    extra_instructions: str = "",
    previous_sections_summary: str = "",
    max_attempts: int = 3,
    include_visuals: bool = True,
    topic_image_cache: dict = None,
    used_image_paths: set = None,
) -> dict:
    result = generate_section(
        topic=topic,
        section=section,
        style_profile=style_profile,
        web_results=web_results,
        keywords=keywords,
        extra_instructions=extra_instructions,
        previous_sections_summary=previous_sections_summary,
        include_visuals=include_visuals,
        topic_image_cache=topic_image_cache,
        used_image_paths=used_image_paths,
    )

    attempt = 1
    evaluation = evaluate_section(result["text"], result["sources"], style_profile, previous_sections_summary, section_name=section)

    while not evaluation.passed and attempt < max_attempts:
        result["text"] = _rewrite_section(
            topic=topic,
            section=section,
            original_text=result["text"],
            issues=evaluation.issues,
            style_profile=style_profile,
        )
        attempt += 1
        evaluation = evaluate_section(result["text"], result["sources"], style_profile, previous_sections_summary, section_name=section)

    return {
        "text": result["text"],
        "sources": result["sources"],
        "attempts": attempt,
        "passed": evaluation.passed,
        "remaining_issues": evaluation.issues,
    }


def check_post_humanization_quality(text: str) -> dict:
    """
    Lightweight quality check that runs after humanization.
    Returns metrics and warnings for the UI to display.
    """
    # Strip image tags for analysis
    clean = re.compile(r"!\[(.*?)\]\((.*?)\)").sub("", text).strip()
    if not clean:
        return {"warnings": [], "metrics": {}}

    score = score_candidate(clean)
    variety = measure_sentence_initial_variety(clean)

    warnings = []
    if score["burstiness_cv"] < 0.45:
        warnings.append(f"Burstiness CV is low ({score['burstiness_cv']:.2f}) — text may still have uniform sentence lengths")
    if score["residual_tells"] > 0:
        warnings.append(f"{score['residual_tells']} AI-tell word(s) remain: {', '.join(str(t) for t in score['found_tells'][:5])}")
    if variety < 0.35:
        warnings.append(f"Sentence-initial variety is low ({variety:.2f}) — too many sentences start with articles/pronouns")

    return {
        "warnings": warnings,
        "metrics": {
            "burstiness_cv": round(score["burstiness_cv"], 3),
            "residual_tells": score["residual_tells"],
            "composite_score": round(score["composite_score"], 1),
            "sentence_initial_variety": round(variety, 3),
        },
    }


def _rewrite_section(topic: str, section: str, original_text: str, issues: list[str], style_profile) -> str:
    """
    Takes the section text plus the Evaluator's specific complaints and
    asks the LLM to fix exactly those issues — not regenerate from scratch.
    Preserves all image placeholders from being lost during rewrite.
    """
    from src.core.generation.prompts import build_rewrite_prompt

    # Extract existing image tags
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    images = image_pattern.findall(original_text)
    clean_text = image_pattern.sub("", original_text).strip()

    prompt = build_rewrite_prompt(
        topic=topic,
        section=section,
        original_text=clean_text,
        issues=issues,
        style_notes=style_profile.to_prompt_text(),
    )
    llm = get_llm()
    response = llm.invoke(prompt)
    rewritten_text = response.content if (response and response.content) else clean_text

    # Re-inject preserved images into rewritten text
    if images:
        paragraphs = [p.strip() for p in rewritten_text.split("\n\n") if p.strip()]
        for caption, path_or_spec in images:
            tag = f"![{caption}]({path_or_spec})"
            if len(paragraphs) >= 3:
                paragraphs.insert(2, tag)
            else:
                paragraphs.append(tag)
        rewritten_text = "\n\n".join(paragraphs)

    return rewritten_text


def _summarize_for_context(section_name: str, text: str, max_words: int = 60) -> str:
    words = text.split()
    snippet = " ".join(words[:max_words])
    return f"- {section_name}: {snippet}{'...' if len(words) > max_words else ''}"


def generate_full_paper(topic, style_profile, sections=None, keywords="", extra_instructions="", max_attempts: int = 3, include_visuals: bool = True):
    sections = sections or DEFAULT_SECTIONS
    running_summary_parts = []
    used_urls = set()
    used_image_paths = set()
    all_sources: list[dict] = []  # Collect {title, url} dicts across all sections
    topic_image_cache = _load_topic_image_cache(topic, keywords)  # Reuse images only for same topic+keywords

    for section in sections:
        if section.lower() == "references":
            # Build proper APA-style references from all sources collected so far
            ref_text = "References\n\n"
            # Deduplicate by URL
            seen_urls = set()
            unique_sources = []
            for src in all_sources:
                url = src.get("url", "")
                if url and url != "#" and url not in seen_urls:
                    seen_urls.add(url)
                    unique_sources.append(src)

            if not unique_sources:
                ref_text += "No external web sources were cited in this paper."
            else:
                for i, src in enumerate(unique_sources, 1):
                    title = src.get("title", "Unknown Source")
                    url = src.get("url", "")
                    # APA-style: Author/Source. (n.d.). Title. Retrieved from URL
                    ref_text += f"{i}. {title}. Retrieved from {url}\n\n"

            result = {
                "text": ref_text,
                "sources": [],
                "attempts": 1,
                "passed": True,
                "remaining_issues": []
            }
            yield section, result
            continue

        web_results = search_topic_content(topic, "", section)
        fresh_results = [r for r in web_results if r["url"] not in used_urls]
        for r in fresh_results:
            used_urls.add(r["url"])
            # Collect for references: only real web sources (not image sources with url="#")
            if r.get("url") and r["url"] != "#":
                all_sources.append({"title": r.get("title", ""), "url": r["url"]})

        result = generate_reviewed_section(
            topic=topic,
            section=section,
            style_profile=style_profile,
            web_results=fresh_results,
            keywords=keywords,
            extra_instructions=extra_instructions,
            previous_sections_summary="\n".join(running_summary_parts),
            max_attempts=max_attempts,
            include_visuals=include_visuals,
            topic_image_cache=topic_image_cache,
            used_image_paths=used_image_paths,
        )
        running_summary_parts.append(_summarize_for_context(section, result["text"]))
        yield section, result

    _save_topic_image_cache(topic, keywords, topic_image_cache)
