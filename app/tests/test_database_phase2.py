import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./vajra_test.db")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("LLM_PROVIDER", "dummy")

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session, configure_mappers, sessionmaker

from app.core.config import settings
from app.db.types import GUID, JSONBType, StringList
from app.models.chat import Conversation, Message
from app.models.memory import Memory
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ConversationCreate, ConversationUpdate, MessageCreate
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.services.chat_service import ChatService
from app.services.memory_service import memory_service


@pytest.fixture()
def migrated_db(tmp_path):
    db_path = tmp_path / "vajra_phase2.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    previous_url = settings.DATABASE_URL
    settings.DATABASE_URL = db_url
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("script_location", "alembic")
        command.upgrade(alembic_cfg, "head")
        yield db_url
    finally:
        settings.DATABASE_URL = previous_url


@pytest.fixture()
def db_session(migrated_db):
    engine = create_engine(migrated_db, future=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def two_user_dataset(db_session: Session):
    user_repo = UserRepository(db_session)
    chat_service = ChatService(ChatRepository(db_session))

    user_a = user_repo.create(
        User(
            supabase_user_id=uuid.uuid4(),
            email="user-a@example.test",
            full_name="User A",
        )
    )
    user_b = user_repo.create(
        User(
            supabase_user_id=uuid.uuid4(),
            email="user-b@example.test",
            full_name="User B",
        )
    )

    conversation_a = chat_service.create_conversation(
        user_a,
        ConversationCreate(title="A conversation"),
    )
    conversation_b = chat_service.create_conversation(
        user_b,
        ConversationCreate(title="B conversation"),
    )

    message_a = chat_service.create_message(
        user_a,
        conversation_a.id,
        MessageCreate(role="user", content="A message"),
    )
    message_b = chat_service.create_message(
        user_b,
        conversation_b.id,
        MessageCreate(role="user", content="B message"),
    )

    memory_a = memory_service.create_memory(
        db_session,
        MemoryCreate(
            content="User A likes green tea.",
            conversation_id=conversation_a.id,
            origin_conversation_id=conversation_a.id,
            origin_message_id=message_a.id,
            memory_metadata={"owner": "a"},
        ),
        user_a.id,
    )
    memory_b = memory_service.create_memory(
        db_session,
        MemoryCreate(
            content="User B likes coffee.",
            conversation_id=conversation_b.id,
            origin_conversation_id=conversation_b.id,
            origin_message_id=message_b.id,
            memory_metadata={"owner": "b"},
        ),
        user_b.id,
    )

    return {
        "user_a": user_a,
        "user_b": user_b,
        "conversation_a": conversation_a,
        "conversation_b": conversation_b,
        "message_a": message_a,
        "message_b": message_b,
        "memory_a": memory_a,
        "memory_b": memory_b,
        "chat_service": chat_service,
    }


def assert_not_found(callable_):
    with pytest.raises(HTTPException) as exc_info:
        callable_()
    assert exc_info.value.status_code == 404


def test_alembic_migrates_empty_sqlite_database_to_head(migrated_db):
    engine = create_engine(migrated_db, future=True)
    inspector = inspect(engine)

    try:
        assert set(inspector.get_table_names()) >= {
            "alembic_version",
            "users",
            "conversations",
            "messages",
            "memories",
        }

        with engine.connect() as connection:
            revision = connection.exec_driver_sql(
                "select version_num from alembic_version"
            ).scalar_one()
        assert revision == "7a5478824875"
    finally:
        engine.dispose()


def test_migrated_schema_constraints_indexes_and_columns(migrated_db):
    engine = create_engine(migrated_db, future=True)
    inspector = inspect(engine)

    try:
        for table_name in ["users", "conversations", "messages", "memories"]:
            pk = inspector.get_pk_constraint(table_name)
            assert pk["constrained_columns"] == ["id"]

        user_uniques = inspector.get_unique_constraints("users")
        user_indexes = inspector.get_indexes("users")
        unique_columns = {
            column
            for item in [*user_uniques, *user_indexes]
            if item.get("unique")
            for column in item["column_names"]
        }
        assert {"email", "supabase_user_id"}.issubset(unique_columns)

        fk_map = {
            "conversations": {"users"},
            "messages": {"conversations"},
            "memories": {"users", "conversations", "messages"},
        }
        for table_name, expected_targets in fk_map.items():
            referred_tables = {
                fk["referred_table"] for fk in inspector.get_foreign_keys(table_name)
            }
            assert expected_targets.issubset(referred_tables)

        memory_columns = {
            column["name"]: column for column in inspector.get_columns("memories")
        }
        assert memory_columns["user_id"]["nullable"] is False
        assert memory_columns["content"]["nullable"] is False
        assert memory_columns["conversation_id"]["nullable"] is True
        assert memory_columns["origin_conversation_id"]["nullable"] is True
        assert memory_columns["origin_message_id"]["nullable"] is True

        indexed_columns = {
            column
            for index in inspector.get_indexes("memories")
            for column in index["column_names"]
        }
        assert {"user_id", "conversation_id", "memory_type", "deleted"}.issubset(
            indexed_columns
        )
    finally:
        engine.dispose()


def test_sqlalchemy_models_match_migrated_tables(migrated_db):
    engine = create_engine(migrated_db, future=True)
    inspector = inspect(engine)

    try:
        model_tables = {
            User.__tablename__: User,
            Conversation.__tablename__: Conversation,
            Message.__tablename__: Message,
            Memory.__tablename__: Memory,
        }
        for table_name, model in model_tables.items():
            migrated_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            model_columns = {column.name for column in model.__table__.columns}
            assert model_columns == migrated_columns
    finally:
        engine.dispose()


def test_postgresql_type_variants_remain_native():
    pg_dialect = postgresql.dialect()

    assert GUID().compile(dialect=pg_dialect) == "UUID"
    assert JSONBType.compile(dialect=pg_dialect) == "JSONB"
    assert StringList().compile(dialect=pg_dialect) == "VARCHAR[]"


def test_sqlite_type_variants_are_test_compatible():
    sqlite_dialect = sqlite.dialect()

    assert GUID().compile(dialect=sqlite_dialect) == "CHAR(36)"
    assert JSONBType.compile(dialect=sqlite_dialect) == "JSON"
    assert StringList().compile(dialect=sqlite_dialect) == "JSON"


def test_crud_for_users_conversations_messages_and_memories(
    db_session: Session,
    two_user_dataset,
):
    user_a = two_user_dataset["user_a"]
    conversation_a = two_user_dataset["conversation_a"]
    message_a = two_user_dataset["message_a"]
    memory_a = two_user_dataset["memory_a"]
    chat_service = two_user_dataset["chat_service"]

    user_repo = UserRepository(db_session)
    assert user_repo.get_by_email("user-a@example.test").id == user_a.id
    assert user_repo.get_by_supabase_id(str(user_a.supabase_user_id)).id == user_a.id

    fetched_conversation = chat_service.get_conversation(user_a, conversation_a.id)
    assert fetched_conversation.id == conversation_a.id

    updated_conversation = chat_service.update_conversation(
        user_a,
        conversation_a.id,
        ConversationUpdate(title="Updated A", pinned=True),
    )
    assert updated_conversation.title == "Updated A"
    assert updated_conversation.pinned is True

    messages = chat_service.list_messages(user_a, conversation_a.id)
    assert [message.id for message in messages] == [message_a.id]

    fetched_memory = memory_service.get_memory(db_session, memory_a.id, user_a.id)
    assert fetched_memory.id == memory_a.id

    updated_memory = memory_service.update_memory(
        db_session,
        memory_a.id,
        MemoryUpdate(content="User A likes jasmine tea.", favorite=True),
        user_a.id,
    )
    assert updated_memory.content == "User A likes jasmine tea."
    assert updated_memory.favorite is True

    deleted_memory = memory_service.delete_memory(db_session, memory_a.id, user_a.id)
    assert deleted_memory.deleted is True
    assert_not_found(lambda: memory_service.get_memory(db_session, memory_a.id, user_a.id))

    chat_service.delete_conversation(user_a, conversation_a.id)
    assert_not_found(lambda: chat_service.get_conversation(user_a, conversation_a.id))


def test_memory_relationships_use_distinct_conversation_foreign_keys(
    two_user_dataset,
):
    configure_mappers()

    memory_a = two_user_dataset["memory_a"]
    conversation_a = two_user_dataset["conversation_a"]
    message_a = two_user_dataset["message_a"]

    assert memory_a.conversation.id == conversation_a.id
    assert memory_a.origin_conversation.id == conversation_a.id
    assert memory_a.origin_message.id == message_a.id


def test_user_isolation_and_cross_user_direct_access_rejected(
    db_session: Session,
    two_user_dataset,
):
    user_a = two_user_dataset["user_a"]
    user_b = two_user_dataset["user_b"]
    conversation_a = two_user_dataset["conversation_a"]
    conversation_b = two_user_dataset["conversation_b"]
    message_b = two_user_dataset["message_b"]
    memory_a = two_user_dataset["memory_a"]
    memory_b = two_user_dataset["memory_b"]
    chat_service = two_user_dataset["chat_service"]

    assert [item.id for item in chat_service.list_conversations(user_a)] == [
        conversation_a.id
    ]
    assert [item.id for item in chat_service.list_conversations(user_b)] == [
        conversation_b.id
    ]
    assert [item.id for item in memory_service.get_memories(db_session, user_a.id)] == [
        memory_a.id
    ]
    assert [item.id for item in memory_service.get_memories(db_session, user_b.id)] == [
        memory_b.id
    ]

    assert_not_found(lambda: chat_service.get_conversation(user_a, conversation_b.id))
    assert_not_found(lambda: chat_service.list_messages(user_a, conversation_b.id))
    assert_not_found(lambda: memory_service.get_memory(db_session, memory_b.id, user_a.id))
    assert_not_found(lambda: memory_service.get_memory(db_session, memory_a.id, user_b.id))

    assert_not_found(
        lambda: memory_service.create_memory(
            db_session,
            MemoryCreate(
                content="Invalid cross-user conversation link.",
                conversation_id=conversation_b.id,
            ),
            user_a.id,
        )
    )
    assert_not_found(
        lambda: memory_service.create_memory(
            db_session,
            MemoryCreate(
                content="Invalid cross-user origin conversation link.",
                origin_conversation_id=conversation_b.id,
            ),
            user_a.id,
        )
    )
    assert_not_found(
        lambda: memory_service.create_memory(
            db_session,
            MemoryCreate(
                content="Invalid cross-user origin message link.",
                origin_message_id=message_b.id,
            ),
            user_a.id,
        )
    )

    own_memory = memory_service.create_memory(
        db_session,
        MemoryCreate(
            content="Valid own linked memory.",
            conversation_id=conversation_a.id,
            origin_conversation_id=conversation_a.id,
        ),
        user_a.id,
    )
    assert own_memory.user_id == user_a.id
    assert own_memory.conversation_id == conversation_a.id
    assert own_memory.origin_conversation_id == conversation_a.id
