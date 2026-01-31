"""
Eternal Memory System - Main Engine Implementation

Integrates all pipelines into a unified system that implements
the EternalMemoryEngine abstract base class.
"""

from typing import Literal, Optional, List

from eternal_memory.config import MemoryConfig, load_config
from eternal_memory.database.repository import MemoryRepository
from eternal_memory.database.schema import DatabaseSchema
from eternal_memory.engine.base import EternalMemoryEngine
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import Category, MemoryItem
from eternal_memory.models.retrieval import RetrievalResult
from eternal_memory.models.retrieval import RetrievalResult
from eternal_memory.pipelines.consolidate import ConsolidatePipeline
from eternal_memory.pipelines.memorize import MemorizePipeline
from eternal_memory.pipelines.flush import FlushPipeline
from eternal_memory.pipelines.predict import PredictPipeline
from eternal_memory.pipelines.retrieve import RetrievePipeline
from eternal_memory.scheduling.scheduler import CronScheduler
from eternal_memory.scheduling.jobs import job_daily_reflection, job_maintenance, get_job_function
from eternal_memory.scheduling.jobs import job_daily_reflection, job_maintenance, get_job_function
from eternal_memory.vault.markdown_vault import MarkdownVault


class EternalMemorySystem(EternalMemoryEngine):
    """
    Main implementation of the Eternal Memory System.
    
    Provides the four core capabilities:
    1. memorize() - Store new memories
    2. retrieve() - Recall memories (fast/deep modes)
    3. consolidate() - Maintain and archive
    4. predict_context() - Proactive context generation
    4. predict_context() - Proactive context generation
    5. buffer_and_flush() - Manage conversation buffer and periodic flush
    6. cron - Automated background tasks (Daily Reflection, Maintenance)
    
    Usage:
        memory = EternalMemorySystem()
        await memory.initialize()
        
        # Store a memory
        item = await memory.memorize("User prefers TypeScript over Python")
        
        # Retrieve memories
        result = await memory.retrieve("programming language preferences")
        
        # Cleanup
        await memory.close()
    """
    
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        vault_path: Optional[str] = None,
    ):
        """
        Initialize the memory system.
        
        Args:
            config: Configuration object. Loads from ~/.openclaw/config if not provided.
            vault_path: Path to markdown vault. Uses ~/.openclaw if not provided.
        """
        self.config = config or load_config()
        
        # Initialize components
        self.schema = DatabaseSchema(self.config.database.connection_string)
        self.repository = MemoryRepository(self.config.database.connection_string)
        self.vault = MarkdownVault(vault_path)
        self.llm = LLMClient(
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            usage_callback=self.repository.record_token_usage,
        )
        
        # Initialize pipelines
        self._memorize_pipeline: Optional[MemorizePipeline] = None
        self._retrieve_pipeline: Optional[RetrievePipeline] = None
        self._consolidate_pipeline: Optional[ConsolidatePipeline] = None
        self._predict_pipeline: Optional[PredictPipeline] = None
        self._flush_pipeline: Optional[FlushPipeline] = None
        
        # Conversation buffer state
        self.conversation_buffer: list[dict] = []
        # Conversation buffer state
        self.conversation_buffer: list[dict] = []
        self.FLUSH_THRESHOLD_TOKENS = 1000  # Reasonable threshold for production
        
        # Scheduler
        self.scheduler = CronScheduler()
        
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize all system components.
        
        - Creates database schema
        - Sets up markdown vault directories
        - Initializes connection pools
        """
        if self._initialized:
            return
        
        # Initialize database schema
        await self.schema.initialize()
        
        # Connect to database
        await self.repository.connect()
        
        # Initialize vault
        await self.vault.initialize()
        
        # Ensure standard root categories exist
        standard_roots = [
            ("Knowledge", "knowledge", "General facts and information"),
            ("Personal", "personal", "Personal preferences, feelings, and lifestyle"),
            ("Projects", "projects", "Work, code, and side projects"),
            ("Preferences", "preferences", "User-specific settings and preferences"),
        ]
        
        for name, path, desc in standard_roots:
            # We don't use MemorizePipeline here to avoid circular dependencies or extra LLM calls
            # Just a simple ensure logic
            existing = await self.repository.get_category_by_path(path)
            if not existing:
                emb = await self.llm.generate_embedding(name)
                cat = Category(name=name, path=path, description=desc)
                await self.repository.create_category(cat, embedding=emb)
                await self.vault.ensure_category_file(path)
        
        # Initialize pipelines
        self._memorize_pipeline = MemorizePipeline(
            repository=self.repository,
            llm_client=self.llm,
            vault=self.vault,
        )
        
        self._retrieve_pipeline = RetrievePipeline(
            repository=self.repository,
            llm_client=self.llm,
            vault=self.vault,
        )
        
        self._consolidate_pipeline = ConsolidatePipeline(
            repository=self.repository,
            llm_client=self.llm,
            vault=self.vault,
            stale_days_threshold=self.config.retention.stale_days_threshold,
            max_category_items=100,
        )
        
        self._predict_pipeline = PredictPipeline(
            repository=self.repository,
            llm_client=self.llm,
            vault=self.vault,
        )
        
        self._flush_pipeline = FlushPipeline(
            repository=self.repository,
            llm_client=self.llm,
            vault=self.vault,
            memorize_pipeline=self._memorize_pipeline,
        )
        
        self._flush_pipeline = FlushPipeline(
            repository=self.repository,
            llm_client=self.llm,
            vault=self.vault,
            memorize_pipeline=self._memorize_pipeline,
        )
        
        # Register standard cron jobs
        # Daily Reflection (every 24h = 86400s)
        self.scheduler.add_job(
            name="daily_reflection",
            interval_seconds=86400,
            func=lambda: job_daily_reflection(self),
            job_type="daily_reflection",
            is_system=True,
        )
        
        # Maintenance/Consolidation (every 12h = 43200s)
        self.scheduler.add_job(
            name="maintenance", 
            interval_seconds=43200, 
            func=lambda: job_maintenance(self),
            job_type="maintenance",
            is_system=True,
        )
        
        # Save system jobs to DB (so they appear in the UI)
        await self.repository.save_scheduled_task(
            name="daily_reflection",
            job_type="daily_reflection",
            interval_seconds=86400,
            enabled=True,
            is_system=True,
        )
        await self.repository.save_scheduled_task(
            name="maintenance",
            job_type="maintenance",
            interval_seconds=43200,
            enabled=True,
            is_system=True,
        )
        await self.repository.save_scheduled_task(
            name="weekly_summary",
            job_type="weekly_summary",
            interval_seconds=604800,  # 7 days
            enabled=True,
            is_system=True,
        )
        await self.repository.save_scheduled_task(
            name="monthly_summary",
            job_type="monthly_summary",
            interval_seconds=2592000,  # 30 days
            enabled=True,
            is_system=True,
        )
        
        # Load any custom jobs from DB
        await self._load_custom_jobs_from_db()
        
        # Start the scheduler
        await self.scheduler.start()
        
        self._initialized = True
    
    async def close(self) -> None:
        """Close all connections and cleanup."""
        if self.scheduler:
            await self.scheduler.stop()
            
        if self.repository:
            await self.repository.disconnect()
        self._initialized = False
    
    async def _load_custom_jobs_from_db(self) -> None:
        """Load custom jobs from database and register them with the scheduler."""
        try:
            tasks = await self.repository.get_scheduled_tasks()
            for task in tasks:
                # Skip system tasks (already registered)
                if task["is_system"]:
                    continue
                
                # Skip already registered jobs
                if task["name"] in [j["name"] for j in self.scheduler.get_jobs()]:
                    continue
                
                # Get the job function
                job_func = get_job_function(task["job_type"])
                if job_func is None:
                    continue
                
                # Register the job
                self.scheduler.add_job(
                    name=task["name"],
                    interval_seconds=task["interval_seconds"],
                    func=lambda f=job_func: f(self),
                    job_type=task["job_type"],
                    is_system=False,
                )
        except Exception as e:
            # Log but don't fail startup
            print(f"Warning: Failed to load custom jobs from DB: {e}")
    
    async def memorize(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        Store new information as memory.
        
        Implements the memorize pipeline:
        1. Extract salient facts from text via LLM
        2. Assign to existing or new category
        3. Save to Vector DB with embedding
        4. Append to corresponding Markdown file
        
        Args:
            text: Input text to memorize
            metadata: Optional metadata (sender, app context, etc.)
            
        Returns:
            The primary created MemoryItem (first extracted fact)
        """
        if not self._initialized:
            await self.initialize()
        
        items = await self._memorize_pipeline.execute(text, metadata)
        
        # Return the first item, or create a placeholder if none extracted
        if items:
            return items[0]
        else:
            # No facts were extracted, but we logged it
            return MemoryItem(
                content=f"[Logged] {text[:100]}...",
                category_path="timeline",
                type="fact",
            )

    async def save_fact(
        self,
        content: str,
        metadata: Optional[dict] = None,
        importance: float = 0.5,
    ) -> MemoryItem:
        """Store a single fact directly."""
        if not self._initialized:
            await self.initialize()
            
        return await self._memorize_pipeline.store_single_memory(
            content=content,
            metadata=metadata,
            importance=importance,
        )
    
    async def retrieve(
        self,
        query: str,
        mode: Literal["fast", "deep"] = "fast",
    ) -> RetrievalResult:
        """
        Recall memories based on query.
        
        Implements dual-mode retrieval:
        - 'fast': Vector similarity search + Keyword search (RAG mode)
        - 'deep': LLM reads summaries → Opens Markdown → Reasons answer
        
        Args:
            query: Search query
            mode: Retrieval mode ('fast' or 'deep')
            
        Returns:
            RetrievalResult with matching items and context
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._retrieve_pipeline.execute(query, mode)
    
    async def consolidate(self) -> None:
        """
        Optimize and archive memories.
        
        Implements the maintenance pipeline:
        1. Scan for rarely accessed items
        2. Summarize them into 'archived' files
        3. Re-cluster categories if too large
        """
        if not self._initialized:
            await self.initialize()
        
        await self._consolidate_pipeline.execute()
    
    async def predict_context(
        self,
        current_context: dict,
    ) -> str:
        """
        Generate context string for system prompt injection.
        
        Based on current time, open apps, recent patterns, etc.
        
        Args:
            current_context: Dictionary with current state info
            
        Returns:
            Context string for proactive injection
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._predict_pipeline.execute(current_context)
    
    async def add_to_buffer(self, role: str, content: str) -> None:
        """Add message to conversation buffer."""
        self.conversation_buffer.append({"role": role, "content": content})
        
    async def check_and_flush(self) -> List[MemoryItem]:
        """
        Check if buffer size exceeds threshold and flush if needed.
        
        Returns:
            List of created MemoryItems (if flush occurred)
        """
        if not self._initialized:
            await self.initialize()
            
        # Simple estimation: 1 token ~= 4 chars (rough English avg)
        # For mixed Korean/English, 1 char might be closer to 1 token or more
        # We use a conservative estimate: len(content) / 2
        total_chars = sum(len(m["content"]) for m in self.conversation_buffer)
        estimated_tokens = total_chars / 2
        
        if estimated_tokens < self.FLUSH_THRESHOLD_TOKENS:
            return []
            
        return await self.flush_buffer()
        
    async def flush_buffer(self) -> List[MemoryItem]:
        """Force flush the current buffer to permanent memory."""
        if not self._initialized:
            await self.initialize()
            
        if not self.conversation_buffer:
            return []
            
        print(f"🔄 Flushing memory buffer ({len(self.conversation_buffer)} messages)...")
        
        # Execute flush pipeline
        items = await self._flush_pipeline.execute(self.conversation_buffer)
        
        # Clear buffer after successful flush
        self.conversation_buffer = []
        
        return items

    async def get_stats(self) -> dict:
        """
        Get system statistics.
        
        Returns:
            Dictionary with counts of resources, categories, and memory items
        """
        if not self._initialized:
            await self.initialize()
        
        return await self.schema.get_stats()

    async def reset_system(self) -> None:
        """
        Wipe all data from the database and markdown vault.
        USE WITH CAUTION - this destroys all data.
        """
        if not self._initialized:
            await self.initialize()
            
        print("🚨 Resetting Eternal Memory System...")
        
        # 1. Drop and recreate database schema
        # We need to disconnect repository first to close any active transactions
        await self.repository.disconnect()
        await self.schema.drop_all()
        
        # 2. Clear Markdown vault
        await self.vault.clear()
        
        # 3. Re-initialize everything
        self._initialized = False
        await self.initialize()
        print("✅ System reset complete.")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
