from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import os
import time
import datetime
import requests
from cachetools import TTLCache

GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"
RECS_BASE = "https://api.semanticscholar.org/recommendations/v1"
API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://semantic-scholar-api.onrender.com")

app = FastAPI(
    title="Semantic Scholar Research API",
    version="1.1.0",
    description="Wrapper API for Semantic Scholar paper search, details, recommendations, reading-list generation, and foundational paper discovery.",
    servers=[
        {
            "url": PUBLIC_BASE_URL,
            "description": "Production server"
        }
    ],
)

# Caches
search_cache = TTLCache(maxsize=1000, ttl=3600)       # 1 hour
paper_cache = TTLCache(maxsize=2000, ttl=86400)       # 24 hours
related_cache = TTLCache(maxsize=1000, ttl=43200)     # 12 hours
reading_list_cache = TTLCache(maxsize=500, ttl=3600)  # 1 hour
foundational_cache = TTLCache(maxsize=500, ttl=3600)  # 1 hour


def s2_headers() -> dict:
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    return headers


def current_year() -> int:
    return datetime.datetime.now().year


def citation_density(citation_count: Optional[int], year: Optional[int]) -> float:
    citations = citation_count or 0
    y = year or current_year()
    age = max(current_year() - y + 1, 1)
    return citations / age


def make_summary(
    title: str,
    year: Optional[int],
    venue: Optional[str],
    citation_count: Optional[int]
) -> str:
    year_part = str(year) if year else "n.d."
    venue_part = venue if venue else "Unknown venue"
    citation_part = (
        f"cited {citation_count} times"
        if citation_count is not None
        else "citation count unavailable"
    )
    return f"{title} ({year_part}, {venue_part}) — {citation_part}."


def fetch_json(
    url: str,
    params: Optional[dict[str, Any]] = None,
    method: str = "GET",
    json_body: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    last_response = None

    for attempt in range(3):
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=s2_headers(), timeout=20)
            else:
                response = requests.post(url, params=params, json=json_body, headers=s2_headers(), timeout=20)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc

        last_response = response

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429 and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue

        raise HTTPException(status_code=response.status_code, detail=response.text)

    raise HTTPException(status_code=last_response.status_code, detail=last_response.text)


class AuthorItem(BaseModel):
    authorId: Optional[str] = None
    name: str


class PaperListItem(BaseModel):
    paperId: str
    title: str
    year: Optional[int] = None
    citationCount: Optional[int] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    authors: List[AuthorItem] = Field(default_factory=list)
    summary: str


class PaperSearchResponse(BaseModel):
    total: int
    data: List[PaperListItem]


class PaperDetailResponse(BaseModel):
    paperId: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    citationCount: Optional[int] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    authors: List[AuthorItem] = Field(default_factory=list)
    summary: str


class RecommendationResponse(BaseModel):
    sourcePaperId: str
    recommended: List[PaperListItem]


class ReadingListItem(BaseModel):
    rank: int
    paperId: str
    title: str
    year: Optional[int] = None
    citationCount: Optional[int] = None
    venue: Optional[str] = None
    whyIncluded: str
    url: Optional[str] = None
    summary: str


class ReadingListResponse(BaseModel):
    query: str
    items: List[ReadingListItem]


class FoundationalPaperItem(BaseModel):
    rank: int
    paperId: str
    title: str
    year: Optional[int] = None
    citationCount: Optional[int] = None
    venue: Optional[str] = None
    score: float
    whyIncluded: str
    url: Optional[str] = None
    summary: str


class FoundationalPaperResponse(BaseModel):
    query: str
    items: List[FoundationalPaperItem]


def normalize_list_item(paper: dict[str, Any]) -> dict[str, Any]:
    title = paper.get("title", "")
    year = paper.get("year")
    venue = paper.get("venue")
    citation_count = paper.get("citationCount")

    return {
        "paperId": paper["paperId"],
        "title": title,
        "year": year,
        "citationCount": citation_count,
        "venue": venue,
        "url": paper.get("url"),
        "authors": paper.get("authors", []),
        "summary": make_summary(title, year, venue, citation_count),
    }


@app.get("/papers/search", response_model=PaperSearchResponse, operation_id="searchPapers")
def search_papers(
    q: str = Query(..., description="Search query"),
    limit: int = Query(8, ge=1, le=20)
):
    cache_key = f"search:{q}:{limit}"
    if cache_key in search_cache:
        return search_cache[cache_key]

    params = {
        "query": q,
        "limit": limit,
        "fields": "paperId,title,year,citationCount,venue,url,authors",
    }
    data = fetch_json(f"{GRAPH_BASE}/paper/search", params=params)

    items = [normalize_list_item(paper) for paper in data.get("data", [])]
    items.sort(
        key=lambda p: citation_density(p.get("citationCount"), p.get("year")),
        reverse=True,
    )

    result = {
        "total": data.get("total", len(items)),
        "data": items,
    }
    search_cache[cache_key] = result
    return result


@app.get("/paper/{paper_id}", response_model=PaperDetailResponse, operation_id="getPaper")
def get_paper(paper_id: str):
    if paper_id in paper_cache:
        return paper_cache[paper_id]

    params = {
        "fields": "paperId,title,abstract,year,citationCount,venue,url,authors",
    }
    data = fetch_json(f"{GRAPH_BASE}/paper/{paper_id}", params=params)

    result = {
        "paperId": data["paperId"],
        "title": data["title"],
        "abstract": data.get("abstract"),
        "year": data.get("year"),
        "citationCount": data.get("citationCount"),
        "venue": data.get("venue"),
        "url": data.get("url"),
        "authors": data.get("authors", []),
        "summary": make_summary(
            data.get("title", ""),
            data.get("year"),
            data.get("venue"),
            data.get("citationCount"),
        ),
    }
    paper_cache[paper_id] = result
    return result


@app.get("/paper/{paper_id}/related", response_model=RecommendationResponse, operation_id="getRelatedPapers")
def get_related_papers(
    paper_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    cache_key = f"related:{paper_id}:{limit}"
    if cache_key in related_cache:
        return related_cache[cache_key]

    params = {
        "limit": limit,
        "fields": "paperId,title,year,citationCount,venue,url,authors",
    }
    data = fetch_json(f"{RECS_BASE}/papers/forpaper/{paper_id}", params=params)

    items = [normalize_list_item(paper) for paper in data.get("recommendedPapers", [])]
    items.sort(
        key=lambda p: citation_density(p.get("citationCount"), p.get("year")),
        reverse=True,
    )

    result = {
        "sourcePaperId": paper_id,
        "recommended": items,
    }
    related_cache[cache_key] = result
    return result


@app.get("/papers/reading-list", response_model=ReadingListResponse, operation_id="buildReadingList")
def build_reading_list(
    q: str = Query(..., description="Topic or query"),
    limit: int = Query(5, ge=1, le=10)
):
    cache_key = f"reading-list:{q}:{limit}"
    if cache_key in reading_list_cache:
        return reading_list_cache[cache_key]

    params = {
        "query": q,
        "limit": limit,
        "fields": "paperId,title,year,citationCount,venue,url",
    }
    data = fetch_json(f"{GRAPH_BASE}/paper/search", params=params)

    ranked = sorted(
        data.get("data", []),
        key=lambda p: citation_density(p.get("citationCount"), p.get("year")),
        reverse=True,
    )

    items = []
    for idx, paper in enumerate(ranked[:limit], start=1):
        cite_count = paper.get("citationCount")
        year = paper.get("year")
        score = citation_density(cite_count, year)

        reason = "Relevant topical result"
        if isinstance(cite_count, int) and cite_count > 1000:
            reason = "Seminal highly cited paper"
        elif isinstance(cite_count, int) and cite_count > 250:
            reason = "Influential paper or strong overview"
        elif year and year >= current_year() - 3:
            reason = "Recent research worth reviewing"
        elif score > 50:
            reason = "High citation-density paper"

        items.append({
            "rank": idx,
            "paperId": paper["paperId"],
            "title": paper["title"],
            "year": year,
            "citationCount": cite_count,
            "venue": paper.get("venue"),
            "whyIncluded": reason,
            "url": paper.get("url"),
            "summary": make_summary(
                paper.get("title", ""),
                year,
                paper.get("venue"),
                cite_count,
            ),
        })

    result = {
        "query": q,
        "items": items,
    }
    reading_list_cache[cache_key] = result
    return result


@app.get("/papers/foundational", response_model=FoundationalPaperResponse, operation_id="getFoundationalPapers")
def get_foundational_papers(
    q: str = Query(..., description="Topic or research area"),
    limit: int = Query(5, ge=1, le=10)
):
    cache_key = f"foundational:{q}:{limit}"
    if cache_key in foundational_cache:
        return foundational_cache[cache_key]

    params = {
        "query": q,
        "limit": max(limit * 3, 10),
        "fields": "paperId,title,year,citationCount,venue,url",
    }
    data = fetch_json(f"{GRAPH_BASE}/paper/search", params=params)

    candidates = []
    for paper in data.get("data", []):
        cite_count = paper.get("citationCount") or 0
        year = paper.get("year")
        score = citation_density(cite_count, year)

        reason = "Foundational candidate"
        if cite_count > 2000:
            reason = "Seminal highly cited paper"
        elif cite_count > 500:
            reason = "Strong foundational paper"
        elif score > 75:
            reason = "High citation-density foundational paper"

        candidates.append({
            "paperId": paper["paperId"],
            "title": paper["title"],
            "year": year,
            "citationCount": cite_count,
            "venue": paper.get("venue"),
            "score": round(score, 2),
            "whyIncluded": reason,
            "url": paper.get("url"),
            "summary": make_summary(
                paper.get("title", ""),
                year,
                paper.get("venue"),
                cite_count,
            ),
        })

    candidates.sort(key=lambda p: p["score"], reverse=True)

    items = []
    for idx, paper in enumerate(candidates[:limit], start=1):
        items.append({
            "rank": idx,
            **paper,
        })

    result = {
        "query": q,
        "items": items,
    }
    foundational_cache[cache_key] = result
    return result