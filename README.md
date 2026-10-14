# Research Paper Generator

A Generative AI system that produces human-like academic research papers with near-zero AI detection scores. It learns writing style from reference papers, grounds content in live web sources, and applies a multi-pass humanization pipeline to eliminate detectable AI patterns.

## Key Features

- **Style-Aware Generation** — Extracts 12 quantitative style features from reference papers and instructs the LLM to match them
- **Web-Grounded Content** — Every section is backed by real, current sources via Tavily API (no hallucinated citations)
- **5-Pass Humanization Pipeline** — Structural manipulation + LLM-based multi-candidate re-ranking + lexical processing + quality gate + final enforcement
- **Automated Quality Assurance** — 5 evaluation checks with iterative refinement before humanization
- **Academic Image Integration** — Relevant figures from Tavily, Unsplash, Wikimedia, and Europe PMC with cross-section deduplication
- **Professional Export** — Complete papers as PDF (with embedded images and DejaVu fonts) or DOCX
- **Multi-Provider LLM Support** — xAI Grok, Google Gemini, Groq, and OpenRouter

## How It Works

1. **Upload** 3-8 reference PDF papers for writing style extraction
2. **Enter** a research topic and keywords
3. **Generate** — the system searches the web, builds structured prompts, generates each section, evaluates quality, rewrites if needed, then humanizes
4. **Export** the finished paper as PDF or DOCX

### Humanization Pipeline

The core innovation targeting Turnitin-style detection signals:

| Pass | What It Does | Method |
|------|-------------|--------|
| 1 | Structural variation | Burstiness injection, sentence restructuring, paragraph mixing (pure Python) |
| 2 | LLM rewrite | 3 candidates with different personas, scored and best picked |
| 3 | Lexical processing | Perplexity-raising word swaps, synonym rotation, human artifacts |
| 4 | Quality gate | Composite >= 80, burstiness CV >= 0.45, variety >= 0.35 |
| 5 | Final enforcement | Clean up any uniformity the LLM re-introduced |

### Detection Metrics (Before vs After)

| Metric | Before | After |
|--------|--------|-------|
| Burstiness CV | 0.15 - 0.25 | > 0.45 |
| Residual AI Tells | 5 - 15 words | 0 |
| Sentence Variety | 0.15 - 0.25 | > 0.35 |
| Composite Score | 30 - 50 | > 80 |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| LLM Orchestration | LangChain |
| LLM Providers | Google Gemini, xAI Grok, Groq, OpenRouter |
| Web Search | Tavily API |
| Embeddings | SentenceTransformer (all-MiniLM-L6-v2) |
| Vector Store | FAISS |
| PDF Extraction | PyMuPDF (fitz) with VLM fallback |
| Export | fpdf2 (PDF), python-docx (DOCX) |
| Image Sources | Tavily, Unsplash, Wikimedia, Europe PMC |

## Project Structure

```
RSW/
├── app.py                            # Streamlit web application
├── src/
│   └── core/
│       ├── config.py                 # Configuration & API keys
│       ├── ingestion/                # PDF loader, chunker, VLM extractor
│       ├── style/                    # Style analysis (12 features)
│       ├── llm/                      # Multi-provider LLM factory
│       ├── retrieval/                # Tavily web search
│       ├── generation/               # Section & paper generation
│       │   ├── generator.py          # Generation, evaluation & image pipeline
│       │   ├── evaluator.py          # 5 automated quality checks
│       │   └── prompts.py            # LLM prompt construction
│       ├── humanizer/                # 5-pass humanization pipeline
│       │   ├── humanizer.py          # Pipeline orchestrator
│       │   ├── burstiness.py         # Sentence length variation
│       │   ├── sentence_restructurer.py  # Clause reordering
│       │   ├── paragraph_mixer.py    # Paragraph structure variation
│       │   ├── reranker.py           # 3-candidate scoring
│       │   ├── lexical_booster.py    # Perplexity word swaps
│       │   ├── human_artifacts.py    # Hedges, parentheticals
│       │   └── patterns.py           # AI-tell word patterns
│       ├── illustration/             # Image search (4 sources)
│       ├── detection/                # AI detection score checker
│       ├── export/                   # PDF & DOCX generators
│       ├── embeddings/               # Embedding model wrapper
│       └── vectorstore/              # FAISS vector store
├── deliverables/
│   ├── rsw_walkthrough.ipynb         # Jupyter notebook walkthrough
│   ├── rsw_walkthrough.py            # Script version of walkthrough
│   ├── generate_report.py            # Project report generator
│   └── RSW_Project_Report.pdf        # Project report
└── data/
    ├── uploads/                      # Uploaded reference PDFs
    ├── images/                       # Downloaded academic images
    ├── vector_store/                 # FAISS index storage
    └── image_cache/                  # Per-topic image cache
```

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd RSW-Coursework
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API keys

Create a `.env` file in the project root (see `.env.example`):

```env
# LLM Provider (choose one: xai, gemini, groq, openrouter)
LLM_PROVIDER=gemini

# Provider API keys (set the one matching your provider)
GOOGLE_API_KEY=your_key_here

# Web search (required for grounded content)
TAVILY_API_KEY=your_key_here

# Image search (optional)
UNSPLASH_API_KEY=your_key_here
```

### 3. Run

```bash
streamlit run app.py
```

## Usage

1. Upload 3-8 reference PDFs and click **Process papers**
2. Enter a topic and keywords
3. Generate individual sections or a full paper
4. Enable humanization (Deep recommended) for best results
5. Export the final paper as PDF or DOCX

## Deliverables

1. **Jupyter Notebook** (`deliverables/rsw_walkthrough.ipynb`) — 12-step interactive walkthrough of the entire pipeline
2. **Python Script** (`deliverables/rsw_walkthrough.py`) — Same walkthrough as a runnable script
3. **Streamlit App** (`app.py`) — Web application
4. **Project Report** (`deliverables/RSW_Project_Report.pdf`) — Business understanding, project understanding, architecture diagram, flowchart, final outcome

## License

This project is for academic and educational purposes.
