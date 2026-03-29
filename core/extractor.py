"""
Prior Extractor

Takes raw input (URL content, PDF text, user notes) and extracts
actionable principles that can be practiced.

URL handling:
  - YouTube → fetch real transcript via youtube-transcript-api (free, no key)
  - Other URLs → fetch HTML and extract text, fall back to Gemini search grounding
"""

import re
import json
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from core.llm import complete_json
from core.config import get_api_key

EXTRACT_PROMPT = """You are an expert at turning knowledge into actionable practice.

The user has shared something they learned. First, identify what type of source this is (book, movie/TV, article, podcast, personal notes, etc.), then adapt your extraction accordingly.

SOURCE:
---
{content}
---

Adapt your extraction to the source type:
- Books → include notable quotes from the text or reviews, key themes
- Movies/TV → include character lessons, thematic insights, memorable dialogue
- Articles/blogs → include key arguments, surprising findings, data points
- Podcasts/talks → include speaker insights, frameworks discussed, key exchanges
- Personal notes → focus on the user's own reflections and intentions

For each prior, provide:
- name: Short name (2-5 words)
- principle: The core insight in one sentence
- practice: A concrete way to practice this (specific, doable in under 5 minutes)
- trigger: When/where in daily life this applies (e.g., "before a meeting", "when writing an email")
- source: Where this came from (book title, movie name, article, etc.)
- quote: A relevant quote, line of dialogue, or passage that captures this idea (leave empty if none available)

Return JSON:
{{
  "title": "source title",
  "source_type": "book | movie | article | podcast | notes | other",
  "summary": "2-3 sentence summary of the source material",
  "notable_quotes": ["standout quotes, dialogue, or passages — include all you can find"],
  "priors": [
    {{
      "name": "...",
      "principle": "...",
      "practice": "...",
      "trigger": "...",
      "source": "...",
      "quote": "..."
    }}
  ]
}}

Extract as many priors as the content supports. Focus on actionable, life-changing insights.
Return ONLY valid JSON."""


async def extract_priors(content: str, source_hint: str = "") -> Dict[str, Any]:
    """Extract actionable priors from raw content."""
    prompt = EXTRACT_PROMPT.format(content=content[:25000])
    if source_hint:
        prompt += f"\n\nSource hint: {source_hint}"

    return await complete_json(prompt)


# ---------------------------------------------------------------------------
# YouTube helpers
# ---------------------------------------------------------------------------

def _extract_youtube_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    parsed = urlparse(url)

    # youtu.be/VIDEO_ID
    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/").split("/")[0]

    # youtube.com/watch?v=VIDEO_ID
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        # youtube.com/embed/VIDEO_ID or /shorts/VIDEO_ID
        for prefix in ("/embed/", "/shorts/", "/v/"):
            if parsed.path.startswith(prefix):
                return parsed.path[len(prefix):].split("/")[0]

    return None


def _fetch_youtube_transcript(video_id: str) -> Optional[str]:
    """Fetch transcript text from YouTube. Returns None if unavailable."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id)
        text = " ".join(snippet.text for snippet in transcript.snippets)
        return text if text.strip() else None
    except Exception:
        return None


def _fetch_youtube_metadata(video_id: str) -> Dict[str, str]:
    """Fetch title and author via YouTube oembed (free, no key)."""
    try:
        import urllib.request
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(oembed_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {
                "title": data.get("title", ""),
                "author": data.get("author_name", ""),
            }
    except Exception:
        return {"title": "", "author": ""}


# ---------------------------------------------------------------------------
# Gemini search grounding fallback
# ---------------------------------------------------------------------------

async def _fetch_via_gemini_search(url: str, hint: str = "") -> Optional[str]:
    """Use Gemini + Google Search grounding to get content about a URL."""
    try:
        from google import genai
        from google.genai.types import Tool, GoogleSearch

        key = get_api_key("gemini")
        if not key:
            return None

        client = genai.Client(api_key=key)

        prompt = f"""Search for and provide a detailed summary of the content at this URL: {url}"""
        if hint:
            prompt += f"\nContext: {hint}"
        prompt += """

Include all major topics, key arguments, specific examples, quotes, and insights discussed. Be as thorough as possible."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "tools": [Tool(google_search=GoogleSearch())],
                "temperature": 0.2,
            },
        )
        return response.text if response.text else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# HTML fetch for articles/blogs
# ---------------------------------------------------------------------------

def _fetch_html_content(url: str) -> Optional[str]:
    """Fetch and extract text from an HTML page."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Simple HTML-to-text: strip tags, decode entities
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) > 100 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Enrichment: fetch additional content for books/movies
# ---------------------------------------------------------------------------

def _extract_goodreads_quotes_url(url: str) -> Optional[str]:
    """Extract the quotes page URL from a Goodreads book URL."""
    # goodreads.com/book/show/12345-title -> goodreads.com/work/quotes/12345-title
    match = re.search(r'goodreads\.com/(?:en/)?book/show/(\d+[^/?]*)', url)
    if match:
        book_slug = match.group(1)
        return f"https://www.goodreads.com/work/quotes/{book_slug}"
    return None


def _fetch_goodreads_quotes(url: str) -> str:
    """Fetch quotes from the Goodreads quotes page for a book."""
    quotes_url = _extract_goodreads_quotes_url(url)
    if not quotes_url:
        return ""
    content = _fetch_html_content(quotes_url)
    return content or ""


async def _search_quotes(url: str, source_type: str = "book") -> str:
    """Use Gemini search to find quotes and insights about a book/movie from its URL."""
    try:
        from google import genai
        from google.genai.types import Tool, GoogleSearch

        key = get_api_key("gemini")
        if not key:
            return ""

        client = genai.Client(api_key=key)

        if source_type == "movie":
            query = f"Find the best quotes, memorable dialogue, and key themes from this movie/show: {url}. Include character insights and life lessons."
        else:
            query = f"Find the best quotes and key insights from this book: {url}. Include notable passages, reader highlights, and core ideas."

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config={
                "tools": [Tool(google_search=GoogleSearch())],
                "temperature": 0.2,
            },
        )
        return response.text or ""
    except Exception:
        return ""


ENRICHABLE_SITES = {
    "goodreads": "book",
    "letterboxd": "movie",
    "imdb": "movie",
    "rottentomatoes": "movie",
}


def _get_enrichable_type(url: str) -> Optional[str]:
    """Return 'book' or 'movie' if this is a known site we should enrich, else None."""
    url_lower = url.lower()
    for site, source_type in ENRICHABLE_SITES.items():
        if site in url_lower:
            return source_type
    return None


async def _enrich_content(url: str, base_content: str) -> str:
    """Enrich content with additional quotes for known book/movie sites."""
    source_type = _get_enrichable_type(url)
    if not source_type:
        return base_content

    # Base content first (authoritative source)
    parts = [base_content]

    # Goodreads: also fetch the quotes page
    if "goodreads" in url.lower():
        quotes_content = _fetch_goodreads_quotes(url)
        if quotes_content:
            parts.append(f"\n\n--- QUOTES PAGE ---\n{quotes_content}")

    # Web search for additional quotes (supplementary — may not be perfectly on-topic)
    search_results = await _search_quotes(url, source_type)
    if search_results:
        parts.append(f"\n\n--- ADDITIONAL WEB RESULTS (use only if relevant to the main source above) ---\n{search_results}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main URL extraction (multi-step pipeline)
# ---------------------------------------------------------------------------

async def extract_from_url(url: str) -> Dict[str, Any]:
    """
    Multi-step extraction pipeline:
      1. Fetch — get raw content (YouTube transcript, HTML, or Gemini search)
      2. Identify — detect title and source type
      3. Enrich — for books/movies, fetch additional quotes and insights
      4. Return combined content for prior extraction
    """
    video_id = _extract_youtube_id(url)

    # --- Step 1: Fetch ---
    if video_id:
        metadata = _fetch_youtube_metadata(video_id)
        transcript = _fetch_youtube_transcript(video_id)

        if transcript:
            return {
                "accessible": True,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "content": transcript,
            }

        hint = f"{metadata['title']} by {metadata['author']}" if metadata["title"] else ""
        search_content = await _fetch_via_gemini_search(url, hint)
        if search_content:
            return {
                "accessible": True,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "content": search_content,
            }

        return {"accessible": False, "title": metadata.get("title", ""), "content": ""}

    # Non-YouTube: fetch HTML
    html_content = _fetch_html_content(url)
    if not html_content:
        html_content = await _fetch_via_gemini_search(url) or ""

    if not html_content:
        return {"accessible": False, "title": "", "content": ""}

    # --- Step 2: Enrich (only for known book/movie sites) ---
    enriched_content = await _enrich_content(url, html_content)

    return {
        "accessible": True,
        "title": "",
        "content": enriched_content,
    }
