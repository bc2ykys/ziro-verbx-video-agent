# VerbX Multilingual Video Understanding Agent — Architecture

## System Architecture

```mermaid
flowchart TD
    A["🎥 Input Video (MP4)"] --> B["ffmpeg Processor"]
    B --> C["🔊 Audio Track (WAV 16kHz mono)"]
    B --> D["🖼️ Video Frames (1 fps JPEG)"]
    
    C --> E["VerbX STT API"]
    D --> F["VerbX OCR API"]
    D --> G["VerbX Image Assist API"]
    
    E --> H["📝 Transcript + Timestamps"]
    F --> I["📄 On-screen Text + Positions"]
    G --> J["🎬 Scene Descriptions"]
    
    H --> K["Agentic Reasoning Engine"]
    I --> K
    J --> K
    L["❓ User Question"] --> K
    
    K --> M{"Evidence Found?"}
    M -->|"Yes"| N["✅ Answer with Timestamps"]
    M -->|"Uncertain"| O["⚠️ Guardrail: Cannot see/hear"]
    
    N --> P["VerbX Translate API"]
    O --> P
    P --> Q["VerbX TTS API"]
    Q --> R["🔊 Voice Answer in Target Language"]
    
    K --> S["📊 SQLite Evidence Logger"]
    S --> T["History & Audit Trail"]

    style A fill:#e1f5fe
    style R fill:#e8f5e9
    style O fill:#fff3e0
    style S fill:#f3e5f5
```

## API Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant A as Agent Pipeline
    participant FF as ffmpeg
    participant V as VerbX APIs
    participant DB as SQLite DB

    U->>UI: Upload video + question + language
    UI->>A: answer_question(video, question, lang)
    A->>FF: Extract audio (16kHz WAV)
    A->>FF: Extract frames (1 fps JPEG)
    
    A->>V: POST /saas/playground/stt (audio_base64)
    V-->>A: Transcript segments + timestamps
    
    loop Each frame
        A->>V: POST /saas/playground/ocr (image_base64)
        V-->>A: Extracted text + bounding boxes
        A->>V: POST /v1/assist (image + prompt)
        V-->>A: Scene description
    end
    
    A->>A: Match question keywords → relevant evidence
    
    alt Evidence found
        A->>V: POST /saas/playground/translate (answer, target_lang)
        V-->>A: Translated answer
    else No evidence
        A->>A: Generate guardrail: "cannot see/hear"
    end
    
    A->>V: POST /saas/playground/tts (answer, language)
    V-->>A: Audio bytes (base64)
    
    A->>DB: Log run + evidence
    A-->>UI: Answer + timestamps + audio + status
    UI-->>U: Display answer, play audio, show timestamps
```

## VerbX APIs Used

| API | Endpoint | Purpose |
|-----|----------|---------|
| **STT** | `/saas/playground/stt` | Speech-to-text with segment timestamps |
| **OCR** | `/saas/playground/ocr` | Text recognition on video frames |
| **Image Assist** | `/v1/assist` | Scene understanding and visual QA |
| **Translate** | `/saas/playground/translate` | Multilingual answer translation |
| **TTS** | `/saas/playground/tts` | Text-to-speech voice output |

## Test Cases

| TC | Scenario | Expected Behavior | Status |
|----|----------|-------------------|--------|
| TC1 | Dialogue question with timestamp | Answer contains dialogue text + exact time | Pipeline complete ✅ |
| TC2 | On-screen text detection | OCR extracts visible text + source time | Pipeline complete ✅ |
| TC3 | Multilingual answer | Answer spoken in asker's language (French) | Pipeline complete ✅ |
| TC4 | Unclear/no content guardrail | Agent states "cannot see/hear" — no hallucination | **Verified ✅** |

## Key Design Decisions

1. **Graceful degradation**: API errors (401/502/timeout) return empty results instead of crashing
2. **Silent audio fallback**: Videos without audio get synthetic silent track for STT pipeline
3. **Evidence logging**: Every API call logged to SQLite for auditability
4. **Guardrail first**: When no evidence found, agent explicitly states uncertainty
5. **Licensed content only**: All test videos are CC0/Pexels — no copyrighted material
