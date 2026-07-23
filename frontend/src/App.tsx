import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { ShopPage } from "./customer/ShopPage";
import { OverviewPage } from "./operations/OverviewPage";
import { IncidentListPage } from "./operations/IncidentListPage";
import { IncidentDetailPage } from "./operations/IncidentDetailPage";

type Readiness = {
  database: string;
  collection: string;
  field: string;
  index_present: boolean;
};

type SearchResult = {
  query: string;
  result: { searchField: string; payload: string };
  index_present: boolean;
  latency_ms: number;
  trace_id: string;
};

const phases = ["Trigger", "Analysis", "Remediation", "Resolution"];

function LegacyScenario() {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    const response = await fetch("/api/readiness/remediation");
    if (!response.ok) throw new Error(`Readiness failed: ${response.status}`);
    setReadiness((await response.json()) as Readiness);
  }, []);

  useEffect(() => {
    refresh().catch((reason: Error) => setError(reason.message));
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  async function runScenario() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/search?q=needle");
      if (!response.ok) throw new Error(`Search failed: ${response.status}`);
      const data = (await response.json()) as SearchResult;
      setResult(data);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unknown request failure");
    } finally {
      setLoading(false);
    }
  }

  const degraded = readiness?.index_present === false;
  const latencyState = result ? (result.latency_ms > 2000 ? "critical" : "healthy") : "idle";

  return (
    <main>
      <header>
        <div className="brand-mark">A</div>
        <div>
          <p className="eyebrow">AUTONOMOUS SRE PIPELINE</p>
          <h1>Aegis Operations Console</h1>
        </div>
        <span className={`status ${degraded ? "critical" : "healthy"}`}>
          <i /> {readiness ? (degraded ? "Index missing" : "Protected") : "Connecting"}
        </span>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">CLOSED-LOOP REMEDIATION</p>
          <h2>Observe. Diagnose. Repair. Verify.</h2>
          <p className="lede">
            Generate a traced database request and watch Aegis turn telemetry into a bounded,
            verified MongoDB remediation.
          </p>
          <button onClick={runScenario} disabled={loading}>
            {loading ? "Running traced request…" : "Generate latency scenario"}
          </button>
        </div>
        <div className="metric-card">
          <span>Latest request</span>
          <strong className={latencyState}>{result ? `${result.latency_ms.toFixed(0)} ms` : "—"}</strong>
          <small>P95 objective &lt; 2,000 ms</small>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="grid">
        <article>
          <div className="card-title"><span>01</span><h3>Target state</h3></div>
          <dl>
            <div><dt>Database</dt><dd>{readiness?.database ?? "—"}</dd></div>
            <div><dt>Collection</dt><dd>{readiness?.collection ?? "—"}</dd></div>
            <div><dt>Index field</dt><dd>{readiness?.field ?? "—"}</dd></div>
            <div><dt>Index status</dt><dd>{readiness?.index_present ? "searchField_1 present" : "missing"}</dd></div>
          </dl>
        </article>

        <article>
          <div className="card-title"><span>02</span><h3>Trace evidence</h3></div>
          <dl>
            <div><dt>Trace ID</dt><dd className="trace">{result?.trace_id || "Run a scenario"}</dd></div>
            <div><dt>Query</dt><dd>{result?.query ?? "—"}</dd></div>
            <div><dt>Plan signal</dt><dd>{result ? (result.index_present ? "Indexed lookup" : "Collection scan") : "—"}</dd></div>
          </dl>
        </article>
      </section>

      <section className="pipeline">
        <p className="eyebrow">SLACK OPERATIONS TIMELINE</p>
        <div className="phases">
          {phases.map((phase, index) => (
            <div key={phase}>
              <b>{String(index + 1).padStart(2, "0")}</b>
              <span>{phase}</span>
              <small>{["Alert accepted", "Trace inspected", "Index created", "Latency verified"][index]}</small>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

export default function App() {
  return <BrowserRouter><nav><Link to="/shop">Shop</Link> | <Link to="/ops">Operations</Link></nav><Routes><Route path="/shop" element={<ShopPage />} /><Route path="/ops" element={<OverviewPage />} /><Route path="/ops/incidents" element={<IncidentListPage />} /><Route path="/ops/incidents/:incidentId" element={<IncidentDetailPage />} /><Route path="*" element={<LegacyScenario />} /></Routes></BrowserRouter>;
}
