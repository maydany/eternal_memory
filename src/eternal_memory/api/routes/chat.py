"""
Chat API Routes

Endpoints for memory-augmented conversation.
"""

import os
import time
from pathlib import Path
from typing import Literal, Optional

import aiofiles
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eternal_memory.api.main import get_memory_system
from eternal_memory.engine.context_pruner import ContextPruner

router = APIRouter()

SYSTEM_PROMPT_PATH = Path.cwd() / "setting" / "system_prompt.txt"


class ChatMessage(BaseModel):
    """Chat message request."""
    content: str
    metadata: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat response with memory context."""
    message: str
    memories_stored: int
    references: list[dict]
    processing_steps: list[str]


class RetrieveRequest(BaseModel):
    """Memory retrieval request."""
    query: str
    mode: Literal["fast", "deep"] = "fast"


class RetrieveResponse(BaseModel):
    """Memory retrieval response."""
    items: list[dict]
    related_categories: list[str]
    suggested_context: str
    query_evolved: Optional[str]
    mode: str
    confidence_score: float


@router.post("/memorize", response_model=dict)
async def memorize(message: ChatMessage):
    """
    Store information as memory.
    
    Extracts salient facts from the input and stores them
    in both the vector database and Markdown vault.
    """
    try:
        system = await get_memory_system()
        item = await system.memorize(message.content, message.metadata)
        
        return {
            "success": True,
            "item": {
                "id": str(item.id),
                "content": item.content,
                "category_path": item.category_path,
                "type": item.type.value if hasattr(item.type, 'value') else str(item.type),
                "importance": item.importance,
            },
            "processing_steps": [
                "Extracting facts from input...",
                "Assigning to category...",
                "Generating embedding...",
                "Saving to database...",
                "Updating Markdown vault...",
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(request: RetrieveRequest):
    """
    Retrieve memories based on query.
    
    Supports two modes:
    - fast: Vector similarity + keyword search (RAG)
    - deep: LLM reads summaries and reasons the answer
    """
    try:
        system = await get_memory_system()
        result = await system.retrieve(request.query, request.mode)
        
        return RetrieveResponse(
            items=[
                {
                    "id": str(item.id),
                    "content": item.content,
                    "category_path": item.category_path,
                    "type": item.type.value if hasattr(item.type, 'value') else str(item.type),
                    "importance": item.importance,
                    "confidence": item.confidence,
                }
                for item in result.items
            ],
            related_categories=result.related_categories,
            suggested_context=result.suggested_context,
            query_evolved=result.query_evolved,
            mode=result.retrieval_mode,
            confidence_score=result.confidence_score,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-context")
async def predict_context(context: dict):
    """
    Generate proactive context based on current situation.
    
    Analyzes patterns and predicts what information
    might be relevant for the user.
    """
    try:
        system = await get_memory_system()
        predicted = await system.predict_context(context)
        
        return {
            "context": predicted,
            "source": "predict_pipeline",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConversationRequest(BaseModel):
    """Natural conversation request."""
    message: str
    mode: Literal["fast", "deep"] = "fast"
    conversation_history: Optional[list[dict]] = None


class ConversationResponse(BaseModel):
    """Natural conversation response."""
    response: str
    memories_retrieved: list[dict]
    memories_stored: list[dict]
    processing_info: dict


from fastapi import APIRouter, HTTPException, BackgroundTasks

# ...

@router.post("/conversation", response_model=ConversationResponse)
async def conversation(request: ConversationRequest, background_tasks: BackgroundTasks):
    """
    Natural conversation with automatic memory management.
    
    This endpoint:
    1. Retrieves relevant memories based on the message
    2. Generates an LLM response with memory context
    3. Auto-memorizes important information from the conversation
    """
    import os
    from openai import AsyncOpenAI
    
    try:
        system = await get_memory_system()
        
        # Initialize process tracking
        process_steps = []
        
        # Step 1: Retrieve relevant memories
        memories_retrieved = []
        memories_stored = []
        memory_context = ""
        retrieval_categories = []
        
        step1_start = time.time()
        retrieval_status = "completed"
        retrieval_error = None
        
        try:
            result = await system.retrieve(request.message, request.mode)
            if result.items:
                memories_retrieved = [
                    {
                        "id": str(item.id),
                        "content": item.content,
                        "category_path": item.category_path,
                        "confidence": item.confidence,
                    }
                    for item in result.items
                ]
                memory_context = "\n".join([f"- {item.content}" for item in result.items])
                retrieval_categories = result.related_categories[:5] if result.related_categories else []
        except Exception as e:
            retrieval_status = "error"
            retrieval_error = str(e)
        
        step1_duration = int((time.time() - step1_start) * 1000)
        process_steps.append({
            "step": "memory_retrieval",
            "status": retrieval_status,
            "duration_ms": step1_duration,
            "details": {
                "mode": request.mode,
                "items_found": len(memories_retrieved),
                "categories_matched": retrieval_categories,
                "error": retrieval_error,
                "retrieved_items": memories_retrieved[:5],  # Show up to 5 items
            }
        })
        
        # Step 2: Context Building (System Prompt + Memory Context)
        step2_start = time.time()
        
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        client = AsyncOpenAI(api_key=api_key)
        # Load system prompt from file or use default
        system_prompt = "You are a helpful AI assistant with persistent memory.\nYou remember information about the user across conversations.\nWhen the user shares personal information, acknowledge it warmly and remember it.\nWhen you have relevant memories, use them naturally in your responses.\n\nImportant: Always respond in the same language the user uses."
        if SYSTEM_PROMPT_PATH.exists():
            try:
                async with aiofiles.open(SYSTEM_PROMPT_PATH, "r") as f:
                    custom_prompt = await f.read()
                    if custom_prompt.strip():
                        system_prompt = custom_prompt.strip()
            except Exception:
                pass  # Use default if file read fails
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add memory context if available
        if memory_context:
            messages.append({
                "role": "system", 
                "content": f"Relevant memories about this user:\n{memory_context}"
            })
        
        # Add conversation history if provided
        history_count = 0
        if request.conversation_history:
            history_count = min(len(request.conversation_history), 10)
            messages.extend(request.conversation_history[-10:])  # Last 10 messages
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # --- Context Pruning ---
        pruner = ContextPruner(max_tokens=30000)
        messages_before_prune = len(messages)
        messages = pruner.prune_messages(messages)
        messages_after_prune = len(messages)
        
        step2_duration = int((time.time() - step2_start) * 1000)
        process_steps.append({
            "step": "context_building",
            "status": "completed",
            "duration_ms": step2_duration,
            "details": {
                "system_prompt_length": len(system_prompt),
                "system_prompt_preview": system_prompt[:300] + ("..." if len(system_prompt) > 300 else ""),
                "memory_context_length": len(memory_context),
                "memory_context_preview": memory_context[:500] + ("..." if len(memory_context) > 500 else "") if memory_context else None,
                "history_messages": history_count,
                "total_messages": len(messages),
                "pruned_messages": messages_before_prune - messages_after_prune,
            }
        })

        # Step 3: LLM Generation
        step3_start = time.time()
        
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        ai_response = completion.choices[0].message.content
        
        step3_duration = int((time.time() - step3_start) * 1000)
        process_steps.append({
            "step": "llm_generation",
            "status": "completed",
            "duration_ms": step3_duration,
            "details": {
                "model": model,
                "tokens_prompt": completion.usage.prompt_tokens if completion.usage else 0,
                "tokens_completion": completion.usage.completion_tokens if completion.usage else 0,
                "tokens_total": completion.usage.total_tokens if completion.usage else 0,
                "response_preview": ai_response[:200] + ("..." if len(ai_response) > 200 else "") if ai_response else None,
            }
        })
        
        # Step 4: Fact Extraction
        step4_start = time.time()
        extraction_status = "completed"
        facts_found = 0
        
        extraction_prompt = f"""Analyze this conversation and extract CRITICAL facts about the user.
Only extract facts that are EXTREMELY important to remember immediately (like a name change, urgent preference).
If it can wait for a batch summary, respond with "NONE".

User message: {request.message}

Respond in this format (one fact per line):
FACT: [the fact to remember]

Or just:
NONE"""

        extraction_response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0,
            max_tokens=200,
        )
        
        extracted = extraction_response.choices[0].message.content.strip()
        
        if extracted and extracted.upper() != "NONE":
            # Parse and store each fact
            for line in extracted.split("\n"):
                if line.startswith("FACT:"):
                    fact = line[5:].strip()
                    if fact:
                        try:
                            # Direct storage without re-extraction
                            item = await system.save_fact(fact, {"source": "conversation_immediate"})
                            
                            memories_stored.append({
                                "id": str(item.id),
                                "content": item.content,
                                "category_path": item.category_path,
                            })
                            facts_found += 1
                        except Exception as e:
                            # Log but don't crash
                            print(f"ERROR: Memorize failed: {e}")
        else:
            extraction_status = "skipped"
        
        step4_duration = int((time.time() - step4_start) * 1000)
        # Collect extracted fact contents for display
        extracted_facts_content = [m["content"] for m in memories_stored] if memories_stored else []
        process_steps.append({
            "step": "fact_extraction",
            "status": extraction_status,
            "duration_ms": step4_duration,
            "details": {
                "facts_found": facts_found,
                "extraction_model": model,
                "extracted_facts": extracted_facts_content,
                "raw_extraction": extracted[:300] + ("..." if len(extracted) > 300 else "") if extracted else None,
            }
        })
        
        # Step 4.5: Triple Extraction Information
        # Get triple extraction config from system
        llm_config = system._memorize_pipeline.llm_config if hasattr(system, '_memorize_pipeline') else None
        triple_enabled = llm_config.use_semantic_triples if llm_config else False
        triple_immediate = llm_config.triple_extraction_immediate if llm_config else False
        
        triple_status = "completed" if facts_found > 0 and triple_enabled else "skipped"
        triple_mode = "immediate" if triple_immediate else "lazy"
        
        # Count triples that would be extracted (estimate: ~1-3 triples per fact)
        estimated_triples = facts_found * 2 if triple_immediate else 0
        
        process_steps.append({
            "step": "triple_extraction",
            "status": triple_status,
            "duration_ms": 0,  # Included in fact_extraction timing
            "details": {
                "triples_enabled": triple_enabled,
                "extraction_mode": triple_mode,
                "facts_processed": facts_found,
                "estimated_triples": estimated_triples if triple_immediate else None,
                "pending_extraction": facts_found if not triple_immediate and facts_found > 0 else 0,
                "description": (
                    f"즉시 추출: {facts_found}개 사실에서 트리플 추출" 
                    if triple_immediate and facts_found > 0 
                    else f"지연 추출: {facts_found}개 사실 대기 중" 
                    if not triple_immediate and facts_found > 0 
                    else "추출할 사실 없음"
                ),
            }
        })
        
        # Step 5: Buffer Update
        step5_start = time.time()
        
        await system.add_to_buffer("user", request.message)
        await system.add_to_buffer("assistant", ai_response)
        
        # Calculate buffer status directly (same logic as buffer.py route)
        buffer = system.conversation_buffer
        threshold = system.FLUSH_THRESHOLD_TOKENS
        total_chars = sum(len(m.get("content", "")) for m in buffer)
        estimated_tokens = int(total_chars / 2)
        fill_percentage = min(100, int((estimated_tokens / threshold) * 100)) if threshold > 0 else 0
        
        # Check and flush if threshold reached (Background Task)
        background_tasks.add_task(system.check_and_flush)
        
        step5_duration = int((time.time() - step5_start) * 1000)
        process_steps.append({
            "step": "buffer_update",
            "status": "completed",
            "duration_ms": step5_duration,
            "details": {
                "messages_buffered": 2,
                "buffer_fill_percentage": fill_percentage,
                "auto_flush_scheduled": True,
                "buffered_messages": [
                    {
                        "role": "user",
                        "content_preview": request.message[:150] + ("..." if len(request.message) > 150 else ""),
                    },
                    {
                        "role": "assistant",
                        "content_preview": ai_response[:150] + ("..." if len(ai_response) > 150 else "") if ai_response else "",
                    },
                ],
            }
        })
        
        return ConversationResponse(
            response=ai_response,
            memories_retrieved=memories_retrieved,
            memories_stored=memories_stored,
            processing_info={
                "mode": request.mode,
                "model": model,
                "memories_found": len(memories_retrieved),
                "facts_extracted": len(memories_stored),
                "process_steps": process_steps,
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

