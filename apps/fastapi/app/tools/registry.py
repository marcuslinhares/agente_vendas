import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict
    is_idempotent: bool = True
    execute: Callable[[dict], Awaitable[str]] = field(default=lambda x: "Not implemented")  # type: ignore[arg-type,assignment]


class ToolRegistry:
    def __init__(self) -> None:
        self._core_tools: list[ToolDef] = []
        self._dynamic_tools: list[ToolDef] = []

    def register_core(self, tool: ToolDef) -> None:
        self._core_tools.append(tool)

    async def _load_dynamic_from_db(self) -> list[ToolDef]:
        from app.services.postgres import get_pool

        try:
            pool = await get_pool()
            rows = await pool.fetch(
                "SELECT name, description, schema, endpoint, http_method, "
                "headers, timeout_ms, is_idempotent, rate_limit "
                "FROM tools_catalog WHERE is_active = true"
            )
            tools = []
            for row in rows:
                tool = ToolDef(
                    name=row["name"],
                    description=row["description"],
                    parameters=row["schema"],
                    is_idempotent=row.get("is_idempotent", True),
                    execute=self._make_http_executor(
                        row["endpoint"],
                        row.get("http_method", "POST"),
                        row.get("headers", {}),
                        row.get("timeout_ms", 10000),
                        row.get("rate_limit", 0),
                    ),
                )
                tools.append(tool)
            return tools
        except Exception as e:
            print(f"[registry] DB load error: {e}")
            return []

    def _make_http_executor(
        self,
        endpoint: str,
        method: str,
        headers: dict,
        timeout_ms: int,
        rate_limit: int = 0,
    ) -> Callable[[dict], Awaitable[str]]:
        async def execute(params: dict) -> str:
            if rate_limit > 0:
                from app.services.redis import get_redis

                r = await get_redis()
                key = f"ratelimit:{endpoint}"
                count = await r.incr(key)
                if count == 1:
                    await r.expire(key, 60)
                if count > rate_limit:
                    return f"Rate limit reached ({rate_limit} req/min). Please wait."

            async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
                if method == "GET":
                    resp = await client.get(endpoint, params=params, headers=headers)
                else:
                    resp = await client.post(endpoint, json=params, headers=headers)
                if resp.is_error:
                    return f"Error {resp.status_code}: {resp.text}"
                return resp.text

        return execute

    async def load_all(self) -> list[ToolDef]:
        dynamic = await self._load_dynamic_from_db()
        self._dynamic_tools = dynamic
        return self._core_tools + self._dynamic_tools

    async def execute(self, name: str, params: dict) -> str:
        from app.services.postgres import get_pool

        start = time.monotonic()
        result = ""
        success = False
        error_msg: str | None = None

        try:
            for tool in self._core_tools + self._dynamic_tools:
                if tool.name == name:
                    result = await tool.execute(params)
                    success = True
                    break
            else:
                result = f"Tool '{name}' not found"
        except Exception as e:
            error_msg = str(e)
            result = f"Error executing {name}: {error_msg}"

        finally:
            duration = int((time.monotonic() - start) * 1000)
            try:
                pool = await get_pool()
                await pool.execute(
                    "INSERT INTO tool_execution_log "
                    "(tool_name, parameters, response, duration_ms, success, error_message) "
                    "VALUES ($1, $2::jsonb, $3, $4, $5, $6)",
                    name,
                    json.dumps(params),
                    str(result)[:1000],
                    duration,
                    success,
                    error_msg,
                )
            except Exception as log_err:
                print(f"[registry] Failed to log tool execution: {log_err}")

        return result
