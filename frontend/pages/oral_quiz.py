import streamlit as st
import requests
import base64
import time
import math,os

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Language selector
lang = st.selectbox(
    "🌍 Choose Language",
    options=["en", "hi", "es", "fr"],
    format_func=lambda x: {"en":"English", "hi":"Hindi", "es":"Spanish", "fr":"French"}[x],
    index=0
)
st.session_state["lang"] = lang


# ---------------- Utilities ----------------
def play_tts(text: str):
    """Render and immediately play TTS for given text (Chrome + Safari friendly)."""
    audio_resp = requests.post(
        f"{API_URL}/tts",
        params={"text": text, "lang": st.session_state.get("lang", "en")}
    )

    if audio_resp.status_code == 200:
        b64 = base64.b64encode(audio_resp.content).decode()
        md = f"""
            <audio id="tts_audio" autoplay>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                // Try to play immediately (Safari sometimes needs this explicit call)
                var audio = document.getElementById("tts_audio");
                if (audio) {{
                  audio.play().catch(e => console.log("Autoplay blocked:", e));
                }}
            </script>
        """
        st.markdown(md, unsafe_allow_html=True)

def estimate_tts_seconds(text: str) -> float:
    """
    Rough duration estimate so we can wait for feedback to finish before advancing.
    ~150 wpm ≈ 2.5 words/sec, ~5 chars/word → ~12.5 chars/sec.
    """
    chars_per_sec = 12.5
    sec = len(text) / chars_per_sec
    # Clamp to a sensible range and add a small buffer
    return max(2.0, min(8.0, sec + 0.7))

# ---------------- Session init ----------------
if "quiz" not in st.session_state:
    st.session_state["quiz"] = []
if "current_q" not in st.session_state:
    st.session_state["current_q"] = 0
if "score" not in st.session_state:
    st.session_state["score"] = 0
# Track which question has already been auto-spoken to avoid re-speaking on every rerun
if "spoken_q_index" not in st.session_state:
    st.session_state["spoken_q_index"] = -1

# ---------------- Page config ----------------
st.set_page_config(page_title="🎤 Oral Quiz Mode", page_icon="🎧")
st.title("🎤 Oral Quiz Mode with TTS")

# ---------------- Flow ----------------
# Ensure file is uploaded first
if "filename" not in st.session_state:
    st.warning("⚠️ Please upload a PDF first from the main app.")
else:
    if st.button("📝 Start Oral Quiz"):
        resp = requests.post(
            f"{API_URL}/quiz",
            data={
            "filename": st.session_state['filename'],
            "lang": st.session_state.get("lang", "en")
            }
        )

        if resp.status_code == 200:
            st.session_state["quiz"] = resp.json().get("quiz", [])
            st.session_state["current_q"] = 0
            st.session_state["score"] = 0
            st.session_state["spoken_q_index"] = -1

# ---------------- Render current question ----------------
if st.session_state["quiz"]:
    quiz_data = st.session_state["quiz"]
    i = st.session_state["current_q"]

    if i < len(quiz_data):
        q = quiz_data[i]
        st.markdown(f"**Q{i+1}. {q['question']}**")

        # Auto-play this question ONCE (avoid re-speaking when user changes radio selection)
        if st.session_state["spoken_q_index"] != i:
            play_tts(q["question"])
            st.session_state["spoken_q_index"] = i

        # Repeat button
        if st.button("🔁 Repeat Question"):
            play_tts(q["question"])

        # Options
        selected = st.radio(
            f"Choose answer for Q{i+1}",
            q["options"],
            key=f"oral_q_{i}"
        )

        # Check Answer
        if st.button(f"✅ Check Q{i+1}"):
            # Build feedback text & speak it
            if selected == q["answer"]:
                st.success("✅ Correct!")
                feedback = f"Correct! {q['answer']} is the right answer."
                st.session_state["score"] += 1
            else:
                st.error(f"❌ Wrong! Correct answer: {q['answer']}")
                feedback = f"Wrong! The correct answer is {q['answer']}."
            play_tts(feedback)

            # Wait long enough for feedback TTS to finish before advancing
            time.sleep(estimate_tts_seconds(feedback))

            # Advance to next question and ensure that question will auto-speak once
            st.session_state["current_q"] += 1
            st.session_state["spoken_q_index"] = -1
            st.rerun()

    else:
        total = len(quiz_data)
        score = st.session_state["score"]
        st.success(f"🎉 Quiz completed! You scored {score}/{total}")
        play_tts(f"Congratulations! You scored {score} out of {total}.")
