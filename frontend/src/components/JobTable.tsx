import type { JobWithScore } from "../types";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";

interface JobTableProps {
  jobs: JobWithScore[];
}

function scoreColor(score: number): "success" | "warning" | "error" {
  if (score >= 70) return "success";
  if (score >= 50) return "warning";
  return "error";
}

export default function JobTable({ jobs }: JobTableProps) {
  if (jobs.length === 0) {
    return (
      <Typography variant="body1" color="text.secondary" sx={{ py: 4 }}>
        No jobs found. Try crawling or adjusting your search.
      </Typography>
    );
  }

  return (
    <TableContainer component={Paper} sx={{ mt: 2 }}>
      <Table size="small" sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Match</TableCell>
            <TableCell>Company</TableCell>
            <TableCell>Title</TableCell>
            <TableCell>Location</TableCell>
            <TableCell>Apply</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {jobs.map((job, i) => (
            <TableRow key={job.id} hover>
              <TableCell>{i + 1}</TableCell>
              <TableCell>
                <Chip
                  label={`${Math.round(job.match_score)}%`}
                  color={scoreColor(job.match_score)}
                  size="small"
                />
              </TableCell>
              <TableCell>{job.company}</TableCell>
              <TableCell>{job.title}</TableCell>
              <TableCell>{job.location}</TableCell>
              <TableCell>
                <Link
                  href={job.apply_url}
                  target="_blank"
                  rel="noopener"
                  underline="hover"
                >
                  Apply
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
