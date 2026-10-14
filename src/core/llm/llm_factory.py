from langchain_groq import ChatGroq
from src.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


def get_llm(temperature: float = 0.7):
    """Returns the main generation LLM based on LLM_PROVIDER setting."""
    provider = settings.llm_provider

    if provider == "groq":
        return ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=temperature,
        )

    if provider == "xai":
        return ChatOpenAI(
            model=settings.xai_model,
            openai_api_key=settings.xai_api_key,
            openai_api_base="https://api.x.ai/v1",
            temperature=temperature,
        )

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )

    if provider == "openrouter":
        return ChatOpenAI(
            model=settings.openrouter_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'")


def get_humanizer_llm(temperature: float = 0.85):
    """
    Returns a DIFFERENT model than get_llm() for humanization.

    Using a different model family breaks the statistical fingerprint
    that AI detectors use — each model family has different token
    probability distributions (perplexity patterns, burstiness biases).

    Priority order for alternate provider:
      xai      → gemini (very different writing style)
      gemini   → groq   (different base model architecture)
      groq     → gemini
      openrouter → gemini

    Falls back to same provider if alternate key is missing.
    """
    main_provider = settings.llm_provider

    # Determine which alternate to use
    if main_provider == "xai":
        # Try Gemini first (most different from Grok)
        if settings.google_api_key and settings.google_api_key not in ("", "GOOGLE_API_KEY"):
            print(f"[humanizer] Using Gemini ({settings.gemini_model}) as alternate humanizer LLM")
            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                temperature=temperature,
            )
        # Fallback to Groq
        if settings.groq_api_key and settings.groq_api_key not in ("", "GROQ_API_KEY"):
            print(f"[humanizer] Using Groq ({settings.groq_model}) as alternate humanizer LLM")
            return ChatGroq(
                model=settings.groq_model,
                groq_api_key=settings.groq_api_key,
                temperature=temperature,
            )

    elif main_provider == "gemini":
        # Try Groq
        if settings.groq_api_key and settings.groq_api_key not in ("", "GROQ_API_KEY"):
            print(f"[humanizer] Using Groq ({settings.groq_model}) as alternate humanizer LLM")
            return ChatGroq(
                model=settings.groq_model,
                groq_api_key=settings.groq_api_key,
                temperature=temperature,
            )
        # Fallback to xAI
        if settings.xai_api_key and settings.xai_api_key not in ("", "XAI_API_KEY"):
            print(f"[humanizer] Using xAI ({settings.xai_model}) as alternate humanizer LLM")
            return ChatOpenAI(
                model=settings.xai_model,
                openai_api_key=settings.xai_api_key,
                openai_api_base="https://api.x.ai/v1",
                temperature=temperature,
            )

    elif main_provider in ("groq", "openrouter"):
        # Try Gemini
        if settings.google_api_key and settings.google_api_key not in ("", "GOOGLE_API_KEY"):
            print(f"[humanizer] Using Gemini ({settings.gemini_model}) as alternate humanizer LLM")
            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                temperature=temperature,
            )

    # No alternate available — fall back to the same provider
    print(f"[humanizer] No alternate LLM key found — falling back to main provider ({main_provider})")
    return get_llm(temperature=temperature)

