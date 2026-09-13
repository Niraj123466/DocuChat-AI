"""Unit and integration tests for PostgreSQL/SQLite database models, ChatService, and Conversations API."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.db.models.base import Base
from src.db.models.user import User
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.document import DocumentRecord, AuditLog
from src.services.chat_service import ChatService
from src.api.app import app
from src.db.session import get_db, init_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_chat_service_crud_lifecycle(async_db: AsyncSession):
    # 0. Create user to satisfy foreign key constraint
    test_user = User(email="test.db@docuchat.ai", hashed_password="pw", name="DB User", role="user")
    async_db.add(test_user)
    await async_db.flush()

    # 1. Create conversation
    conv = await ChatService.create_conversation(async_db, title="RAG Architecture Discussion", user_id=test_user.id)
    assert conv.id is not None
    assert conv.title == "RAG Architecture Discussion"

    # 2. Record User Turn
    user_msg = await ChatService.record_message(
        async_db,
        conversation_id=conv.id,
        sender="user",
        content="What is LangGraph?",
        user_id=test_user.id
    )
    assert user_msg.id is not None
    assert user_msg.sender == "user"
    assert user_msg.content == "What is LangGraph?"

    # 3. Record Assistant Turn with Citations
    citation = {
        "doc_index": 1,
        "source": "architecture.pdf",
        "chunk_id": "chunk_12",
        "relevance_score": 0.94,
        "text_snippet": "LangGraph provides cyclic state machine graphs."
    }
    assistant_msg = await ChatService.record_message(
        async_db,
        conversation_id=conv.id,
        sender="assistant",
        content="LangGraph is an orchestration library for cyclic agent workflows.",
        citations=[citation],
        metadata={"tokens": 42},
        user_id=test_user.id
    )
    assert assistant_msg.sender == "assistant"
    assert len(assistant_msg.citations) == 1
    assert assistant_msg.citations[0]["doc_index"] == 1

    await async_db.flush()
    await async_db.refresh(conv, ["messages"])

    # 4. Fetch thread with eagerly loaded messages
    loaded = await ChatService.get_conversation(async_db, conv.id, user_id=test_user.id)
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert loaded.messages[0].sender == "user"
    assert loaded.messages[1].sender == "assistant"

    # 5. List conversations
    threads = await ChatService.list_conversations(async_db, user_id=test_user.id)
    assert len(threads) >= 1
    assert threads[0].id == conv.id

    # 6. Delete conversation
    deleted = await ChatService.delete_conversation(async_db, conv.id, user_id=test_user.id)
    assert deleted is True

    # 7. Confirm deletion
    not_found = await ChatService.get_conversation(async_db, conv.id, user_id=test_user.id)
    assert not_found is None

@pytest.mark.asyncio
async def test_conversations_api_endpoints():
    await init_db()
    from src.core.security import JWTHandler
    token = JWTHandler.create_access_token(subject="user@docuchat.ai", role="user")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a conversation
        create_res = await client.post("/api/v1/conversations", json={"title": "Integration Test Thread"}, headers=headers)
        assert create_res.status_code == 200
        conv_data = create_res.json()
        conv_id = conv_data["id"]
        assert conv_data["title"] == "Integration Test Thread"

        # List conversations
        list_res = await client.get("/api/v1/conversations", headers=headers)
        assert list_res.status_code == 200
        ids = [c["id"] for c in list_res.json()]
        assert conv_id in ids

        # Get conversation history (initially 0 messages)
        detail_res = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert detail_res.status_code == 200
        assert len(detail_res.json()["messages"]) == 0

        # Delete conversation
        del_res = await client.delete(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "success"

        # Verify 404 after deletion
        not_found_res = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert not_found_res.status_code == 404

@pytest.mark.asyncio
async def test_chat_endpoint_conversation_persistence(monkeypatch):
    await init_db()
    from src.core.security import JWTHandler
    token = JWTHandler.create_access_token(subject="user@docuchat.ai", role="user")
    headers = {"Authorization": f"Bearer {token}"}

    # Mock workflow to avoid external LLM calls during test
    from src.Workflow import workflow as wf_module
    class MockWorkflow:
        def invoke(self, state):
            return {
                "user_query": state.get("user_query"),
                "query_response": "Test generated response for persistence verification.",
                "evaluation_state": "True",
                "retry_count": 0,
                "citations": [{
                    "doc_index": 1,
                    "source": "doc.pdf",
                    "chunk_id": "c1",
                    "relevance_score": 0.95,
                    "text_snippet": "Snippet text"
                }]
            }
    monkeypatch.setattr(wf_module, "workflow", MockWorkflow())
    
    # Also patch workflow in src.api.v1.chat
    from src.api.v1 import chat as chat_module
    monkeypatch.setattr(chat_module, "workflow", MockWorkflow())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a thread
        create_res = await client.post("/api/v1/conversations", json={"title": "Thread for Chat"}, headers=headers)
        assert create_res.status_code == 200
        conv_id = create_res.json()["id"]

        # Call /api/v1/chat with conversation_id
        chat_res = await client.post("/api/v1/chat", json={
            "user_message": "Tell me about RAG chunking strategies",
            "conversation_id": conv_id
        }, headers=headers)
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert data["conversation_id"] == conv_id

        # Verify turns persisted in conversation history
        history_res = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert history_res.status_code == 200
        messages = history_res.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["sender"] == "user"
        assert "RAG chunking strategies" in messages[0]["content"]
        assert messages[1]["sender"] == "assistant"
        assert "Test generated response" in messages[1]["content"]
        assert len(messages[1]["citations"]) == 1
