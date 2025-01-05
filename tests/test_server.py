"""Test MCP server implementation."""
import anyio
import json
import pytest
from mcp.types import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability

from mcp_local_dev.server import init_server

@pytest.mark.asyncio
async def test_server_tool_registration():
    """Test server tool registration via JSON-RPC."""
    server = await init_server()
    
    # Create memory streams for client/server communication
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream[JSONRPCMessage](1)
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream[JSONRPCMessage](1)
    
    # Start server in background
    async with anyio.create_task_group() as tg:
        tg.start_soon(
            server.run,
            client_to_server_receive,
            server_to_client_send,
            InitializationOptions(
                server_name="mcp-local-dev",
                server_version="0.1.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(listChanged=False)
                )
            )
        )
        
        # Wait for initialization
        init_response = await server_to_client_receive.receive()
        assert isinstance(init_response.root, JSONRPCResponse)
        assert init_response.root.result["status"] == "success"

        # Send tools/list request
        request = JSONRPCMessage(
            root=JSONRPCRequest(
                jsonrpc="2.0",
                id=1,
                method="tools/list"
            )
        )
        await client_to_server_send.send(request)
        
        # Get response
        response = await server_to_client_receive.receive()
        assert isinstance(response.root, JSONRPCResponse)
        tools = response.root.result
        
        assert len(tools) > 0
        assert any(t["name"] == "create_environment" for t in tools)
        assert any(t["name"] == "run_tests" for t in tools)
        assert any(t["name"] == "cleanup" for t in tools)

@pytest.mark.asyncio
async def test_server_tool_execution():
    """Test server tool execution via JSON-RPC."""
    server = await init_server()
    
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream[JSONRPCMessage](1)
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream[JSONRPCMessage](1)
    
    async with anyio.create_task_group() as tg:
        tg.start_soon(
            server.run,
            client_to_server_receive,
            server_to_client_send,
            InitializationOptions(
                server_name="mcp-local-dev",
                server_version="0.1.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(listChanged=False)
                )
            )
        )

        # Wait for initialization
        init_response = await server_to_client_receive.receive()
        assert isinstance(init_response.root, JSONRPCResponse)
        assert init_response.root.result["status"] == "success"
        
        # Send tools/call request
        request = JSONRPCMessage(
            root=JSONRPCRequest(
                jsonrpc="2.0",
                id=1,
                method="tools/call",
                params={
                    "name": "create_environment",
                    "arguments": {
                        "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
                    }
                }
            )
        )
        await client_to_server_send.send(request)
        
        # Get response
        response = await server_to_client_receive.receive()
        assert isinstance(response.root, JSONRPCResponse)
        result = response.root.result[0]
        
        assert result["type"] == "text"
        data = json.loads(result["text"])
        assert "id" in data
        assert "working_dir" in data
