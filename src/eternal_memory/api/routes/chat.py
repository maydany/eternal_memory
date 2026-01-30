"""
Chat API Routes

Endpoints for memory-augmented conversation.
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eternal_memory.api.main import get_memory_system
from eternal_memory.engine.context_pruner import ContextPruner

router = APIRouter()


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
        
        # Step 1: Retrieve relevant memories
        memories_retrieved = []
        memories_stored = []
        memory_context = ""
        
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
        except Exception:
            # Continue even if retrieval fails
            pass
        
        # Step 2: Generate LLM response with memory context
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        client = AsyncOpenAI(api_key=api_key)
        
        system_prompt = """You are a helpful AI assistant with persistent memory.
You remember information about the user across conversations.
When the user shares personal information, acknowledge it warmly and remember it.
When you have relevant memories, use them naturally in your responses.

Important: Always respond in the same language the user uses."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add memory context if available
        if memory_context:
            messages.append({
                "role": "system", 
                "content": f"Relevant memories about this user:\n{memory_context}"
            })
        
        # Add conversation history if provided
        if request.conversation_history:
            messages.extend(request.conversation_history[-10:])  # Last 10 messages
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # --- Context Pruning ---
        # Ensure we don't exceed model limits. 
        # OpenAI models have varying limits, but we'll set a safe "working context" limit
        # to ensure we leave room for the response.
        # e.g., for 128k model, we might want to limit history to 32k or 64k to save cost/latency.
        # But for 'gpt-4o-mini', it has 128k context.
        # We'll set a conservative 32k token limit for input history to correspond with ContextPruner default.
        pruner = ContextPruner(max_tokens=30000)
        messages = pruner.prune_messages(messages)
        # -----------------------

        # Generate response
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        ai_response = completion.choices[0].message.content
        
        # Step 3: Buffer messages and check for flush
        # We buffer both the user message and the AI response
        await system.add_to_buffer("user", request.message)
        await system.add_to_buffer("assistant", ai_response)
        
        # Check and flush if threshold reached (Background Task)
        # We run this in the background to avoid blocking the user response
        background_tasks.add_task(system.check_and_flush)
        
        # Optional: Keep "per-message" extraction but make it very strict
        # or rely solely on flush. For now, we'll keep it as a "fast path" for critical info.
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
                        except Exception as e:
                            # Log but don't crash
                            print(f"ERROR: Memorize failed: {e}")
        
        return ConversationResponse(
            response=ai_response,
            memories_retrieved=memories_retrieved,
            memories_stored=memories_stored,
            processing_info={
                "mode": request.mode,
                "model": model,
                "memories_found": len(memories_retrieved),
                "facts_extracted": len(memories_stored),
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
