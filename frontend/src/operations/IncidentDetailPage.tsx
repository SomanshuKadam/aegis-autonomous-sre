import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { SignozLinks } from "./SignozLinks";

type Detail = { incident_id: string; category: string; state: string; timeline: {state: string; at: string}[]; signoz: Record<string, {url: string | null; reason: string | null}> };

export function IncidentDetailPage() {
  const { incidentId = "" } = useParams(); const [incident, setIncident] = useState<Detail | null>(null); const [error, setError] = useState("");
  useEffect(() => { api<Detail>(`/operations/incidents/${incidentId}`).then(setIncident).catch((reason: Error) => setError(reason.message)); }, [incidentId]);
  if (error) return <main><p role="alert">{error}</p></main>;
  if (!incident) return <main><p>Loading incident</p></main>;
  return <main><h1>{incident.category}</h1><p aria-live="polite">{incident.state}</p><h2>Timeline</h2><ol>{incident.timeline.map((event, index) => <li key={index}>{event.state}</li>)}</ol><SignozLinks links={incident.signoz} /></main>;
}
