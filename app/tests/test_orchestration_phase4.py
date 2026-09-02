import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./vajra_test.db")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("LLM_PROVIDER", "dummy")

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.llm.llm_provider import LLMProviderError
from app.db.session import Base, get_db
from app.models.chat import Conversation
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import MessageCreate
from app.services.chat_service import ChatService
from app.services.tools.base import ToolContext, ToolResult
from app.services.tools.executor import ToolExecutor
from app.services.tools.intent_analyzer import IntentAnalyzer
from app.services.tools.registry import tool_registry


class CapturingProvider:
    def __init__(self, chunks=None):
        self.chunks = chunks or ["ok"]
        self.prompts = []

    def estimate_tokens(self, text):
        return len(text) // 4

    async def generate(self, prompt, system_prompt=None):
        return "".join(self.chunks)

    async def extract_json(self, prompt, system_prompt=None):
        return {"memories": []}

    async def stream_generate(self, prompt, system_prompt=None):
        self.prompts.append(prompt)
        for chunk in self.chunks:
            yield chunk


@pytest.fixture()
def sqlite_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


@pytest.fixture()
def user_conversation(sqlite_session_factory):
    db = sqlite_session_factory()
    try:
        user = User(
            id=uuid.uuid4(),
            supabase_user_id=uuid.uuid4(),
            email="phase4@example.com",
            full_name="Phase Four",
        )
        conversation = Conversation(user_id=user.id, title="Phase 4")
        db.add_all([user, conversation])
        db.commit()
        db.refresh(user)
        db.refresh(conversation)
        return {"user": user, "conversation": conversation}
    finally:
        db.close()


@pytest.mark.anyio
async def test_builtin_tools_are_registered_and_safe():
    assert tool_registry.get_tool("calculator") is not None
    assert tool_registry.get_tool("current_date") is not None
    assert tool_registry.get_tool("current_time") is not None

    context = ToolContext(user_id=uuid.uuid4(), conversation_id=uuid.uuid4())
    result = await ToolExecutor.execute("calculator", context, {"expression": "2 + 3 * 4"})
    assert result.success is True
    assert result.data["result"] == 14

    missing = await ToolExecutor.execute("calculator", context, {})
    assert missing.success is False
    assert "Missing required" in missing.error

    unsupported = await ToolExecutor.execute("missing_tool", context, {})
    assert unsupported.success is False

    unsafe = await ToolExecutor.execute(
        "calculator",
        context,
        {"expression": "__import__('os').system('echo no')"},
    )
    assert unsafe.success is False


@pytest.mark.anyio
async def test_intent_analyzer_is_conservative():
    analyzer = IntentAnalyzer(CapturingProvider())

    calculation = await analyzer.analyze("calculate 7 * 8")
    assert calculation.required_tool == "calculator"

    date = await analyzer.analyze("what is the date?")
    assert date.required_tool == "current_date"

    memory = await analyzer.analyze("please remember that I like tea")
    assert memory.required_tool is None
    assert memory.intent == "Memory Related"

    unsupported = await analyzer.analyze("run a shell command")
    assert unsupported.required_tool == "unsupported"

    chat = await analyzer.analyze("tell me a calm story")
    assert chat.required_tool is None


@pytest.mark.anyio
async def test_chat_orchestration_includes_tool_results_and_persists_once(
    monkeypatch,
    sqlite_session_factory,
    user_conversation,
):
    from app.core.llm.llm_provider import LLMFactory
    import app.db.session as db_session_module

    provider = CapturingProvider(["answer"])
    monkeypatch.setattr(LLMFactory, "get_provider", staticmethod(lambda: provider))
    monkeypatch.setattr(db_session_module, "SessionLocal", sqlite_session_factory)

    db = sqlite_session_factory()
    try:
        user = db.merge(user_conversation["user"])
        conversation = db.merge(user_conversation["conversation"])
        service = ChatService(ChatRepository(db))

        class BackgroundTasks:
            def __init__(self):
                self.tasks = []

            def add_task(self, *args, **kwargs):
                self.tasks.append((args, kwargs))

        background_tasks = BackgroundTasks()
        events = [
            event
            async for event in service.stream_assistant_response(
                user,
                conversation.id,
                MessageCreate(role="user", content="calculate 6 * 7"),
                background_tasks,
            )
        ]

        assert any('"done": true' in event for event in events)
        assert "TOOL RESULTS" in provider.prompts[0]
        assert "calculator" in provider.prompts[0]
        messages = service.list_messages(user, conversation.id)
        assert [message.role for message in messages] == ["user", "assistant"]
        assert messages[1].content == "answer"
        assert messages[1].assistant_metadata["tool_used"] == "calculator"
        assert len(background_tasks.tasks) == 1
    finally:
        db.close()


@pytest.mark.anyio
async def test_failed_provider_does_not_persist_assistant_or_schedule_memory(
    monkeypatch,
    sqlite_session_factory,
    user_conversation,
):
    from app.core.llm.llm_provider import LLMFactory
    import app.db.session as db_session_module

    class FailingProvider(CapturingProvider):
        async def stream_generate(self, prompt, system_prompt=None):
            raise LLMProviderError("internal detail")
            yield ""

    monkeypatch.setattr(LLMFactory, "get_provider", staticmethod(lambda: FailingProvider()))
    monkeypatch.setattr(db_session_module, "SessionLocal", sqlite_session_factory)

    db = sqlite_session_factory()
    try:
        user = db.merge(user_conversation["user"])
        conversation = db.merge(user_conversation["conversation"])
        service = ChatService(ChatRepository(db))

        class BackgroundTasks:
            def __init__(self):
                self.tasks = []

            def add_task(self, *args, **kwargs):
                self.tasks.append((args, kwargs))

        background_tasks = BackgroundTasks()
        events = [
            event
            async for event in service.stream_assistant_response(
                user,
                conversation.id,
                MessageCreate(role="user", content="hello"),
                background_tasks,
            )
        ]

        assert any("LLM provider unavailable" in event for event in events)
        assert not any("internal detail" in event for event in events)
        assert [message.role for message in service.list_messages(user, conversation.id)] == ["user"]
        assert background_tasks.tasks == []
    finally:
        db.close()


def test_ready_and_docs_endpoints_are_available():
    import main

    client = TestClient(main.app)
    assert client.get("/ready").status_code == 200
    assert client.get("/docs").status_code == 200


def test_malformed_token_is_rejected():
    import main

    client = TestClient(main.app)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_valid_user_token_creates_profile(sqlite_session_factory):
    import main

    def override_db():
        db = sqlite_session_factory()
        try:
            yield db
        finally:
            db.close()

    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "valid-user@example.com",
            "user_metadata": {"full_name": "Valid User"},
        },
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )

    main.app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["email"] == "valid-user@example.com"
