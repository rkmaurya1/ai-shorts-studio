import streamlit as st
import os
import sys
import time
import glob
import json
import traceback

st.set_page_config(
    page_title="AI Shorts Studio Pro+",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ensure consistent working directory and imports regardless of where streamlit is invoked
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

try:
    from shorts_engine import (
        download_youtube_video,
        select_clip_moments,
        generate_ambient_beat,
        create_overlay_png,
        render_short_video,
        generate_rich_clip_metadata,
        cleanup_old_files
    )
except Exception as e:
    st.error(f"❌ Error loading shorts_engine: {type(e).__name__}: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()

# Auto-delete files older than 24 hours to keep storage free (₹0 bill forever)
try:
    cleanup_old_files(max_age_hours=24)
except Exception:
    pass

# Responsive, Clean & Compact Video CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Navbar */
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 20px;
        background: rgba(22, 27, 34, 0.9);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(48, 54, 61, 0.7);
        border-radius: 14px;
        margin-bottom: 20px;
    }
    
    .brand-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #FF453A 0%, #FF9F0A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .badge-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(46, 160, 67, 0.15);
        color: #3fb950;
        border: 1px solid rgba(46, 160, 67, 0.3);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .shield-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(56, 139, 253, 0.12);
        color: #58a6ff;
        border: 1px solid rgba(56, 139, 253, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 600;
    }
    
    /* Card Containers */
    .saas-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }
    
    /* COMPACT VIDEO PLAYER STYLING */
    div[data-testid="stVideo"] {
        max-width: 215px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: flex !important;
        justify-content: center !important;
    }
    
    div[data-testid="stVideo"] > video {
        max-width: 215px !important;
        max-height: 380px !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5) !important;
        border: 2px solid #30363d !important;
        object-fit: contain !important;
        background: #000000 !important;
    }
    
    /* Compact Gallery Video Cards */
    .gallery-box {
        background: #11151c;
        border: 1px solid #282e36;
        border-radius: 14px;
        padding: 12px;
        text-align: center;
        margin-bottom: 16px;
    }
    
    /* Primary Action Button */
    .stButton>button {
        background: linear-gradient(135deg, #FF453A 0%, #FF9F0A 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 22px !important;
        box-shadow: 0 4px 14px rgba(255, 69, 58, 0.35) !important;
        transition: all 0.2s ease !important;
        height: 44px !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 69, 58, 0.5) !important;
    }
    
    .stDownloadButton>button {
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        padding: 6px 12px !important;
        font-weight: 600 !important;
    }

    /* Mobile Adaptability */
    @media (max-width: 768px) {
        .top-header {
            flex-direction: column;
            gap: 8px;
            align-items: flex-start;
            padding: 12px 14px;
        }
        div[data-testid="stVideo"] {
            max-width: 175px !important;
        }
        div[data-testid="stVideo"] > video {
            max-width: 175px !important;
            max-height: 310px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

def render_metadata_details(meta):
    """Renders 3 Viral Title Options, Description, and Pinned Comment."""
    st.markdown("##### 📌 Viral Title Options (Choose any 1):")
    opts = meta.get("title_options", [])
    if opts:
        for opt in opts:
            st.markdown(f"**• {opt.get('type', 'Option')}:**")
            st.code(opt.get("title", ""), language="text")
    else:
        st.code(meta.get("title", "Viral Short #Shorts"), language="text")
        
    st.markdown("##### 📝 Description & Hashtags:")
    st.code(meta.get("description", ""), language="text")
    
    st.markdown("##### 💬 Recommended Pinned Comment:")
    st.info(meta.get("pinned_comment", "What was your favorite part? Comment below! 👇"))

# Top Bar Header
st.markdown("""
<div class="top-header">
    <div>
        <p class="brand-title">⚡ AI SHORTS STUDIO PRO</p>
        <span style="color: #8b949e; font-size: 0.82rem;">Smart YouTube to 9:16 Copyright-Safe Shorts</span>
    </div>
    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <span class="badge-status">● Engine Online</span>
        <span class="shield-badge">🛡️ Ultra Anti-Claim Shield v2</span>
        <span class="shield-badge" style="background: rgba(163, 113, 247, 0.15); color: #d2a8ff; border-color: rgba(163, 113, 247, 0.3);">⏳ 24h Auto-Clean Active</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.markdown("### ⚙️ Studio Controls")
    
    gemini_key = st.text_input(
        "Google Gemini API Key (Optional)",
        type="password",
        placeholder="Paste API Key (Optional)",
        help="Free key from aistudio.google.com. Khali chhodne par auto-scene detection use hoga."
    )
    
    num_shorts = st.slider("Kitne Shorts Banane Hain?", min_value=1, max_value=5, value=3)
    target_duration = st.slider("Short Duration (Seconds)", min_value=30, max_value=55, value=45)
    theme = st.selectbox("Design Theme", ["gold", "cyan"], format_func=lambda x: "🟡 Marvel Gold & Red" if x == "gold" else "🔵 Neon Cyan & Red")
    
    st.markdown("---")
    st.markdown("### 🛡️ Copyright Shield Controls")
    shield_preset = st.selectbox(
        "Shield Level",
        [
            "🛡️ Ultra Anti-Claim Shieldss (Recommended)",
            "🔇 Music-Mute Shield (Zero Song Claim)",
            "🎙️ Voice Only (No BGM Beat)",
            "⚙️ Custom Settings"
        ],
        help="Ultra Anti-Claim applies horizontal mirror, 1.12x smart zoom, 1.065x speed cadence, and acoustic vocal mask."
    )
    
    if shield_preset == "🛡️ Ultra Anti-Claim Shield (Recommended)":
        mirror_flip = True
        zoom_crop = 1.12
        speed_boost = 1.065
        audio_mode = "vocal_beat"
        st.caption("✅ Mirror (hflip): ON\n\n✅ 1.12x Zoom & Crop: ON\n\n✅ 1.065x Speed Boost: ON\n\n✅ Vocal EQ & Anti-Claim Beat: ON")
    elif shield_preset == "🔇 Music-Mute Shield (Zero Song Claim)":
        mirror_flip = True
        zoom_crop = 1.12
        speed_boost = 1.065
        audio_mode = "mute_music"
        st.warning("⚠️ Original audio muted & replaced with viral beat. Guarantees 0 claim even if full copyrighted song is playing in original clip.")
    elif shield_preset == "🎙️ Voice Only (No BGM Beat)":
        mirror_flip = True
        zoom_crop = 1.12
        speed_boost = 1.065
        audio_mode = "voice_only"
        st.info("ℹ️ Dialogue preserved with vocal EQ & pitch shift without background beat.")
    else:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            mirror_flip = st.checkbox("🪞 Mirror Flip", value=True)
        with col_c2:
            enable_zoom = st.checkbox("🔍 Smart Zoom", value=True)
        zoom_crop = 1.12 if enable_zoom else 1.0
        speed_boost = st.slider("⚡ Speed Boost", 1.00, 1.12, 1.065, 0.005)
        audio_mode = st.selectbox(
            "Audio Mode",
            ["vocal_beat", "voice_only", "mute_music"],
            format_func=lambda x: "Vocal + Anti-Claim Beat" if x=="vocal_beat" else ("Voice Only" if x=="voice_only" else "Mute Original & Replace")
        )

# Main Input Section
with st.container():
    st.markdown('<div class="saas-card">', unsafe_allow_html=True)
    st.markdown("<h4 style='margin-top:0; font-size:1.05rem; font-weight:700;'>🎬 Enter YouTube Video Link</h4>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3.8, 1.2])
    with col1:
        youtube_url = st.text_input(
            "YouTube Video Link",
            label_visibility="collapsed",
            placeholder="Paste link e.g. https://youtu.be/OV2d3EilpPw",
            value=""
        )
    with col2:
        start_btn = st.button("🚀 Generate Shorts", use_container_width=True)
        
    st.markdown("""
    <div style="margin-top: 6px;">
        <span style="color: #8b949e; font-size: 0.78rem;">💡 Quick Links: </span>
        <code style="font-size: 0.74rem; background: #0d1117; padding: 2px 6px; border-radius: 4px;">https://youtu.be/OV2d3EilpPw</code>
        <code style="font-size: 0.74rem; background: #0d1117; padding: 2px 6px; border-radius: 4px;">https://youtu.be/kI_hRuzVbtU</code>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

output_folder = "output_shorts"
os.makedirs(output_folder, exist_ok=True)
os.makedirs("temp_overlays", exist_ok=True)

# Video Processing Pipeline
if start_btn:
    if not youtube_url.strip():
        st.warning("⚠️ Kripya ek YouTube video link enter kijiye!")
    else:
        status_box = st.status("🎬 Processing Video...", expanded=True)
        
        try:
            status_box.write("📥 Step 1/4: Video download ho raha hai...")
            video_path, info = download_youtube_video(youtube_url)
            status_box.write(f"✅ Video Downloaded: **{info.get('title')}**")

            status_box.write("🎯 Step 2/4: Viral moments aur timestamps select ho rahe hain...")
            clips = select_clip_moments(info, num_shorts=num_shorts, target_duration=target_duration, gemini_api_key=gemini_key)
            status_box.write(f"✅ {len(clips)} Viral Segments Identified!")

            status_box.write("🎵 Step 3/4: Copyright-safe percussion shield synthesize ho raha hai...")
            beat_path = generate_ambient_beat(duration=target_duration + 25)

            status_box.write("🎨 Step 4/4: Anti-Claim 9:16 layout, titles & descriptions render ho rahe hain...")
            
            created_shorts = []
            progress_bar = st.progress(0)
            
            for idx, clip in enumerate(clips):
                status_box.write(f"Rendering Short {idx+1}/{len(clips)}: {clip.get('title1')}...")
                
                overlay_path = f"temp_overlays/overlay_{idx+1}.png"
                create_overlay_png(clip, overlay_path, theme=theme)
                
                out_filename = f"Short_{idx+1}_{int(time.time())}.mp4"
                out_path = os.path.join(output_folder, out_filename)
                
                render_short_video(
                    input_video=video_path,
                    start_sec=clip["start_sec"],
                    duration_sec=clip["duration_sec"],
                    output_file=out_path,
                    overlay_file=overlay_path,
                    beat_file=beat_path,
                    mirror_flip=mirror_flip,
                    zoom_crop=zoom_crop,
                    speed_boost=speed_boost,
                    audio_mode=audio_mode
                )
                
                # Generate and save rich metadata
                meta = generate_rich_clip_metadata(clip, info.get("title", ""), gemini_api_key=gemini_key)
                meta_path = out_path.replace(".mp4", ".json")
                with open(meta_path, "w") as mf:
                    json.dump(meta, mf, indent=2)
                
                created_shorts.append({
                    "path": out_path,
                    "filename": out_filename,
                    "clip": clip,
                    "meta": meta
                })
                progress_bar.progress((idx + 1) / len(clips))
                
            status_box.update(label="🎉 Sabhi Shorts Successfully Taiyar Ho Gaye!", state="complete", expanded=False)
            st.session_state["recent_shorts"] = created_shorts
            st.balloons()
            
        except Exception as e:
            status_box.update(label="❌ Error aayi!", state="error")
            st.error(f"Error: {str(e)}")

# Pro-Tips Upload Guide
st.markdown("""
<div class="saas-card" style="border-left: 4px solid #3fb950; background: #0d1a12; padding: 14px 18px; margin-top: 15px;">
    <h5 style="margin: 0 0 6px 0; color: #3fb950; font-weight: 700;">🛡️ YouTube 0-Claim Upload Guide</h5>
    <ul style="margin: 0; padding-left: 20px; font-size: 0.84rem; color: #c9d1d9; line-height: 1.6;">
        <li><b>Ultra Anti-Claim Shield Active:</b> Video me Horizontal Mirror, 1.12x Smart Zoom, 1.065x Speed Shift aur Acoustic Vocal EQ applied hai taaki YouTube Content ID scanner visual aur audio dono taraf se block ho jaye.</li>
        <li><b>YouTube App se Upload karte waqt:</b> Mobile app me <b>"Add Sound"</b> par tap karke koi bhi popular/trending song ya sound select karein. Isse YouTube audio ko officially license kar deta hai aur 100% Zero Claim rehta hai.</li>
        <li><b>Clean Titles:</b> Niche diye gaye catchy curiosity titles hi use karein. Original show ya episode ka official name title me mat daalein.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Newly Generated Shorts (Two-Column Layout with Compact Player & Rich Metadata)
if "recent_shorts" in st.session_state and st.session_state["recent_shorts"]:
    st.markdown("<h3 style='font-size:1.25rem; font-weight:800; margin-top:20px; margin-bottom:12px;'>✨ Newly Generated Shorts</h3>", unsafe_allow_html=True)
    
    shorts_list = st.session_state["recent_shorts"]
    tabs = st.tabs([f"📱 Short #{i+1}: {item['clip'].get('title1', 'Clip')[:16]}" for i, item in enumerate(shorts_list)])
    
    for i, tab in enumerate(tabs):
        with tab:
            item = shorts_list[i]
            meta = item.get("meta") or generate_rich_clip_metadata(item["clip"], "Viral Video")
            
            col_preview, col_details = st.columns([1, 2.2])
            
            with col_preview:
                st.video(item["path"])
                st.write("")
                with open(item["path"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Short #{i+1}",
                        data=f,
                        file_name=item["filename"],
                        mime="video/mp4",
                        use_container_width=True
                    )
            
            with col_details:
                st.markdown('<div class="saas-card" style="margin-bottom:0;">', unsafe_allow_html=True)
                render_metadata_details(meta)
                st.markdown('</div>', unsafe_allow_html=True)

# Available Shorts Gallery in 4 Neat Compact Columns with Titles & Description Expander
st.markdown("<h3 style='font-size:1.2rem; font-weight:800; margin-top:30px; margin-bottom:14px;'>📁 Available Shorts on your PC</h3>", unsafe_allow_html=True)

existing_files = sorted(
    glob.glob("output_shorts/Short_*.mp4") + glob.glob("Short_*.mp4"),
    key=os.path.getmtime,
    reverse=True
)
seen = set()
unique_files = []
for f in existing_files:
    bn = os.path.basename(f)
    if bn not in seen and not bn.startswith("test_"):
        seen.add(bn)
        unique_files.append(f)

if unique_files:
    num_cols = 4
    cols = st.columns(num_cols)
    for idx, fpath in enumerate(unique_files):
        with cols[idx % num_cols]:
            st.markdown('<div class="gallery-box">', unsafe_allow_html=True)
            st.markdown(f"<p style='font-weight:700; font-size:0.8rem; margin-bottom:6px; color:#c9d1d9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{os.path.basename(fpath)}</p>", unsafe_allow_html=True)
            
            st.video(fpath)
            
            st.write("")
            with open(fpath, "rb") as f:
                st.download_button(
                    label=f"⬇️ Download",
                    data=f,
                    file_name=os.path.basename(fpath),
                    mime="video/mp4",
                    key=f"dl_grid_{fpath}_{idx}",
                    use_container_width=True
                )
                
            meta_path = fpath.replace(".mp4", ".json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r") as jf:
                        card_meta = json.load(jf)
                except Exception:
                    card_meta = None
            else:
                card_meta = None

            if not card_meta:
                card_meta = generate_rich_clip_metadata({"title1": os.path.basename(fpath)}, os.path.basename(fpath))

            with st.expander("📝 View Titles & Description"):
                render_metadata_details(card_meta)
                
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Abhi koi previous shorts nahi hain. Upar link daal kar naya short banayein!")
