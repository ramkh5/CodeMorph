from dataclasses import dataclass
from typing import AsyncGenerator
import asyncio

@dataclass
class ResultDto:
    message: str
    value: int

async def run() -> AsyncGenerator[ResultDto, None]:
    """
    Demo run() method: yields a sequence of ResultDto objects with artificial delay.
    """
    for i in range(3):
        await asyncio.sleep(0.01)  # simulate async work
        yield ResultDto(message=f"step-{i}", value=i)
