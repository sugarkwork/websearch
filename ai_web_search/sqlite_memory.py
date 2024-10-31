import sqlite3
import hashlib
import pickle
import threading
from queue import Queue

database_file = 'persistent_memory.db'
memory_store = {}
write_queue = Queue()
initialized = False

def initialize():
    global initialized
    if initialized:
        return

    # データベースの初期化
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            key TEXT PRIMARY KEY,
            value BLOB
        )
    ''')
    conn.commit()
    conn.close()

    # データベースへの非同期書き込みスレッド開始
    db_writer_thread = threading.Thread(target=async_db_writer, daemon=True)
    db_writer_thread.start()

    initialized = True

def name_hash(name):
    return hashlib.sha512(name.encode()).hexdigest()

def save_memory(key, val):
    global initialized
    if not initialized:
        initialize()
    hash_key = name_hash(key)
    memory_store[hash_key] = val
    write_queue.put((hash_key, val))

def async_db_writer():
    global initialized
    if not initialized:
        initialize()
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    while True:
        hash_key, val = write_queue.get()
        try:
            c.execute('REPLACE INTO memory (key, value) VALUES (?, ?)', (hash_key, pickle.dumps(val)))
            conn.commit()
        except Exception as e:
            print(f"Error writing to DB: {e}")
        write_queue.task_done()

def load_memory(key, defval=None):
    global initialized
    if not initialized:
        initialize()
    hash_key = name_hash(key)
    if hash_key in memory_store:
        return memory_store[hash_key]

    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    try:
        c.execute('SELECT value FROM memory WHERE key = ?', (hash_key,))
        row = c.fetchone()
        if row is not None:
            value = pickle.loads(row[0])
            memory_store[hash_key] = value
            return value
    except Exception as e:
        print(f"Error reading from DB: {e}")
    finally:
        conn.close()
    
    return defval

# データベースの初期化と非同期書き込みスレッドの開始
initialize()
