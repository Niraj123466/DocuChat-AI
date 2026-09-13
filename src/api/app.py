"""DocuChat-AI Enterprise API Application.

Centralized entrypoint providing API versioning, CORS middleware,
request performance instrumentation, Prometheus metrics, and backward compatibility mappings.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from src.db.session import init_db
from src.core.config import settings
from src.core.logging import get_logger
from src.core.telemetry import metrics, trace_span
from src.api.v1.router import api_v1_router
from src.api.v1.chat import chat_endpoint, ChatRequest
from src.api.v1.whatsapp import verify_whatsapp, receive_whatsapp
from src.api.v1.documents import upload_and_ingest

logger = get_logger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] mode")
    status = settings.validate_keys()
    logger.info(f"Configuration audit: Gemini={status['google_api_key']}, Pinecone={status['pinecone_api_key']}")
    try:
        await init_db()
        logger.info("Database schema initialized successfully")
    except Exception as dbe:
        logger.warning(f"Database schema initialization deferred or encountered note: {dbe}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

def create_application() -> FastAPI:
    """Builds and configures the centralized FastAPI application instance."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production RAG Chatbot Platform powered by LangGraph, Pinecone, and Gemini",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request performance & Correlation ID Middleware
    @application.middleware("http")
    async def process_time_and_tracing_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        path = request.url.path
        method = request.method
        start_time = time.perf_counter()

        with trace_span(f"HTTP {method} {path}", attributes={"http.method": method, "http.url": path, "request.id": req_id}):
            try:
                response: Response = await call_next(request)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000
                metrics.inc_counter("docuchat_requests_total", labels={"endpoint": path, "method": method, "status": "500"})
                metrics.observe_histogram("docuchat_request_latency_seconds", duration_ms / 1000.0, labels={"endpoint": path})
                logger.error(f"Unhandled server error on {method} {path}: {exc}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={
                        "type": "https://docuchat.ai/errors/internal",
                        "title": "Internal Server Error",
                        "status": 500,
                        "detail": "An unexpected error occurred during request processing.",
                        "request_id": req_id
                    },
                    headers={"X-Request-ID": req_id, "X-Process-Time": f"{duration_ms:.2f}ms"}
                )

        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics.inc_counter("docuchat_requests_total", labels={"endpoint": path, "method": method, "status": str(response.status_code)})
        metrics.observe_histogram("docuchat_request_latency_seconds", duration_ms / 1000.0, labels={"endpoint": path})

        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        response.headers["X-Request-ID"] = req_id
        return response

    # Mount Core v1 API Router
    application.include_router(api_v1_router)

    # Prometheus /metrics endpoint
    @application.get("/metrics", tags=["Observability"], response_class=PlainTextResponse)
    def prometheus_metrics():
        """Scrape endpoint for Prometheus / Grafana metrics monitoring."""
        return Response(content=metrics.generate_scrape_text(), media_type="text/plain; version=0.0.4")

    # Root landing endpoint
    @application.get("/", tags=["System"])
    def root():
        return {
            "status": "ok",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "documentation": "/docs",
            "metrics": "/metrics",
            "api_v1": "/api/v1"
        }

    # Backward compatibility routes for legacy callers
    application.add_api_route("/chatbot", chat_endpoint, methods=["POST"], include_in_schema=False)
    application.add_api_route("/webhook", verify_whatsapp, methods=["GET"], include_in_schema=False)
    application.add_api_route("/webhook", receive_whatsapp, methods=["POST"], include_in_schema=False)
    application.add_api_route("/upload", upload_and_ingest, methods=["POST"], include_in_schema=False)

    return application

app = create_application()
