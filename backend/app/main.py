from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.db.session import Base, engine
from app.api.chat import router as chat_router
from app.core.limiter import limiter

from app.api.analytics import router as analytics_router
from app.api.gdpr import router as gdpr_router

import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.metrics import REQ_COUNT, REQ_LATENCY
app = FastAPI(title="Assistant Virtuel Campus", version="1.0.0")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)

    path = request.url.path
    method = request.method
    status = str(response.status_code)

    REQ_COUNT.labels(method=method, path=path, status=status).inc()
    REQ_LATENCY.labels(method=method, path=path).observe(time.time() - start)

    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(gdpr_router)
