"""WhatsApp Cloud API Webhook router with secure token verification."""
from __future__ import annotations

import httpx
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Query, HTTPException, Response, BackgroundTasks

from src.Workflow.workflow import workflow
from src.agents.retriver_agent import clean_llm_response
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("whatsapp_webhook")

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Webhook"])

async def send_whatsapp_message(to_number: str, body_text: str) -> None:
    """Sends a text message reply via Meta WhatsApp Cloud API."""
    if not settings.WHATSAPP_TOKEN or not settings.PHONE_NUMBER_ID:
        logger.warning("WhatsApp API token or Phone Number ID not configured. Skipping outbound message.")
        return

    url = f"https://graph.facebook.com/v19.0/{settings.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body_text[:4096]},  # Meta limit is 4096 chars
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.error(f"WhatsApp API outbound error {resp.status_code}: {resp.text}")
            else:
                logger.info(f"WhatsApp reply successfully dispatched to {to_number}")
    except Exception as e:
        logger.error(f"Failed to deliver WhatsApp message to {to_number}: {e}", exc_info=True)

@router.get("/webhook")
def verify_whatsapp(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """WhatsApp Webhook verification challenge (GET)."""
    expected_token = settings.WHATSAPP_VERIFY_TOKEN
    logger.info("Received WhatsApp webhook verification request")

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("WhatsApp webhook challenge verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("WhatsApp verification failed: token mismatch or invalid mode")
    raise HTTPException(status_code=403, detail="Invalid verification credentials")

def _process_whatsapp_inbound(sender: str, user_text: str) -> None:
    """Processes inbound WhatsApp query and dispatches response in threadpool without blocking event loop."""
    logger.info(f"Processing WhatsApp message from {sender}: '{user_text[:50]}...'")
    initial_state = {
        "user_query": user_text,
        "query_response": "",
        "evaluation_state": "",
        "retry_count": 0,
        "instruction": ""
    }

    try:
        final_state = workflow.invoke(initial_state)
        raw_output = final_state.get("query_response", "I could not generate an answer at this time.")
        answer = clean_llm_response(raw_output)
    except Exception as e:
        logger.error(f"Error generating answer for WhatsApp: {e}", exc_info=True)
        answer = "Sorry, an internal error occurred while retrieving information."

    if settings.WHATSAPP_TOKEN and settings.PHONE_NUMBER_ID:
        try:
            url = f"https://graph.facebook.com/v19.0/{settings.PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": sender,
                "type": "text",
                "text": {"body": answer[:4096]},
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    logger.error(f"WhatsApp API outbound error {resp.status_code}: {resp.text}")
                else:
                    logger.info(f"WhatsApp reply successfully dispatched to {sender}")
        except Exception as e:
            logger.error(f"Failed to deliver WhatsApp message to {sender}: {e}")


@router.post("/webhook")
async def receive_whatsapp(request: Request, background_tasks: BackgroundTasks):
    """WhatsApp inbound message receiver (POST). Acknowledges immediately with HTTP 200."""
    try:
        data = await request.json()
    except Exception:
        return Response(status_code=200)

    # Immediately acknowledge webhook to avoid Meta retry storms
    entry = data.get("entry", [])
    if not entry:
        return Response(status_code=200)

    changes = entry[0].get("changes", [])
    if not changes:
        return Response(status_code=200)

    value = changes[0].get("value", {})
    messages = value.get("messages")
    if not messages:
        return Response(status_code=200)

    msg = messages[0]
    sender = msg.get("from")
    mtype = msg.get("type")

    user_text = None
    if mtype == "text":
        user_text = msg.get("text", {}).get("body")
    elif mtype == "button":
        user_text = msg.get("button", {}).get("text")
    elif mtype == "interactive":
        interactive = msg.get("interactive", {})
        itype = interactive.get("type")
        if itype == "button_reply":
            user_text = interactive.get("button_reply", {}).get("title")
        elif itype == "list_reply":
            user_text = interactive.get("list_reply", {}).get("title")

    if not user_text or not sender:
        return Response(status_code=200)

    # Schedule RAG inference and response in background to prevent webhook timeout
    background_tasks.add_task(_process_whatsapp_inbound, sender, user_text)
    return Response(status_code=200)
