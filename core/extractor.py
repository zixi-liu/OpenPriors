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

The user has shared something they learned. Extract actionable "priors" — principles
they can integrate into their daily life through practice.

SOURCE:
---
{content}
---

For each prior, provide:
- name: Short name (2-5 words)
- principle: The core insight in one sentence
- practice: A concrete way to practice this (specific, doable in under 5 minutes)
- trigger: When/where in daily life this applies (e.g., "before a meeting", "when writing an email")
- source: Where this came from (book title, article, etc.)

Return JSON:
{{
  "title": "source title or topic",
  "summary": "2-3 sentence summary of the source material",
  "priors": [
    {{
      "name": "...",
      "principle": "...",
      "practice": "...",
      "trigger": "...",
      "source": "..."
    }}
  ]
}}

Extract 3-7 priors. Focus on the most actionable, life-changing insights.
Return ONLY valid JSON."""


BOOK_EXTRACT_PROMPT = """You are an expert at extracting wisdom from books.

The user shared a book page (likely from Goodreads or similar). Extract the most valuable insights, including quotes, reviewer observations, and the author's core ideas.

SOURCE:
---
{content}
---

For each prior, provide:
- name: Short name (2-5 words)
- principle: The core insight in one sentence
- practice: A concrete way to practice this (specific, doable in under 5 minutes)
- trigger: When/where in daily life this applies
- source: Book title and author
- quote: A memorable quote from the book or reviews that captures this idea (if available, otherwise leave empty)

Return JSON:
{{
  "title": "Book Title by Author",
  "summary": "2-3 sentence summary of the book's core message",
  "notable_quotes": ["list of standout quotes from the book or reviews"],
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

Extract 3-7 priors. Prioritize insights backed by specific quotes or reviewer highlights.
Return ONLY valid JSON."""


def _is_book_source(content: str, source_hint: str = "") -> bool:
    """Detect if the content is from a book source."""
    book_signals = ["goodreads.com", "goodreads", "ratings", "reviews", "Want to Read"]
    combined = (content[:2000] + " " + source_hint).lower()
    return any(signal.lower() in combined for signal in book_signals)


async def extract_priors(content: str, source_hint: str = "") -> Dict[str, Any]:
    """Extract actionable priors from raw content."""
    if _is_book_source(content, source_hint):
        prompt = BOOK_EXTRACT_PROMPT.format(content=content[:15000])
    else:
        prompt = EXTRACT_PROMPT.format(content=content[:15000])
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
# Main URL extraction
# ---------------------------------------------------------------------------

async def extract_from_url(url: str) -> Dict[str, Any]:
    """
    Extract content from a URL. Strategy:
      1. YouTube → transcript API + oembed metadata
      2. Other URLs → HTML fetch
      3. Fallback → Gemini search grounding
    """
    video_id = _extract_youtube_id(url)

    if video_id:
        # YouTube: get real transcript + metadata
        metadata = _fetch_youtube_metadata(video_id)
        transcript = _fetch_youtube_transcript(video_id)

        if transcript:
            return {
                "accessible": True,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "content": transcript,
            }

        # No transcript available — try Gemini search with metadata hint
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

    # Non-YouTube: try HTML fetch first
    html_content = _fetch_html_content(url)
    if html_content:
        return {
            "accessible": True,
            "title": "",
            "content": html_content,
        }

    # Fallback: Gemini search grounding
    search_content = await _fetch_via_gemini_search(url)
    if search_content:
        return {
            "accessible": True,
            "title": "",
            "content": search_content,
        }

    return {"accessible": False, "title": "", "content": ""}
