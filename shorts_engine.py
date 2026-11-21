import os
import sys
import re
import json
import shutil
import subprocess
import wave

try:
    import numpy as np
except ImportError:
    np = None

from PIL import Image, ImageDraw, ImageFont

FFMPEG_BIN = shutil.which("ffmpeg") or (
    "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
)

FONT_IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
FONT_ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_HELVETICA = "/System/Library/Fonts/Helvetica.ttc"

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>| ]', '_', name)

def cleanup_old_files(directories=None, max_age_hours=24):
    """Deletes generated videos and temp files older than max_age_hours to save storage."""
    if directories is None:
        directories = ["output_shorts", "downloads", "temp_overlays"]
    import time
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    for d in directories:
        if os.path.exists(d):
            for filename in os.listdir(d):
                filepath = os.path.join(d, filename)
                try:
                    if os.path.isfile(filepath) and not filename.startswith("."):
                        if os.path.getmtime(filepath) < cutoff:
                            os.remove(filepath)
                except Exception:
                    pass

def get_font(path, size):
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
            
    # Fallback paths for macOS & Linux (Ubuntu / Hugging Face Spaces)
    fallbacks = [
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]
    for fb in fallbacks:
        if os.path.exists(fb):
            try:
                return ImageFont.truetype(fb, size)
            except Exception:
                continue
    return ImageFont.load_default()

def generate_ambient_beat(duration=75, output_path="ambient_beat.wav", style="tension"):
    """
    Synthesizes a copyright-free, rhythmic anti-claim backing beat.
    Features punchy kicks, crisp snares, 16th-note hi-hats, and atmospheric sub-chords.
    Works seamlessly with NumPy or 100% Pure Python fallback.
    """
    sr = 44100
    if np is not None:
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        bpm = 124.0
        spb = 60.0 / bpm
        
        # 1. Punchy Kick: on every beat
        kick_t = t % spb
        kick_env = np.exp(-kick_t * 16.0) * (kick_t < 0.28)
        kick_f = 45.0 + 95.0 * np.exp(-kick_t * 28.0)
        kick = np.sin(2 * np.pi * kick_f * kick_t) * kick_env * 0.65
        
        # 2. Snare / Clap: on beats 1 and 3
        snare_phase = (t + spb) % (2 * spb)
        snare_env = np.exp(-snare_phase * 20.0) * (snare_phase < 0.22)
        noise = np.random.uniform(-1, 1, len(t))
        snare = (noise * 0.75 + np.sin(2 * np.pi * 190.0 * t) * 0.25) * snare_env * 0.40
        
        # 3. Crisp Hi-hats: 16th notes
        hat_phase = t % (spb / 4)
        hat_env = np.exp(-hat_phase * 70.0) * (hat_phase < 0.08)
        hat = noise * hat_env * 0.18
        
        # 4. Cinematic Bass & Lo-fi progression
        chord_time = (t % (spb * 16))
        bass_freq = np.where(chord_time < spb * 4, 73.4,
                    np.where(chord_time < spb * 8, 65.4,
                    np.where(chord_time < spb * 12, 87.3, 58.27)))
        drone = np.sin(2 * np.pi * bass_freq * t) * 0.15 + np.sin(2 * np.pi * (bass_freq * 1.5) * t) * 0.08
        
        mix = kick + snare + hat + drone
        mix = mix / (np.max(np.abs(mix)) + 1e-6) * 0.65
        
        pcm = (mix * 32767).astype(np.int16)
        stereo = np.column_stack([pcm, pcm]).flatten()
        
        with wave.open(output_path, "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(sr)
            f.writeframes(stereo.tobytes())
        return output_path
    else:
        # Zero-dependency Pure Python fallback
        import math, random, struct
        num_samples = int(sr * duration)
        bpm = 124.0
        spb = 60.0 / bpm
        samples = []
        for i in range(num_samples):
            t = i / sr
            kick_t = t % spb
            if kick_t < 0.28:
                kick_env = math.exp(-kick_t * 16.0)
                kick_f = 45.0 + 95.0 * math.exp(-kick_t * 28.0)
                kick = math.sin(2 * math.pi * kick_f * kick_t) * kick_env * 0.65
            else:
                kick = 0.0
                
            snare_phase = (t + spb) % (2 * spb)
            if snare_phase < 0.22:
                snare_env = math.exp(-snare_phase * 20.0)
                noise = random.uniform(-1, 1)
                snare = (noise * 0.75 + math.sin(2 * math.pi * 190.0 * t) * 0.25) * snare_env * 0.40
            else:
                snare = 0.0
                
            hat_phase = t % (spb / 4)
            if hat_phase < 0.08:
                hat_env = math.exp(-hat_phase * 70.0)
                noise = random.uniform(-1, 1)
                hat = noise * hat_env * 0.18
            else:
                hat = 0.0
                
            chord_time = t % (spb * 16)
            if chord_time < spb * 4:
                bass_freq = 73.4
            elif chord_time < spb * 8:
                bass_freq = 65.4
            elif chord_time < spb * 12:
                bass_freq = 87.3
            else:
                bass_freq = 58.27
            drone = math.sin(2 * math.pi * bass_freq * t) * 0.15
            
            val = (kick + snare + hat + drone) * 0.6
            val = max(-1.0, min(1.0, val))
            ival = int(val * 32767)
            samples.append(struct.pack('<hh', ival, ival))
            
        with wave.open(output_path, "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(sr)
            f.writeframes(b''.join(samples))
        return output_path

def parse_timestamps_from_text(text):
    """Finds timestamps like 01:30 or 12:45 in description."""
    matches = re.findall(r'(?:(\d{1,2}):)?(\d{2}):(\d{2})\s+([^\n\r]+)', text)
    chapters = []
    for h, m, s, title in matches:
        sec = int(m) * 60 + int(s)
        if h:
            sec += int(h) * 3600
        chapters.append({"sec": sec, "title": title.strip()})
    return chapters

def clean_youtube_url(url):
    m = re.search(r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})', url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url.strip()

def download_youtube_video(url, output_dir="downloads", progress_callback=None):
    os.makedirs(output_dir, exist_ok=True)
    clean_url = clean_youtube_url(url)
    
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "ignore"
    python_bin = sys.executable or "python3"
    
    # Priority strategy: Android client with universal format 18 completely bypasses
    # YouTube BotGuard, SABR streaming & 403 Forbidden on AWS / Streamlit Cloud without PO-Token
    client_strategies = [
        {"client": "android", "fmt": "18/best[ext=mp4]/best"},
        {"client": "android", "fmt": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"},
        {"client": "android_vr", "fmt": "18/best"},
        {"client": "web,mweb", "fmt": "best"}
    ]

    # Check for optional cookies in Streamlit Secrets or local cookies.txt
    cookie_path = None
    try:
        import streamlit as st
        if "YOUTUBE_COOKIES" in st.secrets and len(st.secrets["YOUTUBE_COOKIES"].strip()) > 20:
            cookie_path = os.path.join(output_dir, "cloud_cookies.txt")
            with open(cookie_path, "w") as f:
                f.write(st.secrets["YOUTUBE_COOKIES"])
    except Exception:
        pass
    if not cookie_path and os.path.exists("cookies.txt"):
        cookie_path = "cookies.txt"

    info = None
    last_err = None

    # Step 1: Fetch Video Metadata
    for strat in client_strategies:
        info_cmd = [
            python_bin, "-m", "yt_dlp",
            "--dump-json",
            "--no-warnings",
            "--no-check-certificates",
            "--geo-bypass",
            "--extractor-args", f"youtube:player_client={strat['client']}",
            clean_url
        ]
        if cookie_path and strat['client'] != "android":
            info_cmd.extend(["--cookies", cookie_path])

        p_info = subprocess.run(info_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        if p_info.returncode == 0:
            raw_out = p_info.stdout.strip()
            json_str = None
            for line in reversed(raw_out.split('\n')):
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    json_str = line.strip()
                    break
            if not json_str:
                json_str = raw_out
            try:
                info = json.loads(json_str)
                break
            except Exception:
                pass
        else:
            last_err = p_info.stderr

    if not info:
        raise RuntimeError(f"Failed to fetch video metadata: {last_err}")

    video_id = info.get("id")
    video_path = os.path.join(output_dir, f"{video_id}.mp4")

    # Step 2: Download Video Data
    if not os.path.exists(video_path):
        if progress_callback:
            progress_callback(f"Downloading: {info.get('title')}...")
        
        download_success = False
        for strat in client_strategies:
            dl_cmd = [
                python_bin, "-m", "yt_dlp",
                "-f", strat["fmt"],
                "--no-warnings",
                "--no-check-certificates",
                "--geo-bypass",
                "--extractor-args", f"youtube:player_client={strat['client']}",
                "-o", video_path,
                clean_url
            ]
            if cookie_path and strat['client'] != "android":
                dl_cmd.extend(["--cookies", cookie_path])

            p_dl = subprocess.run(dl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            if p_dl.returncode == 0 and os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                download_success = True
                break
            else:
                last_err = p_dl.stderr
        
        if not download_success:
            err_str = str(last_err)
            if "Sign in to confirm you’re not a bot" in err_str or "Sign in to confirm you're not a bot" in err_str or "403" in err_str:
                raise RuntimeError(
                    "YouTube Bot Protection Active: Cloud server (AWS) ka IP YouTube ne bot samajh kar block kiya hai.\n"
                    "💡 Solution: Kripya '📁 Upload Video File' tab se video file select karein, ya Local App / Wi-Fi use karein!"
                )
            raise RuntimeError(f"Download failed: {last_err}")
            
    return video_path, info

def get_local_video_info(video_path, custom_title=None):
    """Extracts duration and metadata from a local or uploaded video file."""
    duration = 300.0
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip():
            duration = float(res.stdout.strip())
    except Exception:
        pass
        
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    title = custom_title if custom_title else base_name.replace("_", " ").replace("-", " ").title()
    return {
        "id": base_name,
        "title": title,
        "duration": duration,
        "description": f"Uploaded video: {title}"
    }

def sanitize_hook_text(text):
    """Sanitizes text to remove episode numbers or official copyright patterns."""
    if not text:
        return "VIRAL MOMENT"
    clean = re.sub(r'(?i)(episode\s*\d+|ep\s*\d+|season\s*\d+|s\d+\s*ep\d+|ft\.?[^,\n]+)', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:28].upper() if clean else "VIRAL MOMENT"

def detect_video_genre_and_context(info):
    """
    Detects creator, genre, mood, and relevant keywords from video metadata.
    Supported genres:
    - funny_roast: CarryMinati, comedy, roast, gaming rage, meme, standup
    - motivational_emotional: life lesson, emotional, inspirational, struggle, wisdom
    - gaming: gameplay, clutch, pro player, gta, pubg, bgmi, free fire
    - podcast_interview: raw conversation, truth reveal, exposed, dark reality
    - horror_mystery: spooky, scary, 3am, paranormal, mystery
    - tech_review: gadgets, smartphone, ai, unboxing, tricks
    - devotional_spiritual: bhajan, katha, krishna, shiva, ram, temple, aarti
    - general_trending: tailored to main subject
    """
    if not isinstance(info, dict):
        info = {"title": str(info)}
    title = str(info.get("title", "")).strip()
    channel = str(info.get("channel", info.get("uploader", ""))).strip()
    desc = str(info.get("description", ""))[:1500].lower()
    combined_text = f"{title} {channel} {desc}".lower()

    # Identify primary creator / subject name if prominent
    creator_name = ""
    for c in ["carryminati", "carryislive", "carry", "samay raina", "bhuvan bam", "bb ki vines", 
              "ashish chanchlani", "round2hell", "r2h", "triggered insaan", "fukra insaan",
              "sandeep maheshwari", "khan sir", "ojha sir", "vikas divyakirti", "sonu sharma",
              "dhruv rathee", "beerbiceps", "ranveer allahbadia", "tanmay bhat", "mortal", "scout",
              "total gaming", "techno gamerz", "mythpat"]:
        if c in combined_text:
            creator_name = c.title()
            break

    # Genre determination
    if any(k in combined_text for k in ["carryminati", "carryislive", "roast", "funny", "comedy", "meme", "hasna", "lmao", "lol", "standup", "bassi", "samay raina", "chutkula", "prank", "triggered insaan", "fukra insaan"]):
        genre = "funny_roast"
    elif any(k in combined_text for k in ["motivat", "inspira", "emotion", "sad", "tears", "cry", "life lesson", "truth", "reality", "struggle", "success", "upsc", "ias", "sandeep maheshwari", "khan sir", "ojha sir", "divyakirti", "mindset", "seekh"]):
        genre = "motivational_emotional"
    elif any(k in combined_text for k in ["gameplay", "gta", "bgmi", "pubg", "free fire", "minecraft", "clutch", "headshot", "esports", "total gaming", "techno gamerz", "gaming"]):
        genre = "gaming"
    elif any(k in combined_text for k in ["podcast", "interview", "beerbiceps", "ranveer", "unfiltered", "secrets", "untold", "exposed", "scam", "case study", "dark reality", "conversation"]):
        genre = "podcast_interview"
    elif any(k in combined_text for k in ["horror", "scary", "ghost", "bhoot", "chudail", "paranormal", "haunted", "creepy", "mystery", "3 am", "darr"]):
        genre = "horror_mystery"
    elif any(k in combined_text for k in ["iphone", "smartphone", "unboxing", "review", "gadget", "laptop", "android", "tech", "ai tool"]):
        genre = "tech_review"
    elif any(k in combined_text for k in ["bhajan", "katha", "ram", "krishna", "shiva", "hanuman", "aarti", "mandir", "temple", "spiritual"]):
        genre = "devotional_spiritual"
    else:
        genre = "general_trending"

    # Extract clean subject from title
    clean_title = re.sub(r'\[.*?\]|\(.*?\)|(?i)(official video|full video|4k|hd|trailer|teaser|full episode|first time)', '', title).strip()
    clean_title = re.sub(r'\s+', ' ', clean_title)
    
    return {
        "genre": genre,
        "creator": creator_name or channel,
        "clean_title": clean_title,
        "raw_title": title,
        "channel": channel
    }

def select_clip_moments(info, num_shorts=8, target_duration=45, gemini_api_key=None):
    """Identifies top segments using chapters/description, Gemini AI, or Context-Aware intervals."""
    description = info.get("description", "")
    duration = info.get("duration", 600)
    chapters = parse_timestamps_from_text(description)
    ctx = detect_video_genre_and_context(info)
    genre = ctx["genre"]
    creator = ctx["creator"]
    clean_title = ctx["clean_title"]

    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"""You are a top viral YouTube Shorts strategist and video editor.
Analyze this video metadata:
Title: {info.get('title')}
Creator/Channel: {ctx['creator']}
Detected Genre/Style: {genre}
Total Duration: {duration} seconds
Description snippet: {description[:1200]}

Select {num_shorts} best viral clips of duration {target_duration} seconds each.
CRITICAL INSTRUCTIONS:
1. The hooks, titles and descriptions MUST specifically match the video theme (e.g. if CarryMinati / Funny -> high-energy comedy, savage roasts, funny punchlines; if Motivational/Emotional -> deep, inspiring, heart-touching hooks; if Gaming -> insane clutch/rage moments).
2. DO NOT use generic placeholder text. Reflect the actual video subject!
3. For copyright safety, do not put raw TV episode numbers in overlay titles.

Return ONLY valid JSON array of {num_shorts} objects with keys:
- "start_sec": integer seconds start (between 0 and {max(0, int(duration - target_duration))})
- "duration_sec": integer duration (around {target_duration})
- "tag": short badge tag (e.g. "SAVAGE ROAST", "EPIC MOMENT", "GOLDEN WORDS", "UNREAL SCENE")
- "title1": catchy top hook line (uppercase, max 26 chars)
- "title2": catchy bottom hook line (uppercase, max 26 chars)
- "subtitle": curiosity text (max 35 chars)
- "description": transformative viral YouTube Shorts description
"""
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            raw = response.text.strip()
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            clips = json.loads(raw)
            if isinstance(clips, list) and len(clips) > 0:
                return clips[:num_shorts]
        except Exception as e:
            print("Gemini API call failed, falling back to smart context heuristic:", e)

    # Curated contextual hooks for up to 10 clips per genre
    c_up = (creator or "CARRY").upper()[:12]
    HOOK_PACKS = {
        "funny_roast": [
            {"tag": "SAVAGE ROAST", "t1": f"{c_up}'S SAVAGE ROAST! 😂", "t2": "HE DID NOT HOLD BACK! 🔥", "sub": "Funniest Reaction Moment"},
            {"tag": "COMEDY GOLD", "t1": "UNSTOPPABLE LAUGHTER! 🤣", "t2": "BHAI NE SYSTEM HILA DIYA 💀", "sub": "Pure Comedy Scene"},
            {"tag": "EPIC FAIL", "t1": "INSTANT REGRET MOMENT! 😭", "t2": "HE WAS NOT READY FOR THIS! 😂", "sub": "Hilarious Twist"},
            {"tag": "SAVAGE MODE", "t1": "ULTRA SAVAGE COMEBACK! 💀", "t2": "NOBODY SAW THIS COMING! 🔥", "sub": "Roast Breakdown"},
            {"tag": "PURE CHAOS", "t1": "PURE COMEDY CHAOS! 🤣", "t2": "HAS HAS KE BURA HAAL! 😭", "sub": "Non Stop Laughs"},
            {"tag": "BEAST MODE", "t1": "HE WENT FULL BEAST MODE! 💀", "t2": "CRAZIEST REACTION EVER! 🔥", "sub": "Wild Gaming & Roast"},
            {"tag": "MEME LEVEL", "t1": "THE ULTIMATE MEME SCENE! 😂", "t2": "WAIT FOR THE PUNCHLINE! 🤣", "sub": "Legendary Dialogue"},
            {"tag": "BEST OF BEST", "t1": "CLIMAX PE DHAMAKA! 💥", "t2": "WATCH TILL THE VERY END! 😱", "sub": "Final Shocking Scene"},
            {"tag": "UNBELIEVABLE", "t1": "HOW DID HE SAY THAT?! 💀", "t2": "TOO FUNNY TO MISS! 🤣", "sub": "Unexpected Moment"},
            {"tag": "VIRAL FINALE", "t1": "TOP MOMENT OF THE YEAR! 🔥", "t2": "SHARE THIS WITH FRIENDS! 😂", "sub": "Masterpiece Clip"}
        ],
        "motivational_emotional": [
            {"tag": "GOLDEN WORDS", "t1": "LIFE CHANGING ADVICE! 🥺", "t2": "LISTEN CAREFULLY TO THIS! 💯", "sub": "Deep Life Reality"},
            {"tag": "GOOSEBUMPS", "t1": "GOOSEBUMPS GUARANTEED! ⚡", "t2": "YEH BAAT DIL KO CHHU GAYI ❤️", "sub": "Heart Touching Truth"},
            {"tag": "REALITY CHECK", "t1": "HARDEST TRUTH OF LIFE! 💔", "t2": "NOBODY WILL TELL YOU THIS 💯", "sub": "Eye Opening Lesson"},
            {"tag": "NEVER GIVE UP", "t1": "NEVER GIVE UP IN LIFE! 🔥", "t2": "STRUGGLE TO SUCCESS STORY 🏆", "sub": "Inspiring Transformation"},
            {"tag": "PURE EMOTION", "t1": "ROTE HUE BHI MUSKURAOGE! 😢", "t2": "DEEPEST EMOTIONAL SCENE ❤️", "sub": "Soul Touching Words"},
            {"tag": "SUCCESS MINDSET", "t1": "APNE DUM PAR JEENA SIKHO! ⚡", "t2": "POWERFUL MINDSET 💎", "sub": "Life Lessons For You"},
            {"tag": "TRUE LESSON", "t1": "KABHI DEPEND MAT HONA! 💔", "t2": "AANKHEN KHOL DENE WALI BAAT 👁️", "sub": "Crucial Advice"},
            {"tag": "MASTERPIECE", "t1": "YEH SUN KAR RO DOGE! 🥺❤️", "t2": "MOST INSPIRING MOMENT EVER! 🌟", "sub": "Final Golden Words"},
            {"tag": "DEEP WISDOM", "t1": "ZINDAGI KA KADWA SACH! 💯", "t2": "REMEMBER THIS FOREVER 🔥", "sub": "Powerful Realization"},
            {"tag": "FINAL LESSON", "t1": "DON'T LOSE HOPE EVER! ⚡", "t2": "YOUR TIME WILL COME! 🏆", "sub": "Ultimate Motivation"}
        ],
        "gaming": [
            {"tag": "GOD CLUTCH", "t1": "1V4 IMPOSSIBLE CLUTCH! 🔥", "t2": "GOD LEVEL GAMEPLAY! 🎮", "sub": "Pro Gamer Moment"},
            {"tag": "HEADSHOT", "t1": "MOST INSANE HEADSHOT! 💀", "t2": "ENEMY HAD ZERO CHANCE! ⚡", "sub": "Clean Elimination"},
            {"tag": "FUNNY GLITCH", "t1": "HE WAS NOT READY FOR THIS! 😱", "t2": "HILARIOUS GAMING MOMENT! 😂", "sub": "Epic Game Moment"},
            {"tag": "GAMING RAGE", "t1": "ULTRA RAGE MOMENT! 😡💀", "t2": "KEYBOARD TOD DIYA BHAI! 🤣", "sub": "Streamer Goes Wild"},
            {"tag": "SECRET EASTER", "t1": "NEW SECRET UNLOCKED! 🤯", "t2": "HIDDEN DETAIL IN GAME! 🔍", "sub": "Game Discovery"},
            {"tag": "1 HP SURVIVOR", "t1": "SURVIVED ON 1 HP! 😱🔥", "t2": "HEARTBEAT 200 BPM! 💓", "sub": "Extreme Tension"},
            {"tag": "BIG BRAIN", "t1": "IQ 999 GALAXY BRAIN PLAY! 🧠", "t2": "HE OUTSMARTED EVERYONE! 😂", "sub": "Pro Mindset"},
            {"tag": "VICTORY ROYALE", "t1": "THE FINAL SHOWDOWN! 🏆", "t2": "WHAT AN INSANE FINISH! 💥", "sub": "Victory Moment"},
            {"tag": "EPIC MOMENT", "t1": "UNBELIEVABLE MOVE! ⚡", "t2": "CRAZIEST PLAY OF THE MATCH! 🎮", "sub": "Highlight Reel"},
            {"tag": "LEGENDARY", "t1": "TOP TIER GAMING MOMENT! 🌟", "t2": "LOOK AT THAT PRECISION! 🔥", "sub": "Master Gamer"}
        ],
        "podcast_interview": [
            {"tag": "SHOCKING TRUTH", "t1": "SHOCKING TRUTH REVEALED! 🤯", "t2": "RAW & UNFILTERED TALK 🎙️", "sub": "Untold Story"},
            {"tag": "DARK REALITY", "t1": "DARK REALITY EXPOSED! 💀", "t2": "NOBODY TALKS ABOUT THIS 🤫", "sub": "Deep Revelation"},
            {"tag": "CONFESSION", "t1": "HE BROKE HIS SILENCE! 🤐", "t2": "FIRST TIME ON CAMERA! 😱", "sub": "Shocking Statement"},
            {"tag": "BIG REVEAL", "t1": "THE BIGGEST REALITY! 💥", "t2": "SACH DEKH KAR DANG REH JAOGE 👁️", "sub": "Eye Opening Fact"},
            {"tag": "DEEP TALK", "t1": "WHY DO PEOPLE HIDE THIS?! 🤔", "t2": "UNBELIEVABLE CONVERSATION ⚡", "sub": "Important Truth"},
            {"tag": "RAW STORY", "t1": "UNHEARD STORY OF STRUGGLE! 🥺", "t2": "BEFORE BECOMING FAMOUS... 💔", "sub": "Emotional Journey"},
            {"tag": "BOLD OPINION", "t1": "UNFILTERED RAW OPINION! 🔥", "t2": "HE DID NOT FEAR ANYONE 💯", "sub": "Courageous Statement"},
            {"tag": "VIRAL MOMENT", "t1": "THE MOST VIRAL ANSWER! 🤯", "t2": "THIS CHANGED EVERYTHING! ⚡", "sub": "Final Masterclip"},
            {"tag": "EYE OPENER", "t1": "EVERYONE SHOULD HEAR THIS! 👂", "t2": "POWERFUL PERSPECTIVE 🌟", "sub": "Key Insight"},
            {"tag": "FINAL WORDS", "t1": "DO NOT IGNORE THIS! 💥", "t2": "BEST PODCAST MOMENT 🎙️", "sub": "Unforgettable Talk"}
        ],
        "general_trending": [
            {"tag": "VIRAL SCENE", "t1": f"{clean_title[:20].upper()}! 🔥", "t2": "WAIT FOR THE BEST PART! 😱", "sub": "Trending Moment"},
            {"tag": "UNBELIEVABLE", "t1": "NOBODY SAW THIS COMING! 🤯", "t2": "DID YOU NOTICE THIS?! ⚡", "sub": "Shocking Detail"},
            {"tag": "MUST WATCH", "t1": "MOST VIRAL MOMENT! 🍿", "t2": "CRAZY SCENE HAPPENED! 💥", "sub": "Top Highlight"},
            {"tag": "TWIST ENDING", "t1": "WAIT FOR THE HUGE TWIST! 😱", "t2": "HE COULD NOT BELIEVE IT! 💀", "sub": "Unexpected Ending"},
            {"tag": "TOP HIGHLIGHT", "t1": "BEST PART OF THE VIDEO! 🌟", "t2": "WATCH TILL THE VERY END! 🔥", "sub": "Highlight Segment"},
            {"tag": "EPIC MOMENT", "t1": "THIS BROKE THE INTERNET! ⚡", "t2": "HUNDREDS ARE SHOCKED! 😲", "sub": "Viral Sensation"},
            {"tag": "CRAZY SCENE", "t1": "CAN YOU BELIEVE THIS?! 🤯", "t2": "LOOK AT WHAT HAPPENED! 💥", "sub": "Unreal Clip"},
            {"tag": "THE FINALE", "t1": "THE ULTIMATE CLIMAX! 🏆", "t2": "MOST TALKED ABOUT SCENE! 🔥", "sub": "Final Peak Moment"},
            {"tag": "EXTRA VIRAL", "t1": "DON'T MISS THIS CLIP! 👀", "t2": "EVERYONE IS TALKING ABOUT IT! 💬", "sub": "Buzz Scene"},
            {"tag": "EPIC FINISH", "t1": "THE CRAZIEST FINISH! 💥", "t2": "SHARE THIS WITH FRIENDS! 🔥", "sub": "Ultimate Ending"}
        ]
    }

    hooks_list = HOOK_PACKS.get(genre, HOOK_PACKS["general_trending"])
    clips = []

    # Calculate safe start times across the full video duration
    if duration <= target_duration + 5:
        # Very short video
        for i in range(num_shorts):
            h = hooks_list[i % len(hooks_list)]
            clips.append({
                "start_sec": 0,
                "duration_sec": max(5, int(duration)),
                "tag": h["tag"],
                "title1": h["t1"],
                "title2": h["t2"],
                "subtitle": h["sub"],
                "description": f"{h['t1']} - {clean_title} #Shorts #Viral"
            })
    elif len(chapters) >= num_shorts:
        step = max(1, len(chapters) // num_shorts)
        for i in range(num_shorts):
            idx = min(i * step, len(chapters) - 1)
            ch = chapters[idx]
            st = ch["sec"]
            if st + target_duration > duration:
                st = max(0, duration - target_duration - 2)
            h = hooks_list[i % len(hooks_list)]
            clean_ch = sanitize_hook_text(ch["title"])
            clips.append({
                "start_sec": int(st),
                "duration_sec": target_duration,
                "tag": h["tag"],
                "title1": clean_ch if len(clean_ch) > 4 else h["t1"],
                "title2": h["t2"],
                "subtitle": h["sub"],
                "description": f"{clean_ch} - {clean_title} #Shorts #Viral"
            })
    else:
        # Smart interval division across duration for num_shorts
        available_time = max(0, duration - target_duration - 5)
        interval = available_time / max(1, num_shorts)
        for i in range(num_shorts):
            st = int(interval * i + (interval * 0.15))
            st = max(0, min(st, int(duration - target_duration - 2)))
            h = hooks_list[i % len(hooks_list)]
            clips.append({
                "start_sec": st,
                "duration_sec": target_duration,
                "tag": h["tag"],
                "title1": h["t1"],
                "title2": h["t2"],
                "subtitle": h["sub"],
                "description": f"{h['t1']} - {clean_title} #Shorts #Viral"
            })
    return clips[:num_shorts]

def generate_rich_clip_metadata(clip, main_video_title, info=None, gemini_api_key=None):
    """
    Generates 3 Viral Title Options, Rich Description, and Pinned Comment.
    Context-aware for CarryMinati, Comedy, Motivational, Emotional, Gaming, Podcasts, etc.
    """
    title1 = clip.get("title1", "VIRAL MOMENT")
    title2 = clip.get("title2", "MUST WATCH")
    sub = clip.get("subtitle", "Trending Moment")

    ctx = detect_video_genre_and_context(info if info else {"title": main_video_title})
    genre = ctx["genre"]
    creator = ctx["creator"] or "Creator"
    clean_title = ctx["clean_title"] or main_video_title

    # 1. Try Gemini AI if API key is provided
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"""You are a master viral YouTube Shorts strategist.
Video Subject: {main_video_title}
Creator / Channel: {creator}
Detected Style/Tone: {genre}
Short Clip Focus: {title1} - {title2}
Clip Tag: {clip.get('tag', 'VIRAL')}

CRITICAL INSTRUCTIONS:
- Tailor the 3 Title Options and Description SPECIFICALLY to this video style:
  * If Comedy/Roast (like CarryMinati): energetic, savage, laughing emojis (😂, 🤣, 💀), high-energy hooks.
  * If Motivation/Emotional: deep, inspiring, heart-touching curiosity hooks (🥺, 💔, ❤️, 💯, ⚡).
  * If Gaming: clutch, insane rage, pro gameplay hooks (🎮, 🔥, 💀).
  * If Podcast/Interview: raw truth, untold confession, mystery reveal hooks (🎙️, 🤯, 🤫).
- Avoid generic placeholders like "Wait For The Twist". Use the actual creator or subject context!
- Keep each title under 65 chars with emojis and #Shorts.

Generate JSON with:
- "title_options": [
    {{"type": "High CTR", "title": "Catchy headline with emojis and #Shorts (max 65 chars)"}},
    {{"type": "Curiosity Hook", "title": "Intriguing question headline with emojis and #Shorts (max 65 chars)"}},
    {{"type": "Hindi Mix", "title": "Desi Hindi / Hinglish hook title with emojis (max 65 chars)"}}
  ],
- "description": "Full YouTube Shorts description with hook, breakdown summary, engagement question, CTA, 8-10 trending relevant hashtags, and Section 107 Fair Use disclaimer.",
- "pinned_comment": "Engaging question for viewers to comment on"
"""
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            raw = res.text.strip()
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            data = json.loads(raw)
            if "title_options" in data and "description" in data:
                return data
        except Exception as e:
            print("Gemini metadata generation failed, using algorithmic fallback:", e)

    # 2. Algorithmic Context-Aware Fallback (Specific to Creator & Genre)
    subj = creator if (creator and creator.lower() not in ["creator", "uploaded video"]) else clean_title[:24]

    if genre == "funny_roast":
        opt1 = f"{subj} Ka Savage Roast! 😂🔥 Wait For The End! #Shorts #Viral"
        opt2 = f"Bhai Ne To System Hila Ke Rakh Diya! 🤣💀 #Shorts #Comedy"
        opt3 = f"{subj} Ka Yeh Scene Dekh Kar Hasi Nahi Rukegi! 😭 #CarryMinati #Funny"
        desc = f"""{subj} - Pure comedy and savage moments! 😂🔥

Yeh wala scene dekh kar aapki hasi nahi rukegi! Watch till the very end for the funniest reaction.

Aapko is video me sabse comedy moment konsa laga? Comment me batayein! 👇

🔔 Subscribe for daily funny reactions, comedy roasts, and trending viral shorts!

#Shorts #Viral #Comedy #Funny #CarryMinati #Roast #LMAO #TrendingShorts #Entertainment #Meme

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""
        pinned = "Is clip me sabse funny dialogue konsa laga? 🤣👇 Comment karein!"

    elif genre == "motivational_emotional":
        opt1 = f"Life Changing Words! 🥺💔 Goosebumps Guaranteed ⚡ #Shorts #Motivation"
        opt2 = f"Yeh Baat Har Kisi Ko Samajh Nahi Aayegi... 💯❤️ #LifeLessons"
        opt3 = f"{subj} Ki Yeh Seekh Sun Kar Aankhon Me Aansu Aa Jayenge 😢 #Inspirational"
        desc = f"""{clean_title} - Words that touch your soul! 🥺❤️

A life-changing perspective that everyone needs to hear today. Remember, your struggle will define your success.

Kya aap is baat se sehmat hain? Apne vichar comment box me zaroor share karein! 👇

🔔 Subscribe for daily life motivation, inspiring lessons, and deep wisdom!

#Shorts #Viral #Motivation #Inspirational #LifeLessons #Emotional #Success #Mindset #Quotes #TrueWords

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""
        pinned = "Kya aap is baat se sehmat hain? Apni rai comment me zaroor batayein ❤️👇"

    elif genre == "gaming":
        opt1 = f"1v4 Impossible Clutch Moment! 🔥🎮 God Level Gameplay #Shorts"
        opt2 = f"{subj} - Most Insane Reaction Ever! 😱💀 #Gaming #Viral"
        opt3 = f"Enemy Team Ki Dhajjiyan Uda Di! 🤣💥 #Shorts #GamingClips"
        desc = f"""{clean_title} - Insane gameplay highlights! 🎮🔥

Look at that precision, clutch decision making, and unbelievable finish!

Kya aap aisi situation me clutch nikaal pate? Yes ya No me answer dein! 👇

🔔 Subscribe for pro gaming clutches, funny gaming moments, and live highlights!

#Shorts #Gaming #Gameplay #Clutch #ProGamer #GTA #BGMI #GamingHighlights #Viral

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""
        pinned = "Kya aap aisi situation me clutch nikaal sakte the? Yes or No? 🎮👇"

    elif genre == "podcast_interview":
        opt1 = f"Shocking Truth Revealed In Podcast! 🤯🎙️ #Shorts #Viral"
        opt2 = f"{subj} - Unhone Yeh Baat National Media Par Bol Di?! 😱 #RealTalk"
        opt3 = f"Dark Reality That Nobody Talks About! 💀🤫 #Podcast #Exposed"
        desc = f"""{clean_title} - Untold reality and eye-opening revelation! 🎙️🤯

A deep and unfiltered conversation about what really happens behind closed doors.

Kya aap inki baat se agree karte hain? Sach batana! 👇

🔔 Subscribe for unfiltered podcast highlights, truth revelations, and deep conversations!

#Shorts #Podcast #Interview #RealTalk #Truth #Exposed #UntoldStory #Trending

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""
        pinned = "Kya aap inki baat se agree karte hain? Sach batana! 🎙️👇"

    elif genre == "horror_mystery":
        opt1 = f"Real Ghost Caught On Camera?! 😱👻 #Shorts #Scary"
        opt2 = f"Wait For What Happened At 3:00 AM... 💀😨 #Horror #Viral"
        opt3 = f"Is Video Ko Raat Me Akele Mat Dekhna! 😭⚡ #Mystery #Creepy"
        desc = f"""{clean_title} - Chilling paranormal mystery! 👻😱

Notice the strange anomaly at the end of this clip. Do not watch alone with headphones!

Did you spot anything unusual? Tell us in the comments! 👇

#Shorts #Horror #Scary #Ghost #Paranormal #Mystery #Creepy #ViralShorts

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""
        pinned = "Aapko kya laga, kya yeh sach me paranormal tha? 😱👇"

    else:
        # General Trending (using clean subject)
        hook_clean = clean_text_for_font(title1).title() if title1 else clean_title[:24]
        opt1 = f"{subj[:26]} - Most Insane Scene! 😱🔥 #Shorts #Viral"
        opt2 = f"Did You Notice THIS in The Video?! 🤯⚡ #Shorts #Trending"
        opt3 = f"{subj[:24]} Dekh Kar Sab Hairaan Ho Gaye! 💥🍿 #Viral #Shorts"
        desc = f"""{clean_title} - You won't believe what happened here! 😱🔥

Watch the most viral and thrilling breakdown of this trending scene that everyone is talking about!

What was your favorite moment in this clip? Tell us in the comments! 👇

🔔 Subscribe for daily viral moments, commentary reactions, and trending shorts!

#Shorts #Viral #Trending #Entertainment #YouTubeShorts #MustWatch #EpicMoment #TrendingNow

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""
        pinned = "Aapko is video me sabse best part konsa laga? Comment me batayein! 👇"

    return {
        "title_options": [
            {"type": "High CTR", "title": opt1},
            {"type": "Curiosity Hook", "title": opt2},
            {"type": "Hindi Mix", "title": opt3}
        ],
        "description": desc,
        "pinned_comment": pinned
    }

def clean_text_for_font(text):
    if not text:
        return ""
    clean = re.sub(r'[^\x00-\x7F]+', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def create_overlay_png(config, output_path, theme="gold"):
    width, height = 1080, 1920
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    f_title1 = get_font(FONT_IMPACT, 50)
    f_title2 = get_font(FONT_IMPACT, 58)
    f_tag = get_font(FONT_IMPACT, 28)
    f_sub = get_font(FONT_ARIAL, 32)
    f_cta = get_font(FONT_IMPACT, 40)
    f_disc = get_font(FONT_ARIAL, 22)

    outline_color = (255, 215, 0, 230) if theme == "gold" else (0, 230, 255, 230)
    accent_title = (255, 215, 0, 255) if theme == "gold" else (0, 230, 255, 255)

    tag_text = clean_text_for_font(config.get("tag", "EXCLUSIVE"))
    title1_text = clean_text_for_font(config.get("title1", "WAIT FOR THE END!"))
    title2_text = clean_text_for_font(config.get("title2", "VIRAL MOMENT"))
    sub_text = clean_text_for_font(config.get("subtitle", "Trending Moment"))

    # 1. Top Badge
    draw.rounded_rectangle([400, 140, 680, 190], radius=12, fill=(230, 36, 41, 240))
    draw.text((540, 165), tag_text, font=f_tag, fill=(255, 255, 255, 255), anchor="mm")

    # 2. Main Title Header Card
    draw.rounded_rectangle([50, 210, 1030, 410], radius=24, fill=(16, 18, 24, 225), outline=outline_color, width=4)
    draw.text((540, 268), title1_text, font=f_title1, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((540, 345), title2_text, font=f_title2, fill=accent_title, anchor="mm")

    # 3. Center Video Accent Lines (Removed so video is clean and unobstructed)

    # 4. Bottom Subtitle Card
    draw.rounded_rectangle([60, 1510, 1020, 1605], radius=18, fill=(20, 22, 28, 225), outline=(230, 36, 41, 230), width=3)
    draw.text((540, 1557), sub_text, font=f_sub, fill=(255, 255, 255, 255), anchor="mm")

    # 5. Call to Action
    draw.text((540, 1655), "WAIT FOR THE END!", font=f_cta, fill=(255, 220, 50, 255), anchor="mm")
    draw.text((540, 1715), "SUBSCRIBE FOR DAILY VIRAL SHORTS", font=f_sub, fill=(210, 210, 210, 220), anchor="mm")

    # 6. Fair Use Tag
    draw.text((540, 1860), "Transformative Fan Commentary & Fair Use Review", font=f_disc, fill=(160, 160, 160, 180), anchor="mm")

    img.save(output_path, "PNG")
    return output_path

def render_short_video(
    input_video,
    start_sec,
    duration_sec,
    output_file,
    overlay_file,
    beat_file,
    mirror_flip=True,
    zoom_crop=1.12,
    speed_boost=1.065,
    pitch_ratio=1.048,
    audio_mode="vocal_beat"
):
    """
    Renders 9:16 vertical Short with multi-layered Anti-Claim Copyright Shields:
    1. Horizontal Mirror (hflip) - disrupts spatial CNN/SIFT visual fingerprinting.
    2. Smart Zoom & Edge Crop (1.12x) - changes frame boundaries and crops logos.
    3. Temporal Cadence Shift (1.065x speed) - alters frame count, timing, and FPS cadence.
    4. Audio Lip-Sync Pitch & Tempo Desync - shifts pitch (+4.8%) while maintaining exact lip sync.
    5. Vocal Clarity EQ - removes low-end music bass (<120Hz) & highs (>11.5kHz) while boosting human speech.
    6. Audible Anti-Claim Percussion Bed - masks spectrogram peak detection with real transients.
    """
    # 1. Visual Filters Setup
    hflip_filter = "hflip," if mirror_flip else ""
    
    # Crop factor for zoom (e.g. 1.12x zoom -> crop to 1/1.12 = 0.892 of width/height)
    if zoom_crop > 1.0:
        crop_factor = round(1.0 / zoom_crop, 3)
        fg_crop_filter = f"crop=in_w*{crop_factor}:in_h*{crop_factor},"
    else:
        fg_crop_filter = ""

    # Calculate effective output duration after speedup
    speed = max(1.0, float(speed_boost))
    effective_duration = duration_sec / speed

    # 2. Audio Filter Setup
    # net audio tempo must match video speed: total_tempo = speed
    # asetrate changes pitch and speed by pitch_ratio.
    # so subsequent atempo = speed / pitch_ratio
    atempo_val = round(speed / pitch_ratio, 4)

    if audio_mode == "mute_music":
        # Completely mute original video audio, use only copyright-free viral beat bed
        audio_filter_chain = (
            f"[1:a]volume=0.85,loudnorm=I=-16:TP=-1.5:LRA=11[a_out]"
        )
    elif audio_mode == "voice_only":
        # Voice only: pitch-shifted, speed-matched, and EQ-isolated without background beat
        audio_filter_chain = (
            f"[0:a]aresample=44100,asetrate=44100*{pitch_ratio:.4f},"
            f"atempo={atempo_val:.4f},aresample=48000,"
            f"highpass=f=120,lowpass=f=11500,equalizer=f=1200:t=q:w=1:g=2.5,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[a_out]"
        )
    else:
        # Default: vocal_beat (Voice with Vocal EQ + Audible Anti-Claim Beat Layer)
        audio_filter_chain = (
            f"[0:a]aresample=44100,asetrate=44100*{pitch_ratio:.4f},"
            f"atempo={atempo_val:.4f},aresample=48000,"
            f"highpass=f=120,lowpass=f=11500,equalizer=f=1200:t=q:w=1:g=2.5,volume=0.88[v_audio];"
            f"[1:a]volume=0.35[bgm];"
            f"[v_audio][bgm]amix=inputs=2:duration=first:dropout_transition=2,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[a_out]"
        )

    filter_complex = (
        f"[0:v]split=2[bg_in][fg_in];"
        f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.22:contrast=0.9[bg];"
        f"[fg_in]{hflip_filter}{fg_crop_filter}scale=1080:-2,eq=contrast=1.08:brightness=0.01:saturation=1.12:gamma=1.03,unsharp=3:3:0.5[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[comp1];"
        f"[comp1][2:v]overlay=0:0[comp2];"
        f"[comp2]drawbox=x=0:y=1905:w='1080*t/{effective_duration:.2f}':h=15:color=red@0.95:t=fill,setpts=PTS/{speed:.4f}[v_out];"
        f"{audio_filter_chain}"
    )

    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-i", input_video,
        "-i", beat_file,
        "-i", overlay_file,
        "-filter_complex", filter_complex,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-t", f"{effective_duration:.2f}",
        output_file
    ]

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"FFmpeg render error: {p.stderr}")
    return output_file
