from fastapi import FastAPI
from path.to.sentry_engine import SentryEngine

app = FastAPI()
sentry = SentryEngine()

@app.post("/v1/chat/completions")
async def chat_completions(prompt: str):
    sanitized_prompt = sentry.sanitize(prompt)
    # store token to Redis and call LLM with sanitized prompt
    # return response