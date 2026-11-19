import os
import sys
import re
import json
import shutil
import subprocess
import numpy as np
import wave
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
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
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

def generate_ambient_beat(duration=75, output_path="ambient_beat.wav"):
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # 60 BPM cinematic pulse
    pulse_env = np.maximum(0, np.sin(2 * np.pi * 1.0 * t)) ** 18
    kick = np.sin(2 * np.pi * 55 * t) * pulse_env * 0.45
    
    # Atmospheric drone (D minor)
    d1 = np.sin(2 * np.pi * 73.4 * t) * 0.15
    d2 = np.sin(2 * np.pi * 110.0 * t) * 0.10
    d3 = np.sin(2 * np.pi * 174.6 * t) * 0.08
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.06 * t)
    drone = (d1 + d2 + d3) * mod
    
    # Subtle percussive tick on 8th notes (4 Hz)
    tick_env = np.maximum(0, np.sin(2 * np.pi * 4.0 * t)) ** 64
    noise = np.random.uniform(-0.1, 0.1, len(t))
    tick = noise * tick_env * 0.12
    
    mix = kick + drone + tick
    mix = mix / (np.max(np.abs(mix)) + 1e-6) * 0.5
    
    pcm = (mix * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm]).flatten()
    
    with wave.open(output_path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(stereo.tobytes())
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
    
    # Modern mobile user-agent to bypass cloud/datacenter bot blocks
    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"

    # Multi-client strategy: iOS client bypasses YouTube 403 Forbidden on AWS/Streamlit Cloud
    client_strategies = [
        {"client": "ios,mweb", "fmt": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"},
        {"client": "mweb,android_vr", "fmt": "18/best[ext=mp4]/best"},
        {"client": "android,web", "fmt": "best[ext=mp4]/best"}
    ]

    info = None
    last_err = None

    # Step 1: Fetch Video Metadata
    for strat in client_strategies:
        info_cmd = [
            python_bin, "-m", "yt_dlp",
            "--dump-json",
            "--no-warnings",
            "--user-agent", user_agent,
            "--extractor-args", f"youtube:player_client={strat['client']}",
            clean_url
        ]
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
                "--user-agent", user_agent,
                "--extractor-args", f"youtube:player_client={strat['client']}",
                "-o", video_path,
                clean_url
            ]
            p_dl = subprocess.run(dl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            if p_dl.returncode == 0 and os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                download_success = True
                break
            else:
                last_err = p_dl.stderr
        
        if not download_success:
            raise RuntimeError(f"Download failed: {last_err}")
            
    return video_path, info

def select_clip_moments(info, num_shorts=3, target_duration=45, gemini_api_key=None):
    """Identifies top segments using chapters/description or Gemini AI."""
    description = info.get("description", "")
    duration = info.get("duration", 600)
    chapters = parse_timestamps_from_text(description)
    
    # If Gemini API key is provided, let Gemini pick and create titles
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"""You are a viral YouTube Shorts editor.
Analyze this YouTube video metadata:
Title: {info.get('title')}
Total Duration: {duration} seconds
Description snippet: {description[:1200]}

Please select {num_shorts} best viral clips of duration {target_duration} seconds each.
Return ONLY valid JSON array with keys:
- "start_sec": integer seconds start (between 0 and {duration - target_duration})
- "duration_sec": integer duration (around {target_duration})
- "tag": short badge tag (e.g., "VIRAL MOMENT", "EPIC SCENE")
- "title1": catchy hook line 1 (uppercase, max 30 chars)
- "title2": catchy hook line 2 (uppercase, max 30 chars)
- "subtitle": descriptive context (max 45 chars)
- "description": complete viral YouTube Shorts description with hashtags
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
            print("Gemini API call failed, falling back to smart heuristic:", e)

    # Heuristic / Chapter fallback:
    clips = []
    if len(chapters) >= num_shorts:
        step = max(1, len(chapters) // num_shorts)
        for i in range(0, min(len(chapters), num_shorts * step), step):
            ch = chapters[i]
            st = ch["sec"]
            if st + target_duration > duration:
                st = max(0, duration - target_duration - 5)
            clips.append({
                "start_sec": st,
                "duration_sec": target_duration,
                "tag": "TRENDING SCENE",
                "title1": ch["title"][:25].upper(),
                "title2": "MUST WATCH MOMENT!",
                "subtitle": f"{info.get('title', '')[:35]}",
                "description": f"Must watch moment from {ch['title']}! #Shorts #Viral"
            })
            if len(clips) >= num_shorts:
                break
    else:
        # Divide into intervals
        interval = (duration - target_duration - 10) / (num_shorts + 1)
        for i in range(1, num_shorts + 1):
            st = int(interval * i)
            clips.append({
                "start_sec": st,
                "duration_sec": target_duration,
                "tag": f"PART {i}",
                "title1": "WAIT FOR THE END!",
                "title2": "VIRAL MOMENT 🔥",
                "subtitle": f"{info.get('title', '')[:35]}",
                "description": f"Incredible moment! Subscribe for more! #Shorts #Viral"
            })
    return clips[:num_shorts]

def generate_rich_clip_metadata(clip, main_video_title, gemini_api_key=None):
    """Generates 3 Viral Title Options, Rich Description, and Pinned Comment."""
    title1 = clip.get("title1", "VIRAL MOMENT")
    title2 = clip.get("title2", "MUST WATCH")
    sub = clip.get("subtitle", main_video_title)

    # 1. Try Gemini AI if API key is provided
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"""You are a top viral YouTube Shorts strategist.
Generate metadata for this short video clip:
Main Video: {main_video_title}
Clip Hook: {title1} - {title2}
Context: {sub}

Generate JSON with:
- "title_options": [
    {{"type": "High CTR", "title": "Catchy headline with emojis and #Shorts (max 65 chars)"}},
    {{"type": "Curiosity Hook", "title": "Intriguing question headline with emojis and #Shorts (max 65 chars)"}},
    {{"type": "Hindi Mix", "title": "Desi Hindi / Hinglish hook title with emojis (max 65 chars)"}}
  ],
- "description": "Full 3-4 paragraph YouTube Shorts description with hook, background, subscribe CTA, 8-10 trending hashtags, and Section 107 Fair Use disclaimer.",
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

    # 2. Algorithmic High-Quality Fallback
    tag_clean = clean_text_for_font(title1)
    sub_clean = clean_text_for_font(main_video_title[:35])

    opt1 = f"{title1.title()} - Shocking Moment! 😱🔥 #Shorts"
    opt2 = f"Did You Notice THIS in {sub_clean}?! 🤯⚡ #Shorts"
    opt3 = f"{title1.title()} Dekh Kar Sab Hairaan Ho Gaye! 😂 #Viral"

    desc = f"""{title1.title()} - Unbelievable moment from {main_video_title}! 😱🔥

Watch the most thrilling and hilarious breakdown of this viral scene that everyone is talking about!

What was your favorite part of this video? Let us know in the comments below! 👇

🔔 Subscribe for daily viral shorts, movie secrets, reactions, and trending clips!

#Shorts #Viral #Trending #Entertainment #YouTubeShorts #MustWatch #ViralVideo #EpicMoment

---
Disclaimer: This video is transformative commentary and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright owners."""

    pinned = f"Aapko is clip me sabse accha kya laga? Comment me batayein! 👇"

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
    # Strip emojis and non-ascii glyphs that lack font support to avoid missing boxes
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
    sub_text = clean_text_for_font(config.get("subtitle", "Trending Clip"))

    # 1. Top Badge
    draw.rounded_rectangle([400, 140, 680, 190], radius=12, fill=(230, 36, 41, 240))
    draw.text((540, 165), tag_text, font=f_tag, fill=(255, 255, 255, 255), anchor="mm")

    # 2. Main Title Header Card
    draw.rounded_rectangle([50, 210, 1030, 410], radius=24, fill=(16, 18, 24, 225), outline=outline_color, width=4)
    draw.text((540, 268), title1_text, font=f_title1, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((540, 345), title2_text, font=f_title2, fill=accent_title, anchor="mm")

    # 3. Center Video Accent Lines
    v_top = 732
    v_bottom = 1188
    draw.line([(0, v_top), (1080, v_top)], fill=outline_color, width=4)
    draw.line([(0, v_bottom), (1080, v_bottom)], fill=outline_color, width=4)

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

def render_short_video(input_video, start_sec, duration_sec, output_file, overlay_file, beat_file):
    filter_complex = (
        f"[0:v]split=2[bg_in][fg_in];"
        f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.18:contrast=0.9[bg];"
        f"[fg_in]scale=1080:-2,eq=contrast=1.06:brightness=0.01:saturation=1.1,unsharp=3:3:0.6[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[comp1];"
        f"[comp1][2:v]overlay=0:0[comp2];"
        f"[comp2]drawbox=x=0:y=1905:w='1080*t/{duration_sec}':h=15:color=red@0.95:t=fill[v_out];"
        f"[0:a]aresample=44100,asetrate=44100*1.036,atempo=1/1.036,aresample=48000,equalizer=f=2500:t=q:w=1:g=2,highpass=f=75,lowpass=f=14500,volume=1.2[v_audio];"
        f"[1:a]volume=0.16[bgm];"
        f"[v_audio][bgm]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[a_out]"
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
        "-shortest",
        output_file
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"FFmpeg render error: {p.stderr}")
    return output_file
