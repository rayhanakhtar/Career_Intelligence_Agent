import { useRef, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

interface SearchFormProps {
  onSearch: (
    resumeText: string,
    topK: number,
    locations?: string[]
  ) => Promise<void>;
  onSearchFile: (
    file: File,
    topK: number,
    locations?: string[]
  ) => Promise<void>;
  loading: boolean;
}

export default function SearchForm({
  onSearch,
  onSearchFile,
  loading,
}: SearchFormProps) {
  const [resumeText, setResumeText] = useState("");
  const [locationsText, setLocationsText] = useState("");
  const [topK, setTopK] = useState(10);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const locs = locationsText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const locations = locs.length > 0 ? locs : undefined;

    if (selectedFile) {
      onSearchFile(selectedFile, topK, locations);
    } else if (resumeText.trim()) {
      onSearch(resumeText.trim(), topK, locations);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
  };

  const canSubmit =
    !loading && (!!selectedFile || !!resumeText.trim());

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
        disabled={!!selectedFile}
        sx={{ mb: 2 }}
      />

      <Box sx={{ display: "flex", gap: 2, alignItems: "center", mb: 2 }}>
        <Button
          variant="outlined"
          component="label"
          size="small"
          color={selectedFile ? "success" : "primary"}
        >
          {selectedFile ? selectedFile.name : "Upload Resume (PDF/DOCX/TXT)"}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            hidden
            onChange={handleFileChange}
          />
        </Button>
        {selectedFile && (
          <Button
            size="small"
            color="error"
            onClick={() => {
              setSelectedFile(null);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
          >
            Clear
          </Button>
        )}
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
        <TextField
          label="Preferred Locations"
          size="small"
          sx={{ flex: 1 }}
          value={locationsText}
          onChange={(e) => setLocationsText(e.target.value)}
          placeholder="Bengaluru, Electronic City, Whitefield"
          helperText="Comma-separated — matching jobs get boosted"
        />
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
      </Box>

      <Button
        variant="contained"
        onClick={handleSubmit}
        disabled={!canSubmit}
        startIcon={
          loading ? <CircularProgress size={20} color="inherit" /> : undefined
        }
      >
        {loading ? "Searching..." : "Search"}
      </Button>
    </Box>
  );
}
