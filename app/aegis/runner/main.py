from fastapi import FastAPI

app = FastAPI(title="Aegis Restricted Runner")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-runner"}
