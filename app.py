import streamlit as st
import uuid
from pathlib import Path

from src.agent import answer_question
from src.database import get_recent_runs, init_db
from src.test_cases import TEST_CASES, run_test_case, print_summary

# Page config
st.set_page_config(
    page_title="VerbX Video Agent — Ziro Hackathon 2026",
    page_icon="🎬",
    layout="wide",
)

# Initialize DB
init_db()

# Sidebar
st.sidebar.title("🎬 VerbX Video Agent")
st.sidebar.caption("Ziro Agentic AI Hackathon 2026 — PS 4 (VerbX/IvishAI)")

mode = st.sidebar.radio("Mode", ["Demo Chat", "Run Test Cases (TC1–TC4)", "History"])

# --- Demo Chat ---
if mode == "Demo Chat":
    st.header("Ask a Question About a Video")

    # Video uploader (demo only — not stored permanently)
    uploaded = st.file_uploader("Upload a licensed video (MP4)", type=["mp4", "mov", "mkv"])
    video_path = None
    if uploaded:
        # Save to temp for processing
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        video_path = str(temp_dir / f"upload_{uuid.uuid4().hex[:8]}.mp4")
        with open(video_path, "wb") as f:
            f.write(uploaded.read())
        st.video(video_path)

    question = st.text_input("Your question", placeholder="What did the speaker say about...?")
    target_lang = st.selectbox("Answer language", ["en", "hi", "fr", "es", "de", "ja", "ko", "zh"], index=0)

    if st.button("Get Answer", type="primary", disabled=not (video_path and question)):
        with st.spinner("Processing video through VerbX APIs..."):
            try:
                result = answer_question(video_path, question, target_lang)
                st.success(f"Status: {result['status'].upper()}")

                # Answer
                st.subheader("Answer")
                st.write(result["answer"])

                # Audio
                if result.get("answer_audio_path") and Path(result["answer_audio_path"]).exists():
                    st.audio(result["answer_audio_path"])

                # Timestamps
                st.subheader("Timestamps & Evidence")
                ts = result["timestamps"]
                if ts["dialogue"]:
                    st.write("**Dialogue:**")
                    for d in ts["dialogue"]:
                        st.write(f"  {d['start']:.1f}–{d['end']:.1f}s: {d['text']}")
                if ts["ocr"]:
                    st.write("**On-screen text:**")
                    for o in ts["ocr"]:
                        st.write(f"  {o['timestamp']:.1f}s: {o['text']}")
                if ts["scenes"]:
                    st.write("**Scenes:**")
                    for s in ts["scenes"]:
                        st.write(f"  {s['timestamp']:.1f}s: {s['description']}")

                # Status note
                if result["status"] == "uncertain":
                    st.warning("⚠️ Agent could not see/hear relevant content — guarded response.")
                elif result["status"] == "partial":
                    st.info("ℹ️ Partial evidence found.")

            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)

# --- Test Cases ---
elif mode == "Run Test Cases (TC1–TC4)":
    st.header("Official Test Cases (TC1–TC4)")
    st.caption("Place licensed test videos in `videos/` folder matching TC paths.")

    if st.button("Run All Test Cases", type="primary"):
        results = []
        progress = st.progress(0)
        for i, tc in enumerate(TEST_CASES):
            st.write(f"Running {tc['id']}...")
            result = run_test_case(tc)
            results.append(result)
            progress.progress((i + 1) / len(TEST_CASES))

        # Summary table
        st.subheader("Results")
        for r in results:
            with st.expander(f"{r['test_case']} — {r.get('status', '?').upper()}"):
                st.json(r)

        print_summary(results)

# --- History ---
elif mode == "History":
    st.header("Run History")
    runs = get_recent_runs(50)
    if runs:
        for r in runs:
            with st.expander(f"{r['test_case']} | {r['status']} | {r['created_at']}"):
                st.write(f"**Video:** {r['video_path']}")
                st.write(f"**Q:** {r['question']}")
                st.write(f"**A:** {r['answer']}")
                st.write(f"**Lang:** {r['language']}")
                if r['answer_audio_path'] and Path(r['answer_audio_path']).exists():
                    st.audio(r['answer_audio_path'])
                st.json(r['evidence_json'])
    else:
        st.info("No runs yet.")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Built for Ziro Agentic AI Hackathon 2026")
st.sidebar.caption("VerbX / IvishAI Partner Challenge (PS 4)")