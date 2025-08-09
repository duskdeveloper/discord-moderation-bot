import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

class Database:
    def __init__(self, db_path: str = "moderation.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                config TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds (guild_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds (guild_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_timeouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                expires_at TIMESTAMP,
                reason TEXT,
                moderator_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds (guild_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spam_tracking (
                user_id INTEGER,
                guild_id INTEGER,
                message_count INTEGER DEFAULT 0,
                last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duplicate_count INTEGER DEFAULT 0,
                last_message_content TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("Database initialized successfully")
        
    async def add_guild(self, guild_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)
        ''', (guild_id,))
        
        conn.commit()
        conn.close()
        
    async def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT config FROM guilds WHERE guild_id = ?', (guild_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result[0]) if result[0] else {}
        return {}
        
    async def update_guild_config(self, guild_id: int, config: Dict[str, Any]):
        await self.add_guild(guild_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE guilds SET config = ? WHERE guild_id = ?
        ''', (json.dumps(config), guild_id))
        
        conn.commit()
        conn.close()
        
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
        ''', (guild_id, user_id, moderator_id, reason))
        
        conn.commit()
        conn.close()
        
    async def get_user_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, moderator_id, reason, created_at
            FROM warnings
            WHERE guild_id = ? AND user_id = ?
            ORDER BY created_at DESC
        ''', (guild_id, user_id))
        
        results = cursor.fetchall()
        conn.close()
        
        warnings = []
        for result in results:
            warnings.append({
                'id': result[0],
                'moderator_id': result[1],
                'reason': result[2],
                'created_at': result[3]
            })
            
        return warnings
        
    async def remove_warning(self, warning_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM warnings WHERE id = ?', (warning_id,))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return success
        
    async def clear_user_warnings(self, guild_id: int, user_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM warnings WHERE guild_id = ? AND user_id = ?
        ''', (guild_id, user_id))
        
        conn.commit()
        conn.close()
        
    async def log_moderation_action(self, guild_id: int, user_id: int, moderator_id: int, 
                                  action: str, reason: str, duration: Optional[int] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (guild_id, user_id, moderator_id, action, reason, duration))
        
        conn.commit()
        conn.close()
        
    async def get_moderation_logs(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, moderator_id, action, reason, duration, created_at
            FROM moderation_logs
            WHERE guild_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (guild_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        logs = []
        for result in results:
            logs.append({
                'user_id': result[0],
                'moderator_id': result[1],
                'action': result[2],
                'reason': result[3],
                'duration': result[4],
                'created_at': result[5]
            })
            
        return logs
        
    async def update_spam_tracking(self, guild_id: int, user_id: int, message_content: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        cursor.execute('''
            SELECT message_count, duplicate_count, last_message_content, last_message_time
            FROM spam_tracking
            WHERE guild_id = ? AND user_id = ?
        ''', (guild_id, user_id))
        
        result = cursor.fetchone()
        
        if result:
            last_message_time = datetime.fromisoformat(result[3])
            
            if last_message_time < one_minute_ago:
                message_count = 1
                duplicate_count = 0
            else:
                message_count = result[0] + 1
                duplicate_count = result[1] + 1 if result[2] == message_content else 0
                
            cursor.execute('''
                UPDATE spam_tracking
                SET message_count = ?, duplicate_count = ?, 
                    last_message_content = ?, last_message_time = ?
                WHERE guild_id = ? AND user_id = ?
            ''', (message_count, duplicate_count, message_content, now.isoformat(), guild_id, user_id))
        else:
            cursor.execute('''
                INSERT INTO spam_tracking (guild_id, user_id, message_count, duplicate_count, 
                                         last_message_content, last_message_time)
                VALUES (?, ?, 1, 0, ?, ?)
            ''', (guild_id, user_id, message_content, now.isoformat()))
            
        conn.commit()
        conn.close()
        
    async def get_spam_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_count, duplicate_count, last_message_time
            FROM spam_tracking
            WHERE guild_id = ? AND user_id = ?
        ''', (guild_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            last_message_time = datetime.fromisoformat(result[2])
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            
            if last_message_time < one_minute_ago:
                return {'message_count': 0, 'duplicate_count': 0}
            else:
                return {'message_count': result[0], 'duplicate_count': result[1]}
        
        return {'message_count': 0, 'duplicate_count': 0}
        
    async def cleanup_old_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        cursor.execute('''
            DELETE FROM spam_tracking 
            WHERE last_message_time < ?
        ''', (thirty_days_ago.isoformat(),))
        
        cursor.execute('''
            DELETE FROM user_timeouts 
            WHERE expires_at < ?
        ''', (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
        
    async def close(self):
        pass
