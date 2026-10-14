"""
Research Style Writer — AI Research Paper Generator

User uploads 3-8 reference PDFs for style analysis, enters a topic + keywords,
and the system generates academic paper sections grounded in web search.
Includes optional humanizer post-processing to remove AI writing patterns.
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from src.core.config import settings
from src.core.ingestion.pdf_loader import extract_text_from_uploads
from src.core.ingestion.chunker import chunk_pages
from src.core.style.style_analyzer import analyze_style
from src.core.generation.generator import generate_full_paper, generate_reviewed_section
from src.core.export.pdf_export import generate_pdf
from src.core.export.docx_export import generate_docx
from src.core.humanizer.humanizer import humanize_section
from src.core.generation.generator import check_post_humanization_quality


def render_section_content(text: str):
    """
    Renders text and embedded markdown images cleanly in Streamlit UI.
    """
    image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    lines = text.split("\n")

    for line in lines:
        match = image_pattern.search(line)
        if match:
            caption = match.group(1)
            img_path = match.group(2).strip()
            if os.path.exists(img_path):
                st.image(img_path, caption=caption, use_container_width=True)
            else:
                st.warning(f"Image not found: {img_path}")
        else:
            st.markdown(line)


def main():
    st.set_page_config(page_title="Research Style Writer", layout="wide")
    st.title("Research Style Writer")
    st.caption("Upload reference papers, enter a topic, generate academic sections")

    try:
        settings.validate()
    except ValueError as e:
        st.error(f"Configuration error: {e}")
        st.stop()

    # Session state
    if "style_profile" not in st.session_state:
        st.session_state.style_profile = None
    if "generated_sections" not in st.session_state:
        st.session_state.generated_sections = []

    # ── Sidebar: Options ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Options")
        use_humanizer = st.toggle(
            "Humanize output",
            value=True,
            help="Multi-pass pipeline: structural variation + LLM rewrite + lexical processing. Reduces AI detection score."
        )
        humanizer_strength = 2  # default
        if use_humanizer:
            humanizer_strength = st.select_slider(
                "Humanization Strength",
                options=[1, 2, 3],
                value=2,
                format_func=lambda x: {1: "Standard (1 pass)", 2: "Deep (2 passes)", 3: "Maximum (3 passes)"}[x],
                help="Higher = more LLM rewrite iterations. Deep is recommended for Turnitin. Maximum for highest-stakes submissions."
            )
            st.info(f"Pipeline: Structural variation + {humanizer_strength}x LLM rewrite + Lexical processing + Quality gate")

    # ── Step 1: Upload & process papers ───────────────────────────────────────
    st.header("1. Upload reference papers")
    uploaded_files = st.file_uploader(
        "Upload 3-8 research papers (PDF)",
        type="pdf",
        accept_multiple_files=True,
    )

    if uploaded_files:
        if not (settings.min_files <= len(uploaded_files) <= settings.max_files):
            st.warning(
                f"Please upload between {settings.min_files} and {settings.max_files} PDFs "
                f"(currently {len(uploaded_files)})."
            )
        elif st.button("Process papers"):
            with st.spinner("Extracting text..."):
                pages, skipped = extract_text_from_uploads(uploaded_files)
                if skipped:
                    st.warning(f"Couldn't read: {', '.join(skipped)}")

            if not pages:
                st.error("No text could be extracted from any uploaded file.")
            else:
                with st.spinner("Analyzing style..."):
                    chunks = chunk_pages(pages)
                    style_profile = analyze_style(chunks)
                    st.session_state.style_profile = style_profile

                st.success(f"Processed {len(uploaded_files) - len(skipped)} papers, analyzed writing style.")

    # ── Step 2: Generate a section ───────────────────────────────────────────
    st.header("2. Generate a section")

    if "style_profile" not in st.session_state or st.session_state.style_profile is None:
        st.info("Upload and process papers above before generating.")
    else:
        topic = st.text_input("Paper topic / title")
        keywords = st.text_area(
            "Keywords (comma-separated)",
            placeholder="e.g., Knowledge Graph, Meta-path, Large Language Models, Explainable Recommendation",
            help="These keywords will be woven naturally into the generated text as thematic anchors."
        )
        section = st.selectbox(
            "Section to generate",
            ["Abstract", "Introduction", "Literature Review", "Methodology", "Results", "Conclusion", "References"],
        )
        extra_instructions = st.text_area("Additional instructions (optional)")
        include_visuals = st.checkbox("Generate & Include Real Academic Images & Photos", value=True)

        if st.button("Generate", disabled=not topic):
            with st.spinner("Generating section & searching for real topic images..."):
                try:
                    result = generate_reviewed_section(
                        topic=topic,
                        section=section,
                        style_profile=st.session_state.style_profile,
                        keywords=keywords,
                        extra_instructions=extra_instructions,
                        include_visuals=include_visuals,
                    )

                    # Humanizer post-processing (skip for References)
                    if use_humanizer and section.lower() != "references":
                        with st.spinner(f"Humanizing output ({humanizer_strength} pass{'es' if humanizer_strength > 1 else ''})..."):
                            result = humanize_section(
                                result,
                                style_notes=st.session_state.style_profile.to_prompt_text(),
                                max_passes=humanizer_strength,
                            )

                    st.subheader(f"Generated {section}")
                    render_section_content(result["text"])

                    if result["passed"]:
                        st.caption(f"✅ Passed review after {result['attempts']} attempt(s)")
                    else:
                        st.caption(f"⚠️ {result['attempts']} attempts made, unresolved issues:")
                        for issue in result["remaining_issues"]:
                            st.caption(f"- {issue}")

                    # Show humanization metrics
                    if use_humanizer and "humanization_metrics" in result:
                        metrics = result["humanization_metrics"]
                        with st.expander("Humanization Metrics"):
                            mc1, mc2, mc3, mc4 = st.columns(4)
                            mc1.metric("Burstiness CV", f"{metrics.get('burstiness_cv', 0):.3f}", help="Target: >= 0.45")
                            mc2.metric("AI Tells", metrics.get("residual_tells", 0), help="Target: 0")
                            mc3.metric("Variety", f"{metrics.get('sentence_initial_variety', 0):.3f}", help="Target: >= 0.35")
                            mc4.metric("Composite", f"{metrics.get('composite_score', 0):.0f}", help="Target: >= 80")

                        # Post-humanization quality warnings
                        quality = check_post_humanization_quality(result["text"])
                        for warning in quality.get("warnings", []):
                            st.warning(warning)

                    with st.expander("Sources used"):
                        for src in result["sources"]:
                            st.write(f"- [{src['title']}]({src['url']})")

                    st.download_button(
                        "📄 Download as text",
                        result["text"],
                        file_name=f"{section.lower().replace(' ', '_')}.txt",
                    )

                except Exception as e:
                    st.error(f"Generation failed: {e}")

        if st.button("Generate All Sections"):
            st.session_state.generated_sections = []
            with st.spinner("Generating full paper with figures..."):
                for section_name, result in generate_full_paper(
                    topic,
                    style_profile=st.session_state.style_profile,
                    keywords=keywords,
                    extra_instructions=extra_instructions,
                    include_visuals=include_visuals
                ):
                    # Humanizer post-processing (skip for References)
                    if use_humanizer and section_name.lower() != "references":
                        with st.spinner(f"Humanizing {section_name} ({humanizer_strength} pass{'es' if humanizer_strength > 1 else ''})..."):
                            result = humanize_section(
                                result,
                                style_notes=st.session_state.style_profile.to_prompt_text(),
                                max_passes=humanizer_strength,
                            )

                    st.subheader(section_name)
                    render_section_content(result["text"])

                    with st.expander(f"Sources used ({section_name})"):
                        for src in result["sources"]:
                            st.write(f"- [{src['title']}]({src['url']})")

                    st.session_state.generated_sections.append((section_name, result["text"]))

                    # Humanization metrics per section
                    if use_humanizer and "humanization_metrics" in result:
                        metrics = result["humanization_metrics"]
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.caption(f"CV: {metrics.get('burstiness_cv', 0):.3f}")
                        mc2.caption(f"Tells: {metrics.get('residual_tells', 0)}")
                        mc3.caption(f"Variety: {metrics.get('sentence_initial_variety', 0):.3f}")

                    if result["passed"]:
                        st.caption(f"✅ Passed review after {result['attempts']} attempt(s)")
                    else:
                        st.caption(f"⚠️ {result['attempts']} attempts, unresolved issues:")
                        for issue in result["remaining_issues"]:
                            st.caption(f"- {issue}")


        if st.session_state.generated_sections:
            st.divider()
            st.subheader("Export Options")
            col1, col2 = st.columns(2)

            # PDF Button
            with col1:
                pdf_bytes = generate_pdf(topic, st.session_state.generated_sections)
                st.download_button(
                    "Export as PDF",
                    pdf_bytes,
                    file_name=f"{topic.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            # DOCX Button
            with col2:
                docx_bytes = generate_docx(topic, st.session_state.generated_sections)
                st.download_button(
                    "Export as Word (DOCX)",
                    docx_bytes,
                    file_name=f"{topic.lower().replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )


if __name__ == "__main__":
    main()
