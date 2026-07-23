import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

type Incident = { incident_id: string; category: string; state: string };

export function IncidentListPage() {
  const [items, setItems] = useState<Incident[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<{items: Incident[]}>("/operations/incidents").then((value) => setItems(value.items)).catch((reason: Error) => setError(reason.message)); }, []);
  return <main><h1>Incidents</h1>{error && <p role="alert">{error}</p>}<ul>{items.map((item) => <li key={item.incident_id}><Link to={`/ops/incidents/${item.incident_id}`}>{item.category}</Link> <span>{item.state}</span></li>)}</ul></main>;
}
