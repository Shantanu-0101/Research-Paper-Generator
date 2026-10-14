import os
import re
import io
import json
import urllib.parse
import urllib.request
import requests
from PIL import Image
from src.core.config import settings

IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)


def download_and_save_image(image_url: str, filename_prefix: str = "img") -> str | None:
    """
    Downloads an image from a URL, validates it with PIL, saves to data/images/,
    and returns the local file path.
    """
    if "wikimedia.org" in image_url or "wikipedia.org" in image_url:
        ua = "ResearchStyleWriter/1.0 (https://github.com/research-style-writer; contact@researchstyle.edu)"
    else:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    headers = {
        "User-Agent": ua,
        "Accept": "image/*, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        req = urllib.request.Request(image_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" in content_type:
                # Anti-bot HTML challenge (Cloudflare/Fastly) — not a real image
                return None
            img_bytes = response.read()

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if img.width < 100 or img.height < 100:
            return None  # Skip tiny icons/thumbnails

        import uuid
        filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.png"
        local_path = os.path.join(IMAGE_DIR, filename)
        img.save(local_path, "PNG")
        return local_path
    except Exception as e:
        print(f"[image_search] Failed to download image from {image_url}: {e}")
        return None


def search_tavily_images(query: str, used_paths: set = None) -> dict | None:
    """
    Queries Tavily Search API with include_images=True to find real web photos & diagrams.
    """
    if used_paths is None:
        used_paths = set()

    key = settings.tavily_api_key
    if not key or not key.startswith("tvly-"):
        print("[image_search] Tavily API key missing or invalid — skipping.")
        return None

    clean_terms = re.findall(r"\b[A-Za-z0-9_-]+\b", query)
    stop = {"and", "or", "the", "a", "an", "in", "on", "for", "with", "by", "of", "to", "as", "at"}
    filtered = [w for w in clean_terms if w.lower() not in stop][:8]
    search_term = " ".join(filtered) if filtered else query

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": key,
        "query": f"{search_term} academic figure",
        "include_images": True,
        "max_results": 10,
    }

    try:
        resp = requests.post(url, json=payload, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        images = data.get("images", [])
        print(f"[image_search] Tavily returned {len(images)} image(s) for: {search_term!r}")

        for img_url in images:
            if isinstance(img_url, str) and (img_url.startswith("http://") or img_url.startswith("https://")):
                if img_url in used_paths:
                    continue
                local_path = download_and_save_image(img_url, "tavily")
                if local_path and local_path not in used_paths:
                    used_paths.add(img_url)
                    used_paths.add(local_path)
                    return {
                        "local_path": local_path,
                        "source_url": img_url,
                        "source_name": "Tavily Web Search",
                    }
    except Exception as e:
        print(f"[image_search] Tavily image search error: {e}")
    return None


def search_europe_pmc_figures(query: str, used_paths: set = None) -> dict | None:
    """
    Queries Europe PMC Open Access REST API for published peer-reviewed paper figures.
    """
    if used_paths is None:
        used_paths = set()

    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    words = clean_q.split()[:4]
    search_term = " ".join(words)

    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": f'"{search_term}" HAS_FT:Y OPEN_ACCESS:Y',
        "format": "json",
        "pageSize": 5,
        "resultType": "core",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("resultList", {}).get("result", [])

        for paper in results:
            pmcid = paper.get("pmcid")
            if pmcid:
                paper_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
                xml_resp = requests.get(paper_url, timeout=8)
                if xml_resp.status_code == 200:
                    matches = re.findall(r'graphic[^>]+href="([^"]+)"', xml_resp.text)
                    for match in matches:
                        clean_match = match.replace('.jpg', '').replace('.png', '').replace('.gif', '')
                        img_full_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{clean_match}.jpg"
                        if img_full_url in used_paths:
                            continue
                        local_path = download_and_save_image(img_full_url, "pmc")
                        if local_path and local_path not in used_paths:
                            used_paths.add(img_full_url)
                            used_paths.add(local_path)
                            title = paper.get("title", "Europe PMC Paper Figure")
                            return {
                                "local_path": local_path,
                                "source_url": img_full_url,
                                "source_name": f"Europe PMC ({title[:40]}...)",
                            }
    except Exception as e:
        print(f"Europe PMC figure search error: {e}")
    return None


def search_wikimedia_images(query: str, used_paths: set = None) -> dict | None:
    """
    Searches Wikimedia Commons using sanitized keyword queries for CC-licensed figures.
    """
    if used_paths is None:
        used_paths = set()

    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    words = [w for w in clean_q.split() if len(w) > 2][:5]
    sanitized_query = " ".join(words)

    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"file:{sanitized_query}",
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
    }
    headers = {"User-Agent": "ResearchStyleWriter/1.0 (https://github.com/research-style-writer; contact@researchstyle.edu)"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})

        for page_id, page_info in pages.items():
            info_list = page_info.get("imageinfo", [])
            if info_list:
                img_url = info_list[0].get("url")
                mime = info_list[0].get("mime", "")
                if img_url and mime in ["image/jpeg", "image/png", "image/webp"]:
                    if img_url in used_paths:
                        continue
                    local_path = download_and_save_image(img_url, "wiki")
                    if local_path and local_path not in used_paths:
                        used_paths.add(img_url)
                        used_paths.add(local_path)
                        title = page_info.get("title", "").replace("File:", "")
                        return {
                            "local_path": local_path,
                            "source_url": img_url,
                            "source_name": f"Wikimedia Commons ({title[:30]})",
                        }
    except Exception as e:
        print(f"Wikimedia search error: {e}")
    return None


def search_unsplash_image(query: str, used_paths: set = None) -> dict | None:
    """
    Searches Unsplash API if UNSPLASH_API_KEY is available in settings.
    """
    if used_paths is None:
        used_paths = set()

    key = settings.unsplash_api_key
    if not key or len(key) < 20 or key == "UNSPLASH_API_KEY":
        return None

    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {key}"}
    params = {"query": query, "per_page": 5}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        for res_item in results:
            img_url = res_item["urls"]["regular"]
            if img_url in used_paths:
                continue
            user_name = res_item["user"]["name"]
            local_path = download_and_save_image(img_url, "unsplash")
            if local_path and local_path not in used_paths:
                used_paths.add(img_url)
                used_paths.add(local_path)
                return {
                    "local_path": local_path,
                    "source_url": img_url,
                    "source_name": f"Unsplash (photo by {user_name})",
                }
    except Exception as e:
        print(f"[image_search] Unsplash search error: {e}")
    return None


def get_academic_illustration(query: str, used_paths: set = None) -> dict | None:
    """
    Multi-tier fallback image search engine (optimized order):
    1. Tavily Web Images (most reliable)
    2. Wikimedia Commons
    3. Unsplash (if API key available)
    4. Europe PMC (last, due to fragile URLs)
    """
    if used_paths is None:
        used_paths = set()

    return (
        search_tavily_images(query, used_paths)
        or search_wikimedia_images(query, used_paths)
        or search_unsplash_image(query, used_paths)
        or search_europe_pmc_figures(query, used_paths)
    )
