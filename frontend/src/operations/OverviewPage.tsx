import { useEffect, useState } from "react";
import { api } from "../api/client";

export function OverviewPage() {
  const [status, setStatus] = useState("Checking");
  const [incidents, setIncidents] = useState<{incident_id: string; category: string; state: string}[]>([]);
  useEffect(() => { api<{status: string}>("/health").then((value) => setStatus(value.status)).catch(() => setStatus("unavailable")); api<{items: {incident_id: string; category: string; state: string}[]}>("/orchestration/incidents").then((value) => setIncidents(value.items)).catch(() => undefined); }, []);
  return <main><h1>Aegis Operations</h1><p>Application health: {status}</p><h2>Incidents</h2><ul>{incidents.map((incident) => <li key={incident.incident_id}>{incident.category}: {incident.state}</li>)}</ul><p>This surface intentionally exposes observation only. Remediation controls are restricted to authenticated operators.</p></main>;
}
