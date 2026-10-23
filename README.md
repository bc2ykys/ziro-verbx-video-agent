# 🎬 VerbX Multilingual Video Understanding Agent

> **Ziro Agentic AI Hackathon 2026 — VerbX / IvishAI Partner Challenge (PS 4)**

An AI agent that answers contextual questions about video content — dialogue, on-screen text, and scenes — **by voice** with **precise timestamps**, in the **questioner's language**.

## 🎯 Problem Statement

Build an intelligent agent that:
- **Understands** video scenes, dialogue, and visible text using VerbX APIs
- **Answers** contextual questions **by voice** with **accurate timestamps**
- **Speaks** in the **questioner's language** (multilingual support)
- **States** when something **cannot be seen or heard** (no hallucination — guardrails)
- Uses **only licensed/CC0 videos** (responsible AI)

## 🏗️ Architecture

```
Video (MP4) → ffmpeg Processor
  ├─ Audio (16kHz WAV) → VerbX STT → Transcript + Timestamps
  ├─ Frames (1 fps JPEG) → VerbX OCR → On-screen Text + Positions  
  ├─ Frames (1 fps JPEG) → VerbX Image Assist → Scene Descriptions
  └─ Combined Evidence → Agentic Reasoning Engine
        ├─ Evidence Found → Answer with Timestamps
        ├─ No Evidence → Guardrail: "Cannot see/hear"
        ├─ VerbX Translation → Target Language
        └─ VerbX TTS → Voice Answer
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed Mermaid diagrams and API flow sequences.

## 🔧 VerbX APIs Used

| API | Endpoint | Purpose |
|-----|----------|---------|
| **STT** | `/saas/playground/stt` | Speech-to-text with segment timestamps |
| **OCR** | `/saas/playground/ocr` | Text recognition on video frames |
| **Image Assist** | `/v1/assist` | Scene understanding and visual QA |
| **Translate** | `/saas/playground/translate` | Multilingual answer translation |
| **TTS** | `/saas/playground/tts` | Text-to-speech voice output |

## ✅ Test Cases (TC1–TC4)

| Test | Scenario | Expected | Status |
|------|----------|----------|--------|
| TC1 | Dialogue question + accurate timestamp | Answer + exact time | Pipeline ✅ |
| TC2 | On-screen text + scene + source time | OCR text + time | Pipeline ✅ |
| TC3 | Answer in asker's language (French) | Voice in French | Pipeline ✅ |
| TC4 | Unclear content → guardrail | "Cannot see/hear" | **Verified ✅** |

## 🚀 Quick Start

```bash
# 1. Clone & enter
git clone https://github.com/bc2ykys/ziro-verbx-video-agent
cd ziro-verbx-video-agent

# 2. Create venv & install
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# 3. Install ffmpeg (required for video processing)
# Windows: winget install ffmpeg
# Mac: brew install ffmpeg  
# Linux: sudo apt install ffmpeg

# 4. Configure VerbX credentials
cp .env.example .env
# Edit .env — add your VerbX access token
# Get token: Login at https://one.verbxeco.com → API Settings

# 5. Place test videos (licensed/CC0 only)
# Put MP4 files in videos/ folder

# 6. Run
streamlit run app.py --server.port 8502
```

## 📁 Project Structure

```
ziro-verbx-video-agent/
├── app.py                  # Streamlit demo UI (3 tabs)
├── ARCHITECTURE.md         # Detailed architecture diagrams
├── .env.example            # Template for secrets
├── .gitignore              # Secrets & artifacts excluded
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── LICENSE                 # MIT License
└── src/
    ├── __init__.py
    ├── config.py           # Pydantic settings from .env
    ├── database.py         # SQLite evidence logging
    ├── verbx_client.py     # VerbX API wrapper (5 APIs, retry logic)
    ├── video_processor.py  # ffmpeg frame/audio extraction
    ├── agent.py            # Main pipeline: video → answer + timestamps
    └── test_cases.py       # TC1–TC4 runner + evidence capture
```

## 🖥️ Streamlit UI

The app has 3 interactive tabs:

1. **Demo Chat** — Upload a video, ask a question, get a voice answer
2. **Run Test Cases (TC1–TC4)** — Execute all 4 test cases with progress bar
3. **History** — Browse past runs with full evidence chain (SQLite-backed)

## 🛡️ Key Design Decisions

- **Graceful degradation**: API errors (401/502/timeout) → empty results, not crashes
- **Silent audio fallback**: Videos without audio → synthetic silent track → STT pipeline works
- **Evidence logging**: Every API call logged to SQLite for auditability
- **Guardrail first**: No evidence found → agent explicitly states uncertainty
- **Licensed content only**: All test videos CC0/Pexels — no copyrighted material
- **Retry logic**: Automatic retries with exponential backoff for 502/503 errors

## 🔐 Security

- No API keys in repo — `.gitignore` excludes `.env`, `videos/`, `outputs/`
- VerbX auth via JWT access tokens (login flow)
- All secrets stay local

## 📝 Submission

- **Ziro Dashboard**: [ziro.digital/dashboard](https://ziro.digital/dashboard)
- **VerbX Builds**: [one.verbxeco.com/builds](https://one.verbxeco.com/builds)
- **Public Repo**: [github.com/bc2ykys/ziro-verbx-video-agent](https://github.com/bc2ykys/ziro-verbx-video-agent)

## 📄 License

MIT — see [LICENSE](LICENSE)

---

*Built for Ziro Agentic AI Hackathon 2026 — VerbX / IvishAI Partner Challenge (PS 4)*
