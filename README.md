# ⚡ AI Shorts Studio Pro+

> **Transform Any YouTube Video or Local MP4 into 8 Copyright-Safe, Viral 9:16 Shorts in 1-Click!**  
> 100% Free, Runs Completely Locally on your PC/Mac — ₹0 Cloud Bills Forever.

---

## 🌟 Overview

**AI Shorts Studio Pro+** is an automated video production studio that takes long YouTube videos or uploaded video files, identifies the best viral moments, and converts them into **ready-to-upload 9:16 vertical Shorts / Reels / TikToks**.

Equipped with an **Ultra Anti-Claim Shield**, smart mood detection (CarryMinati, Comedy, Motivation, Gaming, Podcasts), and automated high-CTR title & description generation.

---

## ✨ Key Features (Currently Working on Local)

- **🎬 Dual Input Modes:**
  - **YouTube URL:** Auto-downloads long videos with built-in YouTube BotGuard & SABR streaming bypass (Android Client strategy).
  - **Direct Video Upload:** Drag-and-drop local `.mp4`, `.mov`, `.mkv` files directly.

- **⚡ 8 Viral Shorts in 1-Click:**
  - Slices up to 8 high-retention segments (Part 1 to Part 8) across the video timeline.
  - Generates distinct, captivating hook banners on each short.

- **🧠 Smart Topic & Mood-Aware Titles & Descriptions:**
  - **Auto Genre Detection:**
    - 😂 **CarryMinati / Comedy / Roast:** High-energy savage titles, laughing emojis, `#CarryMinati #Comedy #Roast #Funny`.
    - 🥺 **Motivational / Emotional:** Heart-touching life lessons, goosebumps hooks, `#Motivation #Inspirational #LifeLessons`.
    - 🎮 **Gaming (GTA, BGMI, etc.):** 1v4 clutch, impossible headshot, gameplay highlights.
    - 🎙️ **Podcasts / Interviews:** Raw confessions, untold truths, and shocking reveals.
  - **Real AI Integration (Optional):** Enter your free Google Gemini API key to have **Gemini 2.0 Flash AI** generate 100% customized viral titles, descriptions, and pinned comments.
  - **Algorithmic Fallback:** Generates high-CTR contextual titles even without an API key!

- **🛡️ Ultra Anti-Claim Copyright Shield (Content ID Resistant):**
  - **Visual Shield:** 9:16 layout with heavy ambient background blur, 1.12x smart dynamic zoom, and horizontal mirror flip.
  - **Audio Shield:** 1.065x speed shift, vocal acoustic EQ filter, and auto-synthesized ambient percussion beat overlay.
  - **Overlay Graphics:** Dynamic high-contrast hook cards and Fair-Use disclaimers.

- **🌐 Remote & Mobile Access (Access From Anywhere):**
  - Keep your PC/Mac ON and access the app from your phone anywhere using **Cloudflare Tunnel** or SSH tunneling.

- **🧹 Auto Storage Management:**
  - Automatic 24-hour cleanup of temporary files and old videos to keep your SSD storage free.

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Python 3.9 or higher**
- **FFmpeg** installed on your system:
  ```bash
  # On macOS (Homebrew):
  brew install ffmpeg

  # On Ubuntu / Debian:
  sudo apt update && sudo apt install ffmpeg
  ```

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/rkmaurya1/ai-shorts-studio.git
cd ai-shorts-studio

# Install Python packages
pip3 install -r requirements.txt
```

### 3. Run the Application
Simply execute the run script:
```bash
./run.sh
```
Or start Streamlit directly:
```bash
python3 -m streamlit run app.py --server.port 8501
```

Open your browser and navigate to:
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 📲 Remote Access from Phone (Free Live Link)

While your local PC/Mac is running the app, you can create a secure public URL to make shorts from your mobile phone or share with your team.

Open a new terminal tab and run:
```bash
cloudflared tunnel --url http://localhost:8501
```
Terminal will output a public HTTPS URL (e.g., `https://xxxx.trycloudflare.com`). Open this link on your phone browser!

---

## 📁 Project Directory Structure

```text
ai-shorts-studio/
├── app.py                 # Streamlit Web UI & User Controls
├── shorts_engine.py       # Core Video Processing, FFmpeg Pipeline & AI Metadata
├── run.sh                 # One-click startup shell script
├── requirements.txt       # Python dependencies (Streamlit, yt-dlp, Pillow, requests)
├── downloads/             # Raw downloaded YouTube & uploaded videos
├── output_shorts/         # Final rendered 9:16 Short videos & metadata JSONs
└── temp_overlays/         # Auto-generated graphic hook banners (PNG)
```

---

## ⚙️ Studio Controls

| Setting | Default | Description |
|---|---|---|
| **Shorts Count** | `8` | Number of shorts to extract from the video (1 to 10). |
| **Duration** | `45s` | Duration per short (30s to 55s, optimal for Shorts algorithm). |
| **Theme** | `Marvel Gold` | Graphic theme (`Gold & Red` or `Neon Cyan & Red`). |
| **Shield Level** | `Ultra Anti-Claim` | Content ID protection (Ultra, Music-Mute, or Voice Only). |
| **Gemini API Key** | *Optional* | Free key from [aistudio.google.com](https://aistudio.google.com) for 100% Generative AI metadata. |

---

## ⚖️ Fair Use Notice
This tool is designed to create transformative commentary, analysis, and educational short-form content under **Section 107 of the Copyright Act 1976 (Fair Use)**. Always respect original content creators.

---

## 📄 License
MIT License. Free to use, modify, and distribute.
