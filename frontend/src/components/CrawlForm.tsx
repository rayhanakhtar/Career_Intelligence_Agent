import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

interface CrawlFormProps {
  onCrawl: (source: string, token: string) => Promise<void>;
  onCrawlAll: () => Promise<void>;
  loading: boolean;
  crawlAllLoading: boolean;
  crawlAllResults: Record<string, number> | null;
}

const SOURCES = [
  { value: "greenhouse", label: "Greenhouse" },
  { value: "lever", label: "Lever" },
];

export default function CrawlForm({
  onCrawl,
  onCrawlAll,
  loading,
  crawlAllLoading,
  crawlAllResults,
}: CrawlFormProps) {
  const [source, setSource] = useState("greenhouse");
  const [token, setToken] = useState("");

  const handleSubmit = () => {
    if (!token.trim()) return;
    onCrawl(source, token.trim());
  };

  const resultEntries = crawlAllResults
    ? Object.entries(crawlAllResults)
    : null;

  return (
    <Box
      sx={{
        p: 3,
        mb: 3,
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
      }}
    >
      <Typography variant="h6" gutterBottom>
        Crawl Jobs
      </Typography>

      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", mb: 2 }}>
        <TextField
          select
          label="Source"
          size="small"
          sx={{ width: 160 }}
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          {SOURCES.map((s) => (
            <MenuItem key={s.value} value={s.value}>
              {s.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Token"
          size="small"
          sx={{ flex: 1 }}
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder={
            source === "greenhouse"
              ? "e.g. boschglobalsof"
              : "e.g. google"
          }
        />
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || !token.trim()}
          startIcon={
            loading ? <CircularProgress size={20} color="inherit" : undefined}
          }
        >
          {loading ? "Crawling..." : "Crawl"}
        </Button>
      </Box>

      <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
        <Button
          variant="outlined"
          color="secondary"
          onClick={onCrawlAll}
          disabled={crawlAllLoading}
          startIcon={
            crawlAllLoading ? (
              <CircularProgress size={20} color="inherit" />
            ) : undefined
          }
        >
          {crawlAllLoading ? "Crawling All..." : "Crawl All"}
        </Button>
        {resultEntries && resultEntries.length > 0 && (
          <Typography variant="body2" color="text.secondary">
            {resultEntries.map(([company, count]) => (
              <span key={company} style={{ marginRight: 12 }}>
                {company}: {count}
              </span>
            ))}
          </Typography>
        )}
      </Box>
    </Box>
  );
}


