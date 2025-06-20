from __future__ import annotations

import asyncio
import json
import os
import random
from typing import List, Dict

import openai
from pgvector.psycopg import register_vector
from psycopg_pool import AsyncConnectionPool

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost:5432/purposepath")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

_openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
_pool: AsyncConnectionPool | None = None


async def setup() -> None:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(POSTGRES_URL)
    async with _pool.connection() as conn:
        await register_vector(conn)
        if os.getenv("PGVECTOR_EXTENSION", "false").lower() == "true":
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ritual_logs (
                id SERIAL PRIMARY KEY,
                player_id TEXT,
                "askText"  TEXT,
                "seekText" TEXT,
                "knockText" TEXT,
                theme TEXT,
                sentiment vector(3),
                "intentVec" vector(768),
                created_at TIMESTAMPTZ DEFAULT (now() at time zone 'utc')
            )
            """,
        )


def _fallback_vector(dim: int) -> List[float]:
    random.seed(42)
    return [random.random() for _ in range(dim)]


async def _embedding(text: str) -> List[float]:
    try:
        res = await _openai_client.embeddings.create(
            model=EMBED_MODEL, input=text, dimensions=768
        )
        return res.data[0].embedding
    except Exception:
        return _fallback_vector(768)


async def _sentiment(text: str) -> List[float]:
    prompt = (
        "Return a JSON array [neg, neu, pos] with three numbers between 0 and 1 "
        "representing the sentiment of the text."
    )
    try:
        resp = await _openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            temperature=0,
        )
        vec = json.loads(resp.choices[0].message.content)
        if isinstance(vec, list) and len(vec) == 3:
            return [float(v) for v in vec]
    except Exception:
        pass
    return [0.33, 0.33, 0.34]


async def record(
    player_id: str, ask: str, seek: str, knock: str, theme: str
) -> Dict[str, List[float] | str]:
    if _pool is None:
        await setup()
    text = "\n".join([ask, seek, knock])
    sent_task = asyncio.create_task(_sentiment(text))
    emb_task = asyncio.create_task(_embedding(text))
    sentiment, embedding = await asyncio.gather(sent_task, emb_task)

    try:
        async with _pool.connection() as conn:
            await register_vector(conn)
            await conn.execute(
                'INSERT INTO ritual_logs (player_id,"askText","seekText","knockText",theme,sentiment,"intentVec") '
                'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (
                    player_id,
                    ask,
                    seek,
                    knock,
                    theme,
                    sentiment,
                    embedding,
                ),
            )
    except Exception:
        pass

    return {"intentVector": embedding, "theme": theme, "sentiment": sentiment}
