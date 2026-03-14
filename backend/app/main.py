from fastapi import FastAPI

app = FastAPI(title="SelfPace", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "selfpace", "version": "0.1.0"}
