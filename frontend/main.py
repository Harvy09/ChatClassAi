import streamlit as st
import requests
import io,os 
import base64
API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="📚 ChatClass AI", page_icon="🎧", layout="wide", initial_sidebar_state="collapsed")

hide_sidebar_style = """
    <style>
        [data-testid="stSidebarNav"] {display: none;}  /* Hide sidebar navigation */
        section[data-testid="stSidebar"] {display: none;}  /* Hide sidebar itself */
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

# Language selector
lang = st.selectbox(
    "🌍 Choose Language",
    options=["en", "hi", "es", "fr"],
    format_func=lambda x: {"en":"English", "hi":"Hindi", "es":"Spanish", "fr":"French"}[x],
    index=0
)
st.session_state["lang"] = lang



def get_audio_md(text_type, check):
    if check:
        text = st.session_state[text_type]
    else:
        text = text_type

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
                var audio = document.getElementById("tts_audio");
                
                document.addEventListener("DOMContentLoaded", function() {{
                    audio.play().catch(e => console.log("Autoplay blocked:", e));
                }});
            </script>
        """
        st.markdown(md, unsafe_allow_html=True)


st.set_page_config(page_title="📚 ChatClass AI", page_icon="🎧")
st.title("📚 ChatClass AI with TTS (Powered by Cerebras + LLaMA)")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
if uploaded_file:
    resp = requests.post(f"{API_URL}/upload", files={"file": uploaded_file})
    if resp.status_code == 200:
        st.success(f"Uploaded ✅ {uploaded_file.name}")
        st.session_state["filename"] = uploaded_file.name
    else:
        st.error("❌ Upload failed")

# --- Ask a Question ---
query = st.text_input("Ask a question from your document:")

if st.button("Ask Question") and "filename" in st.session_state:
    resp = requests.post(
        f"{API_URL}/ask",
        data={
            "filename": st.session_state["filename"],
            "query": query,
            "lang": st.session_state.get("lang", "en")
        }
    )

    if resp.status_code == 200:
        st.session_state["answer"] = resp.json().get("answer", "")

# Display Answer if available
if "answer" in st.session_state and st.session_state["answer"]:
    st.subheader("💡 Answer")
    st.write(st.session_state["answer"])

    if st.button("🎧 Listen to Answer"):
        get_audio_md("answer",True)

# --- Summarize Document ---
if st.button("📖 Summarize Document") and "filename" in st.session_state:
    resp = requests.post(
        f"{API_URL}/summarize",
    data={
         "filename": st.session_state["filename"],
         "query": query,
         "lang": st.session_state.get("lang", "en")
        }
    )

    if resp.status_code == 200:
        st.session_state["summary"] = resp.json().get("summary", "")

# Display Summary if available
if "summary" in st.session_state and st.session_state["summary"]:
    st.subheader("📖 Summary (5 Bullet Points)")
    st.markdown(st.session_state["summary"])    

    if st.button("🎧 Listen to Summary"):
        get_audio_md("summary",True)



if st.button("📝 Generate Oral Quiz") and "filename" in st.session_state:
    resp = requests.post(
    f"{API_URL}/quiz",
    data={
        "filename": st.session_state["filename"],
        "query": query,
        "lang": st.session_state.get("lang", "en")
    }
   )

    if resp.status_code == 200:
        st.session_state["quiz"] = resp.json().get("quiz", [])
        st.switch_page("pages/oral_quiz.py")

