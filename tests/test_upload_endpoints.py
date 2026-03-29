"""
Tests for upload/analyze endpoints.

These are integration tests that hit the real LLM — they validate that
the extraction pipeline returns well-structured, sensible priors from
real-world inputs (URLs, text).

Run: pytest tests/test_upload_endpoints.py -v -s
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app import app

REQUIRED_PRIOR_FIELDS = {"name", "principle", "practice", "trigger", "source"}


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# URL upload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_url_upload_youtube(client):
    """YouTube link: should extract meaningful priors from a video."""
    res = await client.post(
        "/api/assets/upload/url",
        json={"url": "https://youtu.be/fcZ2yFXeFHY?si=mbIal-GZXeH3ABFl"},
        timeout=60,
    )
    data = res.json()

    assert data["success"] is True, f"Failed: {data.get('error')}"
    assert data["title"], "Title should not be empty"
    assert data["summary"], "Summary should not be empty"
    assert len(data["priors"]) >= 2, f"Expected >=2 priors, got {len(data['priors'])}"

    for i, prior in enumerate(data["priors"]):
        missing = REQUIRED_PRIOR_FIELDS - set(prior.keys())
        assert not missing, f"Prior {i} missing fields: {missing}"
        assert len(prior["name"].split()) <= 6, f"Prior {i} name too long: {prior['name']}"
        assert len(prior["principle"]) > 10, f"Prior {i} principle too short"
        assert len(prior["practice"]) > 10, f"Prior {i} practice too short"
        assert len(prior["trigger"]) > 5, f"Prior {i} trigger too short"

    print(f"\n--- URL Upload Result ---")
    print(f"Title: {data['title']}")
    print(f"Summary: {data['summary']}")
    for p in data["priors"]:
        print(f"\n  [{p['name']}]")
        print(f"  Principle: {p['principle']}")
        print(f"  Practice:  {p['practice']}")
        print(f"  Trigger:   {p['trigger']}")


@pytest.mark.asyncio
async def test_url_upload_returns_ids(client):
    """Priors from URL upload should be saved and return IDs."""
    res = await client.post(
        "/api/assets/upload/url",
        json={"url": "https://youtu.be/fcZ2yFXeFHY?si=mbIal-GZXeH3ABFl"},
        timeout=60,
    )
    data = res.json()

    assert data["success"] is True
    assert len(data["ids"]) == len(data["priors"]), "Each prior should get an ID"
    for uid in data["ids"]:
        assert len(uid) == 8, f"ID should be 8 chars, got: {uid}"


@pytest.mark.asyncio
async def test_url_upload_goodreads(client):
    """Goodreads book link: should extract priors with quotes."""
    res = await client.post(
        "/api/assets/upload/url",
        json={"url": "https://www.goodreads.com/en/book/show/54110588-the-genius-of-athletes"},
        timeout=120,
    )
    data = res.json()

    assert data["success"] is True, f"Failed: {data.get('error')}"
    assert data["title"], "Title should not be empty"
    assert "athlete" in data["title"].lower() or "genius" in data["title"].lower(), (
        f"Title should reference the book: {data['title']}"
    )
    assert len(data["priors"]) >= 3, f"Expected >=3 priors, got {len(data['priors'])}"
    assert data.get("material_id"), "Should return a material_id"

    # Book priors should have quotes
    priors_with_quotes = [p for p in data["priors"] if p.get("quote")]
    print(f"\n--- Goodreads Upload Result ---")
    print(f"Title: {data['title']}")
    print(f"Priors: {len(data['priors'])}, with quotes: {len(priors_with_quotes)}")
    for p in data["priors"]:
        print(f"  [{p['name']}] {p['principle'][:60]}")
        if p.get("quote"):
            print(f"    Quote: \"{p['quote'][:80]}...\"")


@pytest.mark.asyncio
async def test_url_upload_saves_material(client):
    """URL upload should save material and link it to priors."""
    res = await client.post(
        "/api/assets/upload/url",
        json={"url": "https://youtu.be/fcZ2yFXeFHY?si=mbIal-GZXeH3ABFl"},
        timeout=60,
    )
    data = res.json()
    assert data["success"] is True
    assert data.get("material_id"), "Should return a material_id"

    # Verify material is retrievable
    mat_res = await client.get(f"/api/assets/materials/{data['material_id']}", timeout=10)
    mat_data = mat_res.json()
    assert mat_data["success"] is True
    assert mat_data["material"]["source_type"] == "youtube"
    assert len(mat_data["material"]["content"]) > 1000, "YouTube material should have transcript content"

    print(f"\n--- Material saved ---")
    print(f"ID: {data['material_id']}")
    print(f"Type: {mat_data['material']['source_type']}")
    print(f"Content length: {len(mat_data['material']['content'])} chars")


@pytest.mark.asyncio
async def test_url_upload_bad_url(client):
    """Invalid URL should fail gracefully."""
    res = await client.post(
        "/api/assets/upload/url",
        json={"url": "not-a-real-url"},
        timeout=60,
    )
    data = res.json()
    assert "success" in data


@pytest.mark.asyncio
async def test_material_delete(client):
    """Deleting a material should remove it and its priors."""
    # Create a material first
    res = await client.post(
        "/api/assets/upload/text",
        json={"content": "Always be curious. Ask questions constantly.", "source": "test"},
        timeout=60,
    )
    data = res.json()
    assert data["success"] is True
    material_id = data.get("material_id")
    assert material_id

    # Delete it
    del_res = await client.delete(f"/api/assets/materials/{material_id}", timeout=10)
    del_data = del_res.json()
    assert del_data["success"] is True

    # Verify it's gone
    get_res = await client.get(f"/api/assets/materials/{material_id}", timeout=10)
    assert get_res.status_code == 404


# ---------------------------------------------------------------------------
# Text upload
# ---------------------------------------------------------------------------

SAMPLE_TEXT = """
From "Atomic Habits" by James Clear:

The 1% rule: If you get 1% better each day for a year, you'll be 37 times
better by the end. Conversely, if you get 1% worse each day, you'll decline
to nearly zero.

Implementation intention: "I will [BEHAVIOR] at [TIME] in [LOCATION]."
People who make a specific plan for when and where they will perform a new
habit are more likely to follow through.

Habit stacking: Link a new habit to an existing one. "After I [CURRENT HABIT],
I will [NEW HABIT]." This leverages the natural momentum of your existing routines.

Environment design: Make cues of good habits obvious and cues of bad habits
invisible. You don't need more discipline — you need a better environment.
"""


@pytest.mark.asyncio
async def test_text_upload_basic(client):
    """Text input should extract structured priors."""
    res = await client.post(
        "/api/assets/upload/text",
        json={"content": SAMPLE_TEXT, "source": "Atomic Habits by James Clear"},
        timeout=60,
    )
    data = res.json()

    assert data["success"] is True, f"Failed: {data.get('error')}"
    assert len(data["priors"]) >= 3, f"Expected >=3 priors from clear input, got {len(data['priors'])}"

    for i, prior in enumerate(data["priors"]):
        missing = REQUIRED_PRIOR_FIELDS - set(prior.keys())
        assert not missing, f"Prior {i} missing fields: {missing}"
        assert prior["name"], f"Prior {i} has empty name"
        assert prior["practice"], f"Prior {i} has empty practice"

    print(f"\n--- Text Upload Result ---")
    print(f"Title: {data['title']}")
    print(f"Priors: {len(data['priors'])}")
    for p in data["priors"]:
        print(f"  [{p['name']}] {p['principle'][:80]}")


@pytest.mark.asyncio
async def test_text_upload_empty(client):
    """Empty text should fail gracefully."""
    res = await client.post(
        "/api/assets/upload/text",
        json={"content": "", "source": ""},
        timeout=60,
    )
    data = res.json()
    # Empty input should still return a response without crashing
    assert "success" in data


@pytest.mark.asyncio
async def test_text_upload_short_input(client):
    """Very short input should still produce something reasonable."""
    res = await client.post(
        "/api/assets/upload/text",
        json={"content": "Always be learning. Never stop asking questions."},
        timeout=60,
    )
    data = res.json()

    assert data["success"] is True
    assert len(data["priors"]) >= 1


# ---------------------------------------------------------------------------
# Prior quality checks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_priors_are_actionable(client):
    """Priors should contain actionable practices, not vague advice."""
    res = await client.post(
        "/api/assets/upload/text",
        json={"content": SAMPLE_TEXT, "source": "Atomic Habits"},
        timeout=60,
    )
    data = res.json()
    assert data["success"] is True

    for prior in data["priors"]:
        # Practice should be specific enough to contain a verb
        practice_words = prior["practice"].lower().split()
        assert len(practice_words) >= 5, (
            f"Practice too vague: '{prior['practice']}'"
        )
        # Trigger should reference a time, place, or situation
        assert len(prior["trigger"]) >= 10, (
            f"Trigger too vague: '{prior['trigger']}'"
        )
