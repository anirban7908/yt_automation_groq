import os
import re
import difflib
import certifi
from datetime import datetime, timedelta, timezone  # <--- Added timezone import
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class DBManager:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.db_name = os.getenv("DB_NAME", "yt_automation")

        if not self.uri:
            raise ValueError("❌ Error: MONGO_URI is missing from .env file.")

        # SSL & TIMEOUT FIXES
        self.client = MongoClient(
            self.uri,
            tlsCAFile=certifi.where(),
            connectTimeoutMS=60000,
            socketTimeoutMS=60000,
        )

        self.db = self.client[self.db_name]
        self.collection = self.db["video_tasks"]

        self.base_dir = "data/generated_videos_folder"
        os.makedirs(self.base_dir, exist_ok=True)

    def sanitize_filename(self, name):
        clean = re.sub(r"[^\w\s-]", "", name)
        return re.sub(r"[-\s]+", "_", clean).strip()

    def get_video_folder(self, slot, title):
        now = datetime.now()
        date_str = now.strftime("%d-%m-%Y")
        if not slot:
            slot = "noon"
        safe_title = self.sanitize_filename(title)[:50]
        full_path = os.path.join(self.base_dir, date_str, slot, safe_title)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    # 🟢 HYBRID CHECK: URL + FUZZY TITLE + 7-DAY WINDOW
    def task_exists(self, new_title, source_url=None):
        # 🟢 FIX 1: Use timezone-aware UTC
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

        # CHECK 1: URL MATCH
        if source_url:
            existing_url = self.collection.find_one(
                {"source_url": source_url, "created_at": {"$gte": cutoff_date}}
            )
            if existing_url:
                print(f"      🚫 Duplicate URL Found: '{source_url}' (Used recently)")
                return True

        # CHECK 2: FUZZY TITLE MATCH
        recent_tasks = self.collection.find(
            {"created_at": {"$gte": cutoff_date}}, {"title": 1}
        )

        for task in recent_tasks:
            existing_title = task.get("title", "")

            similarity = difflib.SequenceMatcher(
                None, new_title.lower(), existing_title.lower()
            ).ratio()

            if similarity > 0.85:
                print(
                    f"      🚫 Duplicate Title Found ({int(similarity*100)}% match): '{new_title}' ≈ '{existing_title}'"
                )
                return True

        return False

    def add_task(
        self, title, content, source="manual", status="pending", extra_data=None
    ):
        if extra_data is None:
            extra_data = {}

        source_url = extra_data.get("source_url")

        if self.task_exists(title, source_url):
            print(f"      🚫 DB: Skipping Duplicate '{title[:20]}...'")
            return

        slot = extra_data.get("niche_slot", "morning")
        final_url = source_url if source_url else "https://news.google.com/"
        folder_path = self.get_video_folder(slot, title)

        task = {
            "title": title,
            "content": content,
            "source": source,
            "status": status,
            "source_url": final_url,
            "niche": extra_data.get("niche", "motivation"),
            "slot": slot,
            "folder_path": folder_path,
            # 🟢 FIX 2: Use timezone-aware UTC here too
            "created_at": datetime.now(timezone.utc),
        }

        self.collection.insert_one(task)
        print(f"📥 Task Added: {title}")
