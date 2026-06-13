import pytest
from httpx import Request, RequestError, Response

from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_tool_execution_timeout(mocker):
    registry = ToolRegistry()
    executor = registry._make_http_executor(
        endpoint="http://example.com/api", method="GET", headers={}, timeout_ms=1000
    )

    request = Request("GET", "http://example.com/api")
    mocker.patch("httpx.AsyncClient.get", side_effect=RequestError("mock error", request=request))

    result = await executor({})

    assert "[Tool Execution Error]" in result


@pytest.mark.asyncio
async def test_tool_execution_500(mocker):
    registry = ToolRegistry()
    executor = registry._make_http_executor(
        endpoint="http://example.com/api", method="GET", headers={}, timeout_ms=1000
    )

    request = Request("GET", "http://example.com/api")
    mock_resp = Response(500, text="Internal Server Error", request=request)
    mocker.patch("httpx.AsyncClient.get", return_value=mock_resp)

    result = await executor({})

    assert "Error 500: Internal Server Error" in result


@pytest.mark.asyncio
async def test_tool_execution_post_success(mocker):
    registry = ToolRegistry()
    executor = registry._make_http_executor(
        endpoint="http://example.com/api",
        method="POST",
        headers={"Content-Type": "application/json"},
        timeout_ms=1000,
    )

    request = Request("POST", "http://example.com/api")
    mock_resp = Response(200, text='{"success": true}', request=request)
    mocker.patch("httpx.AsyncClient.post", return_value=mock_resp)

    result = await executor({"key": "value"})

    assert result == '{"success": true}'
