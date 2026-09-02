import asyncio
from uuid import UUID

from app.models.user import User
from app.core.llm.llm_provider import LLMFactory
from app.services.memory_pipeline.conversation_analyzer import ConversationAnalyzer
from app.services.memory_pipeline.memory_extractor import MemoryExtractionService
from app.services.memory_pipeline.memory_classifier import MemoryClassifier
from app.services.memory_pipeline.duplicate_detector import DuplicateDetector
from app.services.memory_pipeline.memory_ranker import MemoryRankingService
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.services.memory_service import memory_service
import logging

logger = logging.getLogger(__name__)

from app.db.session import SessionLocal

class MemoryPipeline:
    def __init__(self):
        self.llm = LLMFactory.get_provider()
        self.analyzer = ConversationAnalyzer(self.llm)
        self.extractor = MemoryExtractionService(self.llm)
        self.classifier = MemoryClassifier(self.llm)
        self.duplicate_detector = DuplicateDetector(self.llm)
        self.ranker = MemoryRankingService()

    async def process_message_background(self, user: User, message: str, conversation_id: UUID):
        """Runs the entire memory extraction pipeline in the background."""
        db = SessionLocal()
        try:
            # 1. Analyze if extraction is needed
            needs_extraction = await self.analyzer.needs_extraction(message)
            if not needs_extraction:
                logger.info("MemoryPipeline: Message ignored (no extractable info)")
                return

            # 2. Extract raw memories
            raw_memories = await self.extractor.extract_memories(message)
            if not raw_memories:
                logger.info("MemoryPipeline: No memories extracted.")
                return

            # 3. Process each memory
            # Note: memory_service requires db, so we need a valid db session
            existing_memories = memory_service.get_memories(db=db, user_id=user.id, limit=50)

            for raw_memory in raw_memories:
                # Classify
                classification = await self.classifier.classify(raw_memory["content"])
                raw_memory.update(classification)

                # Duplicate Detection
                action, target_id = await self.duplicate_detector.check_duplicates(raw_memory, existing_memories)

                if action == "ignore":
                    logger.info("MemoryPipeline: Duplicate found and ignored.")
                    continue

                if action == "update" and target_id:
                    # Update existing memory
                    update_data = MemoryUpdate(
                        content=raw_memory["content"],
                        importance=raw_memory["importance"],
                        confidence=raw_memory["confidence"],
                        tags=raw_memory["tags"]
                    )
                    # Convert target_id to UUID if necessary
                    memory_service.update_memory(db=db, id=UUID(target_id), obj_in=update_data, user_id=user.id)
                    logger.info("MemoryPipeline: Memory updated.")
                else:
                    # Create new memory
                    create_data = MemoryCreate(
                        content=raw_memory["content"],
                        memory_type=raw_memory["memory_type"],
                        importance=raw_memory["importance"],
                        confidence=raw_memory["confidence"],
                        tags=raw_memory["tags"],
                        conversation_id=conversation_id
                    )
                    memory_service.create_memory(db=db, obj_in=create_data, user_id=user.id)
                    logger.info("MemoryPipeline: New memory created.")

        except Exception as e:
            logger.warning("MemoryPipeline: Error processing message safely.")
        finally:
            db.close()

pipeline = MemoryPipeline()
