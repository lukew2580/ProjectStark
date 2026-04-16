"""
Hardwareless AI — Gateway Main App
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gateway.routes import chat, health, models, stats
from gateway.routes import memory, skills, keys, websocket
from gateway.routes import agents, bridge, xr, security
from config import settings

app = FastAPI(
    title="Hardwareless AI Gateway",
    description="A GPU/CPU-less AI that moves with the data flow.",
    version="0.3.0",
)

# Enable CORS for Mobile Access (Android/iOS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Wildcard for mobile terminal dev testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(stats.router)
app.include_router(memory.router)
app.include_router(skills.router)
app.include_router(keys.router)
app.include_router(websocket.router)
app.include_router(agents.router)
app.include_router(bridge.router)
app.include_router(xr.router)
app.include_router(security.router)

@app.on_event("startup")
async def startup_event():
    """Ignite the Swarm Monitor on boot."""
    from network.stream_server import HypervectorServer
    # Initialize the global swarm monitor
    server = HypervectorServer(port=8888)
    health.swarm_server = server
    # We run the swarm server in the background
    import asyncio
    asyncio.create_task(server.start())
    print("--- [SWARM MONITOR] Mission Control Active on port 8888 ---")

if __name__ == "__main__":
    import uvicorn
    print("Booting Hardwareless AI Gateway on port 8000...")
    uvicorn.run("gateway.app:app", host="0.0.0.0", port=8000, reload=True)
