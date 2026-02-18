import json
import re
import os
from groq import Groq  # <--- CHANGED
from core.db_manager import DBManager
from dotenv import load_dotenv

load_dotenv()


class ScriptGenerator:
    def __init__(self):
        self.db = DBManager()
        # Initialize Groq Client
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # <--- CHANGED
        self.model = "llama-3.3-70b-versatile"  # Fast, high quality

    def repair_json(self, json_str):
        try:
            # Clean generic AI chatter
            json_str = re.sub(r"^[^{]*", "", json_str)
            json_str = re.sub(r"[^}]*$", "", json_str)
            return json.loads(json_str)
        except:
            return None

    def generate_script(self):
        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        niche = task.get("niche", "tech")
        source = task.get("content", "")[:3000]
        source_url = task.get("source_url", "https://news.google.com")

        # PROMPT REMAINS EXACTLY THE SAME AS BEFORE
        prompt = f"""
            ROLE: Documentary Director.
            TASK: Convert this news into a structured video script.
            SOURCE: "{source}"
            
            REQUIREMENTS:
            1. Break the story into 6-8 distinct SCENES.
            
            2. 'text': The narration for that scene (1-2 sentences).
            
            3. **VISUALS**:
                - 'keywords': List exactly 2 specific search terms for stock footage.
                - 'image_count': 1 (slow paced) or 2 (fast paced).
            
            4.  **METADATA**:
                - 'title': MUST be "Clickbait" style. High curiosity. 
                - BAD: "New Space Discovery"
                - GOOD: "NASA Just Found THIS on Mars!?"
                - GOOD: "You Won't Believe What Hubble Saw..."
                - RULE: Use ALL CAPS for emphasis words. Max 50 chars.
                - 'description': 3-sentence summary + call to action.
                - 'hashtags': #Viral #Shorts + 3 niche tags.
                
            5. **CRITICAL - KEYWORD RULES (ZERO TOLERANCE)**:
                - 'keywords': A list of exactly 2 string search terms.
                - **NEVER leave this empty.** Even for the Outro/CTA scene.
                - **SPECIFICITY**: Use specific names (e.g., "Sony Camera", "Elon Musk", "SpaceX Rocket").
                - **FALLBACK**: If the scene is generic, use keywords like ["Abstract Tech Background", "News Studio"].
                - **BAD**: [] or [""] -> THIS WILL CRASH THE SYSTEM.
                - **GOOD**: ["Sony LinkBuds", "Earbuds"] or ["Subscribe Button", "Social Media"].
            
            6. **CRITICAL - CTA RULES**: 
                - The FINAL SCENE must be a generic social media Call to Action.
                - Example: "Follow us for more {niche} stories and daily discoveries!"
                - **FORBIDDEN**: Do NOT say "Check out our full documentary", "Watch the full video", or "Link in bio". We do NOT have a full video. Keep it short.
            
            7. **NARRATION ('text')**:
                - Scene 1 MUST be a "Hook". (e.g., "Stop scrolling, you need to see this.")
                - Keep sentences punchy and conversational.
            
            OUTPUT FORMAT (JSON ONLY):
            {{
                "title": "Viral Title Here",
                "description": "Short summary...",
                "hashtags": "#Tag1 #Tag2",
                "tags": "tag1, tag2, tag3",
                "scenes": [
                    {{
                        "text": "Scientists have made a discovery.",
                        "keywords": ["Scientist", "Lab"],
                        "image_count": 1
                    }}
                ]
            }}
        """

        try:
            print(f"🧠 Groq Director: Segmenting {niche.upper()} story...")

            # CALL GROQ API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    # System prompt ensures it forces JSON mode
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that outputs ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                response_format={
                    "type": "json_object"
                },  # Groq supports native JSON mode!
            )

            response_content = chat_completion.choices[0].message.content
            data = self.repair_json(response_content)

            if not data or "scenes" not in data:
                raise ValueError("Invalid JSON structure from AI")

            # 🟢 Create Metadata File (Same as before)
            meta_filename = f"metadata_{task['_id']}.txt"
            metadata_content = f"""
                ===================================================
                🚀 YOUTUBE UPLOAD METADATA
                ===================================================
                📌 TITLE: {data.get('title')}
                📝 DESCRIPTION: {data.get('description')}
                👇 Read the full story here: {source_url}
                ---------------------------------------------------
                🔥 HASHTAGS: {data.get('hashtags')}
                🏷️ TAGS: {data.get('tags')}
                ---------------------------------------------------
                """
            with open(meta_filename, "w", encoding="utf-8") as f:
                f.write(metadata_content)

            # Update Database
            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script_data": data["scenes"],
                        "title": data.get("title", task["title"]),
                        "ai_description": data.get("description"),
                        "ai_hashtags": data.get("hashtags"),
                        "ai_tags": data.get("tags"),
                        "status": "scripted",
                    }
                },
            )
            print(f"✅ Script Segmented: {len(data['scenes'])} scenes created.")

        except Exception as e:
            print(f"❌ Brain Error: {e}")
