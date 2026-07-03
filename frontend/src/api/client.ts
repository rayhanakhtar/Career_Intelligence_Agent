import type { CrawlResponse, Job, SearchResponse } from "../types";

const BASE = "/api";

export async function fetchJobs(): Promise<Job[]> {
  const res = await fetch(`${BASE}/jobs`);
  if (!res.ok) throw new Error(`GET /jobs failed: ${res.status}`);
  return res.json();
}

export async function fetchJob(id: number): Promise<Job> {
  const res = await fetch(`${BASE}/jobs/${id}`);
  if (!res.ok) throw new Error(`GET /jobs/${id} failed: ${res.status}`);
  return res.json();
}

export async function searchJobs(
  resumeText: string,
  topK = 10
): Promise<SearchResponse> {
  const res = await fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_text: resumeText, top_k: topK }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `POST /search failed: ${res.status}`);
  }
  return res.json();
}

export async function triggerCrawl(
  source: string,
  token: string
): Promise<CrawlResponse> {
  const res = await fetch(`${BASE}/crawl`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, token }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `POST /crawl failed: ${res.status}`);
  }
  return res.json();
}
