"""
Official Test Cases TC1–TC4 for VerbX Video Understanding Agent.
Run each and capture input, actual result, evidence.
"""
from pathlib import Path
from typing import Dict, Any, List
from .agent import answer_question
from .database import log_run


# Define test cases — replace video paths with your licensed test videos
TEST_CASES = [
    {
        "id": "TC1",
        "name": "Dialogue question with accurate timestamp",
        "video": "videos/tc1_dialogue.mp4",          # PUT LICENSED VIDEO HERE
        "question": "What did the speaker say about the budget?",
        "target_lang": "en",
        "expected": "Answer contains dialogue text + timestamp",
    },
    {
        "id": "TC2",
        "name": "Visible on-screen text and scene with source time",
        "video": "videos/tc2_onscreen.mp4",          # PUT LICENSED VIDEO HERE
        "question": "What text appears on screen at 0:15?",
        "target_lang": "en",
        "expected": "Answer contains OCR text + timestamp",
    },
    {
        "id": "TC3",
        "name": "Answer in asker's language",
        "video": "videos/tc3_multilingual.mp4",      # PUT LICENSED VIDEO HERE
        "question": "Qu'est-ce que l'orateur a dit ?",  # French question
        "target_lang": "fr",
        "expected": "Answer spoken in French with timestamp",
    },
    {
        "id": "TC4",
        "name": "Unclear content labeled uncertain",
        "video": "videos/tc4_unclear.mp4",           # PUT LICENSED VIDEO HERE (blurry/no audio)
        "question": "What is the small text in the corner?",
        "target_lang": "en",
        "expected": "Agent states 'cannot see/hear' — no hallucination",
    },
]


def run_test_case(tc: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case, return result dict."""
    video_path = tc["video"]
    if not Path(video_path).exists():
        return {
            "test_case": tc["id"],
            "status": "skipped",
            "error": f"Video not found: {video_path}",
            "note": "Place a licensed test video at this path",
        }

    try:
        result = answer_question(video_path, tc["question"], tc["target_lang"])
        result["test_case"] = tc["id"]
        result["expected"] = tc["expected"]
        return result
    except Exception as e:
        return {
            "test_case": tc["id"],
            "status": "error",
            "error": str(e),
        }


def run_all_tests() -> List[Dict[str, Any]]:
    """Run TC1–TC4, return list of results."""
    results = []
    for tc in TEST_CASES:
        print(f"\n=== Running {tc['id']}: {tc['name']} ===")
        result = run_test_case(tc)
        results.append(result)
        print(f"Status: {result.get('status')}")
        if result.get("answer"):
            print(f"Answer: {result['answer'][:100]}...")
        if result.get("error"):
            print(f"Error: {result['error']}")
    return results


def print_summary(results: List[Dict[str, Any]]):
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for r in results:
        tc = r.get("test_case", "?")
        status = r.get("status", "?")
        print(f"{tc}: {status}")
        if r.get("error"):
            print(f"  → {r['error']}")


if __name__ == "__main__":
    results = run_all_tests()
    print_summary(results)