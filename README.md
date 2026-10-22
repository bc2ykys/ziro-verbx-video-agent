# Ziro Agentic AI Hackathon 2026 — VerbX / IvishAI Partner Challenge (PS 4)
**Multilingual Video Understanding Agent**

Answers contextual questions about video dialogue, on-screen text, and scenes — by voice with precise timestamps.

## Problem Statement
Build an agent that:
- Understands video scenes, dialogue, and visible text
- Answers contextual questions **by voice** with **timestamps**
- Speaks in the **questioner's language**
- States when something **cannot be seen or heard** (guardrails)
- Uses **only licensed/CC0 videos**

## Architecture
```
Video → ffmpeg (frames + audio)
  ├─ Audio → VerbX STT → Transcript + timestamps
  ├─ Frames → VerbX OCR → On-screen text + timestamps
  ├─ Frames → VerbX Image Assistant → Scene descriptions + timestamps
  └─ Combined context → LLM reasoning → Answer
        ├─ VerbX Translation → Target language
        └─ VerbX TTS → Voice answer with timestamps
```

## VerbX APIs Used
- **STT** — Speech-to-text with timestamps
- **OCR** — Optical character recognition on frames
- **Image Assistant** — Scene/video understanding
- **Translation** — Multilingual answers
- **TTS** — Text-to-speech for voice output

## Test Cases (TC1–TC4)
| Test | Description | Expected |
|------|-------------|----------|
| TC1 | Dialogue question + accurate timestamp | Answer + exact time |
| TC2 | On-screen text + scene + source time | Answer + time |
| TC3 | Answer in asker's language | Voice in that language |
| TC4 | Unclear content → label uncertain | "Cannot see/hear" |

## Setup
```bash
# 1. Clone & enter
git clone https://github.com/bc2ykys/ziro-verbx-video-agent
cd ziro-verbx-video-agent

# 2. Create venv & install
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Install ffmpeg (required)
# Windows: winget install ffmpeg  OR  choco install ffmpeg
# Mac: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# 4. Configure
cp .env.example .env
# Edit .env with your VerbX API key

# 5. Run
streamlit run app.py
```

## Project Structure
```
ziro-verbx-video-agent/
├── app.py                 # Streamlit demo UI
├── .env.example           # Template for secrets
├── .gitignore             # Secrets & artifacts excluded
├── requirements.txt       # Python deps
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── config.py          # Settings from .env
│   ├── database.py        # SQLite logging (inputs, evidence, results)
│   ├── verbx_client.py    # VerbX API wrapper (STT, OCR, Image, Translate, TTS)
│   ├── video_processor.py # ffmpeg frame/audio extraction
│   ├── agent.py           # Main pipeline: video → answer + timestamps
│   └── test_cases.py      # TC1–TC4 runner + evidence capture
├── tests/
│   ├── test_tc1.py
│   ├── test_tc2.py
│   ├── test_tc3.py
│   └── test_tc4.py
├── videos/                # Place licensed test videos here (NOT committed)
└── outputs/               # Demo outputs, logs (NOT committed)
```

## Submission Checklist (before 23 Oct 2026)
- [ ] Public GitHub repo ✅
- [ ] Working demo (Streamlit) showing TC1–TC4
- [ ] ≤3-min demo video recorded
- [ ] Submitted to **Ziro dashboard**
- [ ] Submitted to **https://one.verbxeco.com/builds** (public repo link, demo video, languages, APIs used)
- [ ] API keys on server only (not in repo)
- [ ] LinkedIn post + tag @ZiroDigital

## License
MIT — see LICENSE