import json
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
from app.core.llm.llm_provider import (
    GeminiProvider,
    LLMConfigurationError,
    LLMProviderError,
    LLMResponseError,
)
from app.db.session import Base, get_db
from app.models.chat import Conversation
from app.models.memory import Memory
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import MessageCreate
from app.services.chat_service import ChatService


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, response_text="Gemini says hello.", fail=False):
        self.response_text = response_text
        self.fail = fail
        self.calls = []

    async def generate_content(self, **kwargs):
        if self.fail:
            raise RuntimeError("provider exploded")
        self.calls.append(kwargs)
        return FakeResponse(self.response_text)

    async def generate_content_stream(self, **kwargs):
        if self.fail:
            raise RuntimeError("provider exploded")
        self.calls.append(kwargs)

        async def iterator():
            for chunk in ["Gemini ", "stream"]:
                yield FakeResponse(chunk)

        return iterator()


class FakeAioClient:
    def __init__(self, models):
        self.models = models


class FakeClient:
    def __init__(self, *, api_key, models=None):
        self.api_key = api_key
        self.models = models or FakeModels()
        self.aio = FakeAioClient(self.models)


class CapturingProvider:
    def __init__(self, chunks):
        self.chunks = chunks
        self.prompts = []
        self.system_prompts = []

    def estimate_tokens(self, text):
        return len(text) // 4

    async def generate(self, prompt, system_prompt=None):
        return "".join(self.chunks)

    async def extract_json(self, prompt, system_prompt=None):
        return {"memories": []}

    async def stream_generate(self, prompt, system_prompt=None):
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
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
def chat_dataset(sqlite_session_factory):
    db = sqlite_session_factory()
    try:
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            supabase_user_id=uuid.uuid4(),
            email="phase3@example.test",
            full_name="Phase Three",
        )
        conversation = Conversation(user_id=user_id, title="Gemini chat")
        memory = Memory(
            user_id=user_id,
            conversation=conversation,
            content="User prefers careful, grounded answers.",
            memory_type="PREFERENCE",
            importance=0.9,
            confidence=0.95,
            tags=["preference"],
            source="test",
            memory_metadata={"test": True},
        )
        db.add_all([user, conversation, memory])
        db.commit()
        db.refresh(user)
        db.refresh(conversation)
        return {
            "user": user,
            "conversation": conversation,
            "memory": memory,
        }
    finally:
        db.close()


@pytest.mark.anyio
async def test_gemini_provider_initialization_and_mocked_generation():
    models = FakeModels(response_text="Real provider path, mocked response.")
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-test",
        client_factory=lambda **kwargs: FakeClient(models=models, **kwargs),
    )

    text = await provider.generate("hello", system_prompt="system")

    assert text == "Real provider path, mocked response."
    assert models.calls[0]["model"] == "gemini-test"
    assert models.calls[0]["contents"] == "hello"


@pytest.mark.anyio
async def test_gemini_provider_missing_api_key_fails_clearly():
    provider = GeminiProvider(api_key="", client_factory=lambda **kwargs: FakeClient(**kwargs))

    with pytest.raises(LLMConfigurationError):
        await provider.generate("hello")


@pytest.mark.anyio
async def test_gemini_provider_failure_is_controlled():
    provider = GeminiProvider(
        api_key="test-key",
        client_factory=lambda **kwargs: FakeClient(models=FakeModels(fail=True), **kwargs),
    )

    with pytest.raises(LLMProviderError):
        await provider.generate("hello")


@pytest.mark.anyio
async def test_gemini_provider_malformed_json_is_controlled():
    provider = GeminiProvider(
        api_key="test-key",
        client_factory=lambda **kwargs: FakeClient(models=FakeModels("not json"), **kwargs),
    )

    with pytest.raises(LLMResponseError):
        await provider.extract_json("extract")


@pytest.mark.anyio
async def test_chat_service_uses_llm_prompt_and_persists_messages(
    monkeypatch,
    sqlite_session_factory,
    chat_dataset,
):
    from app.core.llm.llm_provider import LLMFactory
    import app.db.session as db_session_module

    provider = CapturingProvider(["Gemini ", "answer."])
    monkeypatch.setattr(LLMFactory, "get_provider", staticmethod(lambda: provider))
    monkeypatch.setattr(db_session_module, "SessionLocal", sqlite_session_factory)

    db = sqlite_session_factory()
    try:
        user = db.merge(chat_dataset["user"])
        conversation = db.merge(chat_dataset["conversation"])
        service = ChatService(ChatRepository(db))

        class BackgroundTasks:
            def add_task(self, *args, **kwargs):
                return None

        events = [
            event
            async for event in service.stream_assistant_response(
                user,
                conversation.id,
                MessageCreate(role="user", content="Please remember my preference."),
                BackgroundTasks(),
            )
        ]

        assert any('"delta": "Gemini "' in event for event in events)
        assert any('"done": true' in event for event in events)
        assert provider.system_prompts == ["You are VAJRA, an AI companion."]
        assert "Relevant User Memories" in provider.prompts[0]
        assert "User prefers careful, grounded answers." in provider.prompts[0]

        messages = service.list_messages(user, conversation.id)
        assert [message.role for message in messages] == ["user", "assistant"]
        assert messages[0].content == "Please remember my preference."
        assert messages[1].content == "Gemini answer."
    finally:
        db.close()


@pytest.mark.anyio
async def test_chat_service_provider_error_streams_safe_error(
    monkeypatch,
    sqlite_session_factory,
    chat_dataset,
):
    from app.core.llm.llm_provider import LLMFactory
    import app.db.session as db_session_module

    class FailingProvider(CapturingProvider):
        async def stream_generate(self, prompt, system_prompt=None):
            raise LLMProviderError("hidden provider details")
            yield ""

    monkeypatch.setattr(LLMFactory, "get_provider", staticmethod(lambda: FailingProvider([])))
    monkeypatch.setattr(db_session_module, "SessionLocal", sqlite_session_factory)

    db = sqlite_session_factory()
    try:
        user = db.merge(chat_dataset["user"])
        conversation = db.merge(chat_dataset["conversation"])
        service = ChatService(ChatRepository(db))

        class BackgroundTasks:
            def add_task(self, *args, **kwargs):
                return None

        events = [
            event
            async for event in service.stream_assistant_response(
                user,
                conversation.id,
                MessageCreate(role="user", content="hello"),
                BackgroundTasks(),
            )
        ]

        assert any("LLM provider unavailable" in event for event in events)
        assert not any("hidden provider details" in event for event in events)

        messages = service.list_messages(user, conversation.id)
        assert [message.role for message in messages] == ["user"]
    finally:
        db.close()


def test_authenticated_chat_stream_uses_llm_abstraction(
    monkeypatch,
    sqlite_session_factory,
    chat_dataset,
):
    import main
    from app.core.llm.llm_provider import LLMFactory
    import app.db.session as db_session_module

    provider = CapturingProvider(["API response"])
    monkeypatch.setattr(LLMFactory, "get_provider", staticmethod(lambda: provider))
    monkeypatch.setattr(db_session_module, "SessionLocal", sqlite_session_factory)

    db = sqlite_session_factory()
    user = db.merge(chat_dataset["user"])
    conversation = db.merge(chat_dataset["conversation"])
    supabase_user_id = user.supabase_user_id
    user_email = user.email
    user_full_name = user.full_name
    conversation_id = conversation.id
    db.commit()
    db.close()

    def override_db():
        db_override = sqlite_session_factory()
        try:
            yield db_override
        finally:
            db_override.close()

    main.app.dependency_overrides[get_db] = override_db
    token = jwt.encode(
        {
            "sub": str(supabase_user_id),
            "email": user_email,
            "user_metadata": {"full_name": user_full_name},
        },
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )

    try:
        client = TestClient(main.app)
        response = client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "user", "content": "Hello from API"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "API response" in response.text
    assert json.loads(response.text.split("data: ")[-1]) == {"done": True}
