from fastapi import FastAPI

app = FastAPI(title="Aegis Order Worker")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-worker"}
