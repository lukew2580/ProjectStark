"""
Gateway — GraphQL Wrapper
Optional GraphQL API layer over existing REST endpoints.
Uses graphql-core (optional dependency). Enable with ENABLE_GRAPHQL=1.
"""

import os
import time
import json
import logging
from typing import Optional, Any, Dict, List
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("hardwareless.graphql")

router = APIRouter(prefix="/v1/graphql", tags=["graphql"])

# Check if graphql-core is available
_GRAPHQL_AVAILABLE = False
try:
    import graphql
    from graphql import (
        GraphQLSchema,
        GraphQLObjectType,
        GraphQLField,
        GraphQLString,
        GraphQLList,
        GraphQLArgument,
        GraphQLNonNull,
        GraphQLInt,
        GraphQLFloat,
    )
    _GRAPHQL_AVAILABLE = True
except ImportError:
    logger.warning("graphql-core not installed; GraphQL endpoint disabled")
    graphql = None

if _GRAPHQL_AVAILABLE:
    # Define types
    MessageType = GraphQLObjectType(
        "Message",
        lambda: {
            "role": GraphQLField(GraphQLString),
            "content": GraphQLField(GraphQLString),
        }
    )
    
    ChoiceType = GraphQLObjectType(
        "Choice",
        lambda: {
            "index": GraphQLField(GraphQLInt),
            "message": GraphQLField(MessageType),
            "finish_reason": GraphQLField(GraphQLString),
        }
    )
    
    UsageType = GraphQLObjectType(
        "Usage",
        lambda: {
            "prompt_dimensions": GraphQLField(GraphQLInt),
            "completion_dimensions": GraphQLField(GraphQLInt),
            "total_dimensions": GraphQLField(GraphQLInt),
            "compression": GraphQLField(GraphQLObjectType(
                "CompressionStats",
                lambda: {
                    "raw_words": GraphQLField(GraphQLInt),
                    "compressed_words": GraphQLField(GraphQLInt),
                    "words_saved": GraphQLField(GraphQLInt),
                    "ratio": GraphQLField(GraphQLString),
                }
            )),
        }
    )
    
    ChatCompletionType = GraphQLObjectType(
        "ChatCompletion",
        lambda: {
            "id": GraphQLField(GraphQLString),
            "object": GraphQLField(GraphQLString),
            "created": GraphQLField(GraphQLInt),
            "model": GraphQLField(GraphQLString),
            "choices": GraphQLField(GraphQLList(ChoiceType)),
            "usage": GraphQLField(UsageType),
        }
    )
    
    TranslateResultType = GraphQLObjectType(
        "TranslateResult",
        lambda: {
            "original": GraphQLField(GraphQLString),
            "translated": GraphQLField(GraphQLString),
            "source_lang": GraphQLField(GraphQLString),
            "target_lang": GraphQLField(GraphQLString),
            "confidence": GraphQLField(GraphQLFloat),
        }
    )
    
    # Async resolver helpers
    async def resolve_chat(root, info, messages: List[Dict[str, str]]):
        """Call internal /v1/chat/completions logic."""
        from gateway.routes.chat import chat_completions as chat_handler
        from fastapi import Request
        from core_engine.security.validator import SecurityEvent, SecurityLevel
        from datetime import datetime
        
        # Build OpenAIRequest-like object
        class DummyOpenAIRequest:
            def __init__(self, messages, model="hardwareless-core"):
                self.messages = [type("Msg", (), {"role": m["role"], "content": m["content"]}) for m in messages]
                self.model = model
        
        request = DummyOpenAIRequest(messages)
        req = Request(scope={"type": "http", "client": ("127.0.0.1", 12345)})
        
        try:
            result = await chat_handler(request, req)
            return result
        except HTTPException as e:
            raise graphql.GraphQLError(e.detail)
    
    async def resolve_translate(
        root, info, text: str, source_lang: str = "auto", target_lang: str = "en"
    ):
        """Call internal /translate logic."""
        from gateway.routes.chat import translate as translate_handler
        from gateway.routes.chat import TranslateRequest
        from fastapi import Request
        
        req = Request(scope={"type": "http", "client": ("127.0.0.1", 12345)})
        request = TranslateRequest(text=text, source_lang=source_lang, target_lang=target_lang)
        result = await translate_handler(request, req)
        return result
    
    # Root query
    QueryType = GraphQLObjectType(
        "Query",
        lambda: {
            "chat": GraphQLField(
                ChatCompletionType,
                args={
                    "messages": GraphQLArgument(
                        GraphQLNonNull(GraphQLList(GraphQLNonNull(
                            GraphQLObjectType("MessageInput", lambda: {
                                "role": GraphQLField(GraphQLNonNull(GraphQLString)),
                                "content": GraphQLField(GraphQLNonNull(GraphQLString)),
                            })
                        )))
                    ),
                    "model": GraphQLArgument(GraphQLString, default_value="hardwareless-core"),
                },
                resolve=resolve_chat,
            ),
            "translate": GraphQLField(
                TranslateResultType,
                args={
                    "text": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                    "source_lang": GraphQLArgument(GraphQLString, default_value="auto"),
                    "target_lang": GraphQLArgument(GraphQLString, default_value="en"),
                },
                resolve=resolve_translate,
            ),
            "health": GraphQLField(
                GraphQLObjectType("Health", lambda: {
                    "status": GraphQLField(GraphQLString),
                    "uptime": GraphQLField(GraphQLInt),
                }),
                resolve=lambda root, info: {"status": "ok", "uptime": int(time.time())}
            ),
        }
    )
    
    schema = GraphQLSchema(query=QueryType)


@router.post("/")
async def graphql_endpoint(request: Request):
    """
    GraphQL endpoint.
    POST {"query": "...", "variables": {...}}
    """
    if not _GRAPHQL_AVAILABLE:
        raise HTTPException(503, "GraphQL support not installed (install graphql-core)")
    
    body = await request.json()
    query = body.get("query")
    variables = body.get("variables", {})
    operation_name = body.get("operationName")
    
    if not query:
        raise HTTPException(400, "Missing 'query' field")
    
    start = time.perf_counter()
    try:
        result = await graphql.graphql(
            schema,
            query,
            variable_values=variables,
            operation_name=operation_name,
        )
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"GraphQL query completed in {elapsed:.2f}ms")
        
        return JSONResponse({"data": result.data}, status_code=200)
    except graphql.GraphQLError as e:
        return JSONResponse({"errors": [{"message": str(e)}]}, status_code=400)


@router.get("/")
async def graphql_playground():
    """GraphQL Playground UI (simple HTML form)."""
    if not _GRAPHQL_AVAILABLE:
        raise HTTPException(503, "GraphQL not available")
    html = """
<!doctype html>
<html>
<head><title>HDC GraphQL</title>
<link href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" rel="stylesheet"/>
</head>
<body>
<div id="root"></div>
<script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
<script>window.addEventListener('load', function (event) {
      GraphQLPlayground.init(document.getElementById('root'), {
        endpoint: '/v1/graphql'
      })
    })</script>
</body>
</html>
    """
    return HTMLResponse(html)


from fastapi.responses import HTMLResponse

__all__ = ["router"]
