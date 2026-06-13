from unittest.mock import AsyncMock, patch

import pytest

from app.tools.core.customers import _classify_client, _schedule_followup, register_customers_tools
from app.tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_classify_client():
    # Arrange
    params = {
        "conversation_id": "test_conv_123",
        "classification": "lead_quente",
    }

    mock_pool = AsyncMock()
    with patch("app.services.postgres.get_pool", return_value=mock_pool, new_callable=AsyncMock) as mock_get_pool:
        # Act
        result = await _classify_client(params)

        # Assert
        assert result == "Cliente classificado como: lead_quente"
        mock_get_pool.assert_awaited_once()
        mock_pool.execute.assert_awaited_once_with(
            "UPDATE conversations SET classification = $1, updated_at = NOW() WHERE id = $2",
            "lead_quente",
            "test_conv_123",
        )

@pytest.mark.asyncio
async def test_classify_client_default_classification():
    # Arrange
    params = {
        "conversation_id": "test_conv_456",
    }

    mock_pool = AsyncMock()
    with patch("app.services.postgres.get_pool", return_value=mock_pool, new_callable=AsyncMock) as mock_get_pool:
        # Act
        result = await _classify_client(params)

        # Assert
        assert result == "Cliente classificado como: lead_morno"
        mock_get_pool.assert_awaited_once()
        mock_pool.execute.assert_awaited_once_with(
            "UPDATE conversations SET classification = $1, updated_at = NOW() WHERE id = $2",
            "lead_morno",
            "test_conv_456",
        )

@pytest.mark.asyncio
async def test_classify_client_missing_conversation_id():
    # Arrange
    params = {
        "classification": "lead_quente",
    }

    mock_pool = AsyncMock()
    with patch("app.services.postgres.get_pool", return_value=mock_pool, new_callable=AsyncMock):
        # Act & Assert
        with pytest.raises(KeyError) as exc_info:
            await _classify_client(params)
        assert exc_info.value.args[0] == "conversation_id"

@pytest.mark.asyncio
async def test_schedule_followup():
    # Arrange
    params = {
        "customer_id": "cust_123",
        "days": 5,
        "message_template": "Oi, lembrando de você!",
    }

    # Act
    result = await _schedule_followup(params)

    # Assert
    assert result == "Follow-up agendado para 5 dias. Mensagem: Oi, lembrando de você!"

@pytest.mark.asyncio
async def test_schedule_followup_defaults():
    # Arrange
    params = {
        "customer_id": "cust_456",
    }

    # Act
    result = await _schedule_followup(params)

    # Assert
    assert result == "Follow-up agendado para 3 dias. Mensagem: Olá! Como posso ajudar?"

def test_register_customers_tools():
    # Arrange
    registry = ToolRegistry()

    # Act
    register_customers_tools(registry)

    # Assert
    assert len(registry._core_tools) == 2

    classify_tool = next(t for t in registry._core_tools if t.name == "classify_client")
    assert classify_tool.name == "classify_client"
    assert classify_tool.is_idempotent is True
    assert classify_tool.execute == _classify_client

    schedule_tool = next(t for t in registry._core_tools if t.name == "schedule_followup")
    assert schedule_tool.name == "schedule_followup"
    assert schedule_tool.is_idempotent is False
    assert schedule_tool.execute == _schedule_followup
