import aiosqlite
import hashlib
import pickle
import asyncio
from typing import Any, Optional

database_file = 'persistent_memory.db'
memory_store = {}
write_queue = asyncio.Queue()
initialized = False

async def initialize():
    global initialized
    if initialized:
        return

    # データベースの初期化
    async with aiosqlite.connect(database_file) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        await db.commit()

    # データベースへの非同期書き込みタスク開始
    asyncio.create_task(async_db_writer())
    initialized = True

def name_hash(name: str) -> str:
    return hashlib.sha512(name.encode()).hexdigest()

async def save_memory(key: str, val: Any):
    global initialized
    if not initialized:
        await initialize()
    hash_key = name_hash(key)
    memory_store[hash_key] = val
    await write_queue.put((hash_key, val))

async def async_db_writer():
    global initialized
    if not initialized:
        await initialize()
    
    async with aiosqlite.connect(database_file) as db:
        while True:
            await asyncio.sleep(0.1)
            hash_key, val = await write_queue.get()
            try:
                await db.execute(
                    'REPLACE INTO memory (key, value) VALUES (?, ?)',
                    (hash_key, pickle.dumps(val))
                )
                await db.commit()
            except Exception as e:
                print(f"Error writing to DB: {e}")
            finally:
                write_queue.task_done()

async def load_memory(key: str, defval: Any = None) -> Any:
    global initialized
    if not initialized:
        await initialize()
    
    hash_key = name_hash(key)
    if hash_key in memory_store:
        return memory_store[hash_key]

    try:
        async with aiosqlite.connect(database_file) as db:
            async with db.execute(
                'SELECT value FROM memory WHERE key = ?',
                (hash_key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is not None:
                    value = pickle.loads(row[0])
                    memory_store[hash_key] = value
                    return value
    except Exception as e:
        print(f"Error reading from DB: {e}")
    
    return defval

# 使用例
async def main():
    # データベースの初期化
    await initialize()
    
    # メモリに保存
    await save_memory("test_key", "test_value")
    
    # メモリから読み込み
    value = await load_memory("test_key")
    print(f"Loaded value: {value}")

if __name__ == "__main__":
    asyncio.run(main())
