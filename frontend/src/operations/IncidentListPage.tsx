import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

type Incident = { incident_id: string; category: string; state: string };

export function IncidentListPage() {
  const [items, setItems] = useState<Incident[]>([]); const [activeOnly, setActiveOnly] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api<{items: Incident[]}>("/operations/incidents").then((value) => setItems(value.items)).catch((reason: Error) => setError(reason.message)); }, []);
  const visible = activeOnly ? items.filter((item) => !["RESOLVED", "FAILED", "BLOCKED", "ESCALATED"].includes(item.state)) : items;
  return <main><h1>Incidents</h1><label><input type="checkbox" checked={activeOnly} onChange={(event) => setActiveOnly(event.target.checked)} /> Active only</label>{error && <p role="alert">{error}</p>}<ul>{visible.map((item) => <li key={item.incident_id}><Link to={`/ops/incidents/${item.incident_id}`}>{item.category}</Link> <span>{item.state}</span></li>)}</ul></main>;
}
