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
    
    # Android client bypasses YouTube BotGuard, SABR streaming & 403 Forbidden on AWS / Streamlit Cloud
    client_strategies = [
        {"client": "android", "fmt": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"},
        {"client": "android", "fmt": "18/best"},
        {"client": "android_vr", "fmt": "best[ext=mp4]/best"},
        {"client": "android,web", "fmt": "best"}
    ]

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
            p_dl = subprocess.run(dl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            if p_dl.returncode == 0 and os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                download_success = True
                break
            else:
                last_err = p_dl.stderr
        
        if not download_success:
            raise RuntimeError(f"Download failed: {last_err}")
            
    return video_path, info

def sanitize_hook_text(text):
    """Sanitizes text to remove episode numbers or official copyright patterns."""
    if not text:
        return "VIRAL MOMENT"
    clean = re.sub(r'(?i)(episode\s*\d+|ep\s*\d+|season\s*\d+|s\d+\s*ep\d+|ft\.?[^,\n]+)', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:28].upper() if clean else "VIRAL MOMENT"

def select_clip_moments(info, num_shorts=3, target_duration=45, gemini_api_key=None):
    """Identifies top segments using chapters/description or Gemini AI."""
    description = info.get("description", "")
    duration = info.get("duration", 600)
    chapters = parse_timestamps_from_text(description)
    
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
IMPORTANT FOR COPYRIGHT SAFETY: Do NOT include raw TV episode numbers or copyright celebrity names in hook titles. Use exciting viral curiosity hooks.

Return ONLY valid JSON array with keys:
- "start_sec": integer seconds start (between 0 and {duration - target_duration})
- "duration_sec": integer duration (around {target_duration})
- "tag": short badge tag (e.g., "VIRAL MOMENT", "EPIC SCENE", "UNBELIEVABLE")
- "title1": catchy hook line 1 (uppercase, max 26 chars, e.g. "WAIT FOR THE END!")
- "title2": catchy hook line 2 (uppercase, max 26 chars, e.g. "HE COULDN'T BELIEVE IT")
- "subtitle": curiosity text (max 35 chars, e.g. "Trending Reaction")
- "description": transformative viral YouTube Shorts description with fair use disclaimer
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
            clean_t = sanitize_hook_text(ch["title"])
            clips.append({
                "start_sec": st,
                "duration_sec": target_duration,
                "tag": "TRENDING SCENE",
                "title1": clean_t if clean_t else "WAIT FOR THIS!",
                "title2": "MUST WATCH MOMENT! 🔥",
                "subtitle": "Trending Reaction Moment",
                "description": f"Incredible moment! Wait for the twist at the end. #Shorts #Viral"
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
                "title1": "WAIT FOR THE END! 😱",
                "title2": "VIRAL MOMENT 🔥",
                "subtitle": "Trending Viral Short",
                "description": "Shocking moment! Watch till the end! #Shorts #Viral"
            })
    return clips[:num_shorts]

def generate_rich_clip_metadata(clip, main_video_title, gemini_api_key=None):
    """
    Generates 3 Viral Title Options, Rich Description, and Pinned Comment.
    NOTE: Sanitizes raw episode strings and official copyright names to avoid priority Content ID flags.
    """
    title1 = clip.get("title1", "VIRAL MOMENT")
    title2 = clip.get("title2", "MUST WATCH")
    sub = clip.get("subtitle", "Trending Moment")

    # 1. Try Gemini AI if API key is provided
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"""You are a top viral YouTube Shorts strategist.
Generate metadata for this short video clip:
Context Hook: {title1} - {title2}
Context: {sub}

CRITICAL COPYRIGHT NOTICE: Do not mention specific TV show episode numbers, exact song titles or official copyright strings in title options. Focus on curiosity hooks, shock value, and transformative commentary.

Generate JSON with:
- "title_options": [
    {{"type": "High CTR", "title": "Catchy headline with emojis and #Shorts (max 65 chars)"}},
    {{"type": "Curiosity Hook", "title": "Intriguing question headline with emojis and #Shorts (max 65 chars)"}},
    {{"type": "Hindi Mix", "title": "Desi Hindi / Hinglish hook title with emojis (max 65 chars)"}}
  ],
- "description": "Full YouTube Shorts description with hook, background, subscribe CTA, 8-10 trending hashtags, and Section 107 Fair Use disclaimer.",
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

    # 2. Algorithmic High-Quality Fallback (Disinfected from raw copyright strings)
    hook_clean = clean_text_for_font(title1).title()
    if not hook_clean or len(hook_clean) < 4:
        hook_clean = "Wait For The Twist"

    opt1 = f"{hook_clean} - Shocking Moment! 😱🔥 #Shorts #Viral"
    opt2 = f"Did You Notice THIS in The Video?! 🤯⚡ #Shorts"
    opt3 = f"{hook_clean} Dekh Kar Sab Hairaan Ho Gaye! 😂 #Viral #Shorts"

    desc = f"""{hook_clean} - You won't believe what happened here! 😱🔥

Watch the funniest and most thrilling breakdown of this viral scene that everyone is reacting to!

What was your favorite moment in this clip? Tell us in the comments! 👇

🔔 Subscribe for daily viral moments, comedy reactions, and trending shorts!

#Shorts #Viral #Trending #Comedy #Entertainment #YouTubeShorts #MustWatch #EpicMoment #Reaction

---
⚖️ Fair Use Disclaimer:
This video is transformative commentary, review, and fan analysis created under Section 107 of the Copyright Act 1976 (Fair Use). All rights belong to their respective copyright holders."""

    pinned = "Aapko is scene me sabse zyada kya pasand aaya? Comment me batayein! 👇"

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
