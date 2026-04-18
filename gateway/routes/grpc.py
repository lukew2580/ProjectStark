"""
Gateway — gRPC Server (Optional)
High-performance binary protocol for internal/external clients.
Uses grpcio (optional). Enable with ENABLE_GRPC=1.
"""

import os
import time
import logging
import asyncio
from typing import Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("hardwareless.grpc")

_GRPC_AVAILABLE = False
try:
    import grpc
    from concurrent import futures
    import grpc.aio as aiogrpc
    _GRPC_AVAILABLE = True
except ImportError:
    logger.warning("grpcio not installed; gRPC server disabled")


if _GRPC_AVAILABLE:
    # Define protobuf-like services (no .proto compilation, using raw stubs)
    # Keep it minimal: Chat, Translate, Health
    
    class HDCChatServicer:
        """gRPC service for chat/completions (OpenAI-compatible subset)."""
        
        async def ChatCompletion(self, request, context):
            """
            request has: messages (repeated Message), model (string)
            returns: id, choices[0].message.content, usage
            """
            from gateway.routes.chat import OpenAIRequest
            from gateway.routes.chat import chat_completions as chat_handler
            from fastapi import Request
            
            # Convert gRPC request to FastAPI request
            messages = []
            for msg in request.messages:
                messages.append({"role": msg.role, "content": msg.content})
            
            fasta_req = OpenAIRequest(model=request.model, messages=messages)
            req = Request(scope={
                "type": "http",
                "client": ("127.0.0.1", 0),
                "headers": [],
            })
            
            try:
                result = await chat_handler(fasta_req, req)
                # Build response
                resp = ChatCompletionResponse()
                resp.id = result["id"]
                resp.object = result["object"]
                resp.created = result["created"]
                resp.model = result["model"]
                choice = resp.choices.add()
                choice.index = 0
                choice.message.role = "assistant"
                choice.message.content = result["choices"][0]["message"]["content"]
                choice.finish_reason = "stop"
                
                usage = resp.usage
                usage.prompt_dimensions = result["usage"]["prompt_dimensions"]
                usage.completion_dimensions = result["usage"]["completion_dimensions"]
                usage.total_dimensions = result["usage"]["total_dimensions"]
                # Compression details omitted for brevity
                
                return resp
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return ChatCompletionResponse()
    
    class HDCTranslateServicer:
        """gRPC service for translation."""
        
        async def Translate(self, request, context):
            from gateway.routes.chat import TranslateRequest, translate
            from fastapi import Request
            
            fasta_req = TranslateRequest(
                text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
            )
            req = Request(scope={"type": "http", "client": ("127.0.0.1", 0), "headers": []})
            
            try:
                res = await translate(fasta_req, req)
                resp = TranslateResponse()
                resp.original = res["original"]
                resp.translated = res["translated"]
                resp.source_lang = res["source_lang"]
                resp.target_lang = res["target_lang"]
                resp.confidence = res["confidence"]
                return resp
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return TranslateResponse()
    
    class HDCHealthServicer:
        async def Check(self, request, context):
            from gateway.routes.health import health as health_handler
            res = await health_handler()
            resp = HealthResponse()
            resp.status = "ok"
            resp.services.update(res.get("services", {}))
            return resp
    
    # Protobuf message definitions (minimal)
    from google.protobuf.struct_pb2 import Value
    
    # We need to dynamically create protobuf messages using grpcio-tools or pre-compiled .proto
    # For simplicity, we'll define inline using grpc methods directly
    # In production, you'd compile .proto files and import
    
    # Placeholder: We'll rely on a pre-compiled proto or generate at install
    # Instead, create a simple ASCII protocol handler for demo
    
    class RawgRPCServer:
        """
        Minimal gRPC-compatible server using raw HTTP/2.
        For production, use compiled protos.
        """
        
        def __init__(self, host: str = "0.0.0.0", port: int = 50051):
            self.host = host
            self.port = port
            self._server: Optional[aiogrpc.Server] = None
            self._services = {}
        
        async def start(self):
            """Start the gRPC server (async)."""
            if not _GRPC_AVAILABLE:
                logger.error("gRPC not available; cannot start server")
                return
            
            self._server = aiogrpc.server()
            
            # Register services
            chat_servicer = HDCChatServicer()
            trans_servicer = HDCTranslateServicer()
            health_servicer = HDCHealthServicer()
            
            # Use reflection and health checking
            from grpc.experimental import aio as aio_grpc
            # would normally use add_GrpcChatService_to_server etc.
            
            self._server.add_insecure_port(f"{self.host}:{self.port}")
            await self._server.start()
            logger.info(f"gRPC server listening on {self.host}:{self.port}")
        
        async def stop(self, grace: float = 5.0):
            if self._server:
                await self._server.stop(grace)
                logger.info("gRPC server stopped")


# Factory
def create_grpc_server(host: str = "0.0.0.0", port: int = 50051) -> Any:
    """
    Create and return a gRPC server instance.
    Returns None if grpcio not installed.
    """
    if not _GRPC_AVAILABLE:
        logger.warning("gRPC server not available — install grpcio")
        return None
    return RawgRPCServer(host, port)


__all__ = [
    "create_grpc_server",
    "HDCChatServicer",
    "HDCTranslateServicer",
    "HDCHealthServicer",
]
