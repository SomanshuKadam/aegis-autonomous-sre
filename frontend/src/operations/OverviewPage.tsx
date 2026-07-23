import { useEffect, useState } from "react";
import { api } from "../api/client";

export function OverviewPage() {
  const [status, setStatus] = useState("Checking");
  useEffect(() => { api<{status: string}>("/health").then((value) => setStatus(value.status)).catch(() => setStatus("unavailable")); }, []);
  return <main><h1>Aegis Operations</h1><p>Application health: {status}</p><p>This surface intentionally exposes observation only. Remediation controls are restricted to authenticated operators.</p></main>;
}
