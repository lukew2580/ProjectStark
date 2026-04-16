"""
Tool Integration System
Allows agents to use external tools
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ToolType(Enum):
    HTTP = "http"
    FILE = "file"
    SHELL = "shell"
    SEARCH = "search"
    COMPUTE = "compute"


@dataclass
class ToolDefinition:
    name: str
    tool_type: ToolType
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None


class ToolRegistry:
    """
    Registry for external tools agents can use.
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        default_tools = [
            ToolDefinition(
                name="http_get",
                tool_type=ToolType.HTTP,
                description="Make HTTP GET request",
                parameters={"url": "string", "headers": "dict"}
            ),
            ToolDefinition(
                name="http_post",
                tool_type=ToolType.HTTP,
                description="Make HTTP POST request",
                parameters={"url": "string", "data": "dict", "headers": "dict"}
            ),
            ToolDefinition(
                name="file_read",
                tool_type=ToolType.FILE,
                description="Read file contents",
                parameters={"path": "string"}
            ),
            ToolDefinition(
                name="file_write",
                tool_type=ToolType.FILE,
                description="Write to file",
                parameters={"path": "string", "content": "string"}
            ),
            ToolDefinition(
                name="shell_run",
                tool_type=ToolType.SHELL,
                description="Run shell command",
                parameters={"command": "string", "timeout": "int"}
            ),
            ToolDefinition(
                name="web_search",
                tool_type=ToolType.SEARCH,
                description="Search the web",
                parameters={"query": "string", "num_results": "int"}
            ),
            ToolDefinition(
                name="calculate",
                tool_type=ToolType.COMPUTE,
                description="Perform calculation",
                parameters={"expression": "string"}
            )
        ]
        
        for tool in default_tools:
            self.tools[tool.name] = tool
    
    def register_tool(self, tool: ToolDefinition):
        """Register a new tool."""
        self.tools[tool.name] = tool
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict:
        """Execute a tool."""
        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}
        
        tool = self.tools[tool_name]
        
        try:
            # Execute based on tool type
            if tool.tool_type == ToolType.HTTP:
                return await self._execute_http(tool_name, parameters)
            elif tool.tool_type == ToolType.FILE:
                return self._execute_file(tool_name, parameters)
            elif tool.tool_type == ToolType.SHELL:
                return await self._execute_shell(tool_name, parameters)
            elif tool.tool_type == ToolType.SEARCH:
                return await self._execute_search(tool_name, parameters)
            elif tool.tool_type == ToolType.COMPUTE:
                return self._execute_compute(tool_name, parameters)
            else:
                return {"error": "Unknown tool type"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _execute_http(self, tool_name: str, params: Dict) -> Dict:
        """Execute HTTP tool."""
        import aiohttp
        url = params.get("url", "")
        
        if not url:
            return {"error": "url required"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    text = await resp.text()
                    return {"status": resp.status, "body": text[:1000]}
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_file(self, tool_name: str, params: Dict) -> Dict:
        """Execute file tool."""
        import os
        
        path = params.get("path", "")
        
        if not path:
            return {"error": "path required"}
        
        if "read" in tool_name:
            if not os.path.exists(path):
                return {"error": "File not found"}
            with open(path, "r") as f:
                return {"content": f.read()[:1000]}
        elif "write" in tool_name:
            content = params.get("content", "")
            with open(path, "w") as f:
                f.write(content)
            return {"written": True}
        
        return {"error": "Unknown file operation"}
    
    async def _execute_shell(self, tool_name: str, params: Dict) -> Dict:
        """Execute shell tool."""
        import subprocess
        
        cmd = params.get("command", "")
        
        if not cmd:
            return {"error": "command required"}
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                timeout=params.get("timeout", 30)
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout.decode()[:1000],
                "stderr": result.stderr.decode()[:500]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _execute_search(self, tool_name: str, params: Dict) -> Dict:
        """Execute search tool."""
        query = params.get("query", "")
        
        if not query:
            return {"error": "query required"}
        
        # Would integrate with actual search API
        return {
            "query": query,
            "results": [
                {"title": f"Result for {query}", "url": f"https://example.com/{query}"}
            ]
        }
    
    def _execute_compute(self, tool_name: str, params: Dict) -> Dict:
        """Execute compute tool."""
        expr = params.get("expression", "")
        
        if not expr:
            return {"error": "expression required"}
        
        try:
            result = eval(expr, {"__builtins__": {}}, {})
            return {"expression": expr, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def list_tools(self) -> List[Dict]:
        """List all available tools."""
        return [
            {
                "name": t.name,
                "type": t.tool_type.value,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in self.tools.values()
        ]


_global_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _global_tool_registry
    if _global_tool_registry is None:
        _global_tool_registry = ToolRegistry()
    return _global_tool_registry