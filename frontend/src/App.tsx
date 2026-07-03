import { useCallback, useState } from "react";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Typography from "@mui/material/Typography";

import type { JobWithScore } from "./types";
import { searchJobs, triggerCrawl } from "./api/client";
import CrawlForm from "./components/CrawlForm";
import JobTable from "./components/JobTable";
import Layout from "./components/Layout";
import SearchForm from "./components/SearchForm";

export default function App() {
  const [results, setResults] = useState<JobWithScore[]>([]);
  const [searching, setSearching] = useState(false);
  const [crawling, setCrawling] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    severity: "success" | "error";
    message: string;
  } | null>(null);

  const handleSearch = useCallback(
    async (resumeText: string, topK: number) => {
      setSearching(true);
      try {
        const data = await searchJobs(resumeText, topK);
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

  return (
    <Layout>
      <Typography variant="h5" gutterBottom>
        Discover AI/ML internships and entry-level jobs
      </Typography>

      <SearchForm onSearch={handleSearch} loading={searching} />
      <CrawlForm onCrawl={handleCrawl} loading={crawling} />

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
