from fastapi import FastAPI

app = FastAPI(title="Aegis Inventory")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-inventory"}
