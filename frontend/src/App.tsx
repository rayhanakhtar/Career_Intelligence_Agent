import { useCallback, useState } from "react";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Typography from "@mui/material/Typography";

import type { JobWithScore } from "./types";
import {
  fetchCrawlAllResult,
  searchJobs,
  searchJobsWithFile,
  triggerCrawl,
  triggerCrawlAll,
} from "./api/client";
import CrawlForm from "./components/CrawlForm";
import JobTable from "./components/JobTable";
import Layout from "./components/Layout";
import SearchForm from "./components/SearchForm";

export default function App() {
  const [results, setResults] = useState<JobWithScore[]>([]);
  const [searching, setSearching] = useState(false);
  const [crawling, setCrawling] = useState(false);
  const [crawlAllLoading, setCrawlAllLoading] = useState(false);
  const [crawlAllResults, setCrawlAllResults] = useState<Record<
    string,
    number
  > | null>(null);
  const [snackbar, setSnackbar] = useState<{
    severity: "success" | "error";
    message: string;
  } | null>(null);

  const handleSearch = useCallback(
    async (resumeText: string, topK: number, locations?: string[]) => {
      setSearching(true);
      try {
        const data = await searchJobs(resumeText, topK, locations);
        setResults(data.results);
      } catch (err) {
        setSnackbar({
          severity: "error",
          message: err instanceof Error ? err.message : "Search failed",
        });
      } finally {
        setSearching(false);
      }
    },
    []
  );

  const handleSearchFile = useCallback(
    async (file: File, topK: number, locations?: string[]) => {
      setSearching(true);
      try {
        const data = await searchJobsWithFile(file, topK, locations);
        setResults(data.results);
      } catch (err) {
        setSnackbar({
          severity: "error",
          message: err instanceof Error ? err.message : "Search failed",
        });
      } finally {
        setSearching(false);
      }
    },
    []
  );

  const handleCrawl = useCallback(
    async (source: string, token: string) => {
      setCrawling(true);
      try {
        const data = await triggerCrawl(source, token);
        setSnackbar({
          severity: "success",
          message: `Crawl accepted (task: ${data.task_id.slice(0, 8)}…)`,
        });
      } catch (err) {
        setSnackbar({
          severity: "error",
          message: err instanceof Error ? err.message : "Crawl failed",
        });
      } finally {
        setCrawling(false);
      }
    },
    []
  );

  const handleCrawlAll = useCallback(async () => {
    setCrawlAllLoading(true);
    setCrawlAllResults(null);
    try {
      const { task_id } = await triggerCrawlAll();
      setSnackbar({
        severity: "success",
        message: `Crawl-all accepted (task: ${task_id.slice(0, 8)}…). Polling for results...`,
      });
      // Poll for results every 3 seconds, up to 60 seconds.
      const pollInterval = setInterval(async () => {
        try {
          const result = await fetchCrawlAllResult(task_id);
          if (result.status === "completed") {
            clearInterval(pollInterval);
            setCrawlAllResults(result.results);
            const total = Object.values(result.results).reduce(
              (a, b) => a + b,
              0
            );
            setSnackbar({
              severity: "success",
              message: `Crawl-all complete: ${total} jobs stored`,
            });
            setCrawlAllLoading(false);
          }
        } catch {
          clearInterval(pollInterval);
          setCrawlAllLoading(false);
        }
      }, 3000);
      // Timeout after 60 seconds.
      setTimeout(() => {
        clearInterval(pollInterval);
        setCrawlAllLoading(false);
      }, 60000);
    } catch (err) {
      setSnackbar({
        severity: "error",
        message: err instanceof Error ? err.message : "Crawl-all failed",
      });
      setCrawlAllLoading(false);
    }
  }, []);

  return (
    <Layout>
      <Typography variant="h5" gutterBottom>
        Discover AI/ML internships and entry-level jobs
      </Typography>

      <SearchForm
        onSearch={handleSearch}
        onSearchFile={handleSearchFile}
        loading={searching}
      />
      <CrawlForm
        onCrawl={handleCrawl}
        onCrawlAll={handleCrawlAll}
        loading={crawling}
        crawlAllLoading={crawlAllLoading}
        crawlAllResults={crawlAllResults}
      />

      <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
        Ranked Results
      </Typography>
      <JobTable jobs={results} />

      <Snackbar
        open={snackbar !== null}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {snackbar ? (
          <Alert
            severity={snackbar.severity}
            onClose={() => setSnackbar(null)}
            variant="filled"
          >
            {snackbar.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Layout>
  );
}
