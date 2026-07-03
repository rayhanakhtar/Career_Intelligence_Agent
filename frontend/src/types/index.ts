export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  description: string;
  apply_url: string;
  department: string;
  employment_type: string;
  posted_at: string;
  source: string;
  source_id: string;
  created_at: string;
}

export interface JobWithScore extends Job {
  match_score: number;
}

export interface SearchResponse {
  results: JobWithScore[];
}

export interface CrawlResponse {
  task_id: string;
  status: string;
}
