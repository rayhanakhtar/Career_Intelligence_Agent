import type {
  CrawlAllResponse,
  CrawlAllResultResponse,
  CrawlResponse,
  Job,
  SearchResponse,
} from "../types";

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
  topK = 10,
  locations?: string[]
): Promise<SearchResponse> {
  const body: Record<string, unknown> = {
    resume_text: resumeText,
    top_k: topK,
  };
  if (locations && locations.length > 0) {
    body.locations = locations;
  }
  const res = await fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `POST /search failed: ${res.status}`);
  }
  return res.json();
}

export async function searchJobsWithFile(
  file: File,
  topK = 10,
  locations?: string[]
): Promise<SearchResponse> {
  const formData = new FormData();
  formData.append("resume_file", file);
  formData.append("top_k", String(topK));
  if (locations && locations.length > 0) {
    formData.append("locations", locations.join(","));
  }
  const res = await fetch(`${BASE}/search/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `POST /search/upload failed: ${res.status}`);
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

export async function triggerCrawlAll(): Promise<CrawlAllResponse> {
  const res = await fetch(`${BASE}/crawl/all`, {
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `POST /crawl/all failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchCrawlAllResult(
  taskId: string
): Promise<CrawlAllResultResponse> {
  const res = await fetch(`${BASE}/crawl/all/${taskId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body.detail || `GET /crawl/all/${taskId} failed: ${res.status}`
    );
  }
  return res.json();
}
