from fastapi import FastAPI

app = FastAPI(title="Aegis Workload")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-workload"}
