from fastapi import FastAPI


app = FastAPI(
    title="IT Navigator API",
    description="Backend for helping beginners choose a suitable IT direction.",
    version="0.1.0",
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {
        "message": "IT Navigator backend ishlayapti",
        "status": "ok",
    }
