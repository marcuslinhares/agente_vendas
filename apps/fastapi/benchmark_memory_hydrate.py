import asyncio
import time

class MemoryHydrateNodeBaseline:
    async def run(self, state: dict) -> dict:
        conv_id = state["conversation_id"]

        # L1: Last 10 messages
        l1 = await mock_get_last_messages(conv_id, limit=10)

        # L2: Conversation summary
        l2 = await mock_get_conversation_summary(conv_id) or ""

        return {
            "l1_messages": l1,
            "l2_summary": l2,
        }

class MemoryHydrateNodeOptimized:
    async def run(self, state: dict) -> dict:
        conv_id = state["conversation_id"]

        # Gather both queries concurrently
        l1, l2 = await asyncio.gather(
            mock_get_last_messages(conv_id, limit=10),
            mock_get_conversation_summary(conv_id)
        )
        l2 = l2 or ""

        return {
            "l1_messages": l1,
            "l2_summary": l2,
        }

async def mock_get_last_messages(*args, **kwargs):
    await asyncio.sleep(0.5)
    return []

async def mock_get_conversation_summary(*args, **kwargs):
    await asyncio.sleep(0.5)
    return "Summary"

async def run_benchmark():
    node_baseline = MemoryHydrateNodeBaseline()
    node_optimized = MemoryHydrateNodeOptimized()
    state = {"conversation_id": "test_id"}

    start_time = time.time()
    await node_baseline.run(state)
    end_time = time.time()
    baseline_time = end_time - start_time
    print(f"Baseline elapsed time: {baseline_time:.4f} seconds")

    start_time = time.time()
    await node_optimized.run(state)
    end_time = time.time()
    optimized_time = end_time - start_time
    print(f"Optimized elapsed time: {optimized_time:.4f} seconds")
    print(f"Improvement: {baseline_time - optimized_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
