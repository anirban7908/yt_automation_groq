import sys
import asyncio
import argparse
import json
import os
import datetime
from core.scraper import NewsScraper
from core.brain import ScriptGenerator
from core.voice import VoiceEngine
from core.visuals import VisualScout
from core.assembler import VideoAssembler
from core.upload_prep import UploadManager
from core.uploader import YouTubeUploader
from core.db_manager import DBManager


def run_creation_pipeline(slot_name):
    print(f"\n🎬 STARTING PRODUCTION PIPELINE: {slot_name.upper()}")

    # 1. SCRAPER
    print("---------------------------------------")
    scraper = NewsScraper()
    scraper.scrape_targeted_niche(forced_slot=slot_name)

    # 2. BRAIN (Scripting with Groq)
    print("---------------------------------------")
    brain = ScriptGenerator()
    brain.generate_script()

    # 3. VOICE (Async)
    print("---------------------------------------")
    voice = VoiceEngine()
    asyncio.run(voice.generate_audio())

    # 4. VISUALS
    print("---------------------------------------")
    visuals = VisualScout()
    visuals.download_visuals()

    # 5. ASSEMBLER
    print("---------------------------------------")
    assembler = VideoAssembler()
    assembler.assemble()

    # 6. UPLOAD PREP & UPLOAD
    print("---------------------------------------")
    prep = UploadManager()
    prep.prepare_package()

    # 7. UPLOAD TO YOUTUBE
    print("---------------------------------------")
    uploader = YouTubeUploader()
    uploader.upload_video()

    # 8. JSON LOGGING
    print("---------------------------------------")
    print("📝 Logging details to JSON...")

    db = DBManager()
    # Fetch the video that was just processed
    latest_task = db.collection.find_one(
        {"status": "uploaded"}, sort=[("uploaded_at", -1)]
    )

    if latest_task:
        log_entry = {
            "video_name": latest_task.get("title"),
            "youtube_id": latest_task.get("youtube_id"),
            "time_slot": slot_name,
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        log_file = "production_log.json"

        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except:
                logs = []
        else:
            logs = []

        logs.append(log_entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)

        print(f"✅ Log saved to: {log_file}")
    else:
        print("⚠️ Log skipped (No upload confirmed).")

    print(f"\n✅ PIPELINE COMPLETE for {slot_name}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "slot", help="The time slot (morning, noon, evening, night)", default="noon"
    )
    args = parser.parse_args()

    run_creation_pipeline(args.slot)
