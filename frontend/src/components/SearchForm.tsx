import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

interface SearchFormProps {
  onSearch: (resumeText: string, topK: number) => Promise<void>;
  loading: boolean;
}

export default function SearchForm({ onSearch, loading }: SearchFormProps) {
  const [resumeText, setResumeText] = useState("");
  const [topK, setTopK] = useState(10);

  const handleSubmit = () => {
    if (!resumeText.trim()) return;
    onSearch(resumeText.trim(), topK);
  };

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
        Search Jobs
      </Typography>
      <TextField
        label="Resume / Profile Text"
        multiline
        minRows={4}
        fullWidth
        value={resumeText}
        onChange={(e) => setResumeText(e.target.value)}
        placeholder="Paste your resume or profile text here..."
        sx={{ mb: 2 }}
      />
      <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
        <TextField
          label="Top K"
          type="number"
          size="small"
          sx={{ width: 100 }}
          value={topK}
          onChange={(e) =>
            setTopK(Math.max(1, Math.min(100, Number(e.target.value))))
          }
          slotProps={{ htmlInput: { min: 1, max: 100 } }}
        />
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || !resumeText.trim()}
          startIcon={
            loading ? <CircularProgress size={20} color="inherit" /> : undefined
          }
        >
          {loading ? "Searching..." : "Search"}
        </Button>
      </Box>
    </Box>
  );
}
