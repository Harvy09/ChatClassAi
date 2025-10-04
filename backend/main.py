from fastapi import FastAPI, UploadFile, File, Form ,Query
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from llm_client import query_llm
from rag_utils import index_pdf, retrieve_chunks, collection
from utils import translate_text
from gtts import gTTS
from dotenv import load_dotenv

import re,json,fitz,os,uuid

app = FastAPI()


load_dotenv()
GATEWAY_URL = os.getenv("GATEWAY_URL")

# allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# store docs
documents = {}

# PDF text extractor
def extract_text_from_pdf(file_bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    chunks_count = index_pdf(file_path, file.filename)
    return {"status": "ok", "chunks_indexed": chunks_count, "filename": file.filename}


@app.post("/ask")
async def ask_question(filename: str = Form(...), query: str = Form(...), lang: str = Form("en")):
    # 1. Translate query to English if needed
    query_en = query if lang == "en" else translate_text(query, target_lang="en")

    # 2. Retrieve relevant chunks
    results = collection.query(
        query_texts=[query_en],
        n_results=3,
        where={"doc_id": filename}
    )

    if not results["documents"]:
        return {"answer": "No relevant context found."}

    context = "\n".join(results["documents"][0])

    # 3. Build LLM messages
    messages = [
        {"role": "system", "content": "You are a helpful study assistant. Only answer using the given context."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query_en}"}
    ]

    answer_en = query_llm(messages)

    # 4. Translate back if needed
    answer = answer_en if lang == "en" else translate_text(answer_en, target_lang=lang)

    return {"answer": answer}



@app.post("/summarize")
async def summarize(filename: str = Form(...), lang: str = Form("en")):
    results = collection.get(where={"doc_id": filename})
    if not results["documents"]:
        return {"error": "File not uploaded or indexed"}

    all_text = " ".join(results["documents"])
    context = all_text[:4000]

    messages = [
        {"role": "system", "content": "You are a helpful study assistant."},
        {"role": "user", "content": (
            "Summarize the following text into exactly 5 concise bullet points. "
            "Format the output with each bullet starting on a new line with '- ':\n\n"
            f"{context}"
        )}
    ]

    summary_en = query_llm(messages, max_tokens=500)
    summary = summary_en if lang == "en" else translate_text(summary_en, target_lang=lang)

    return {"summary": summary}



# --- TTS Agent ---
@app.post("/tts")
def text_to_speech(text: str = Query(...), lang: str = Query("en")):
    mp3_path = None
    try:
        file_id = str(uuid.uuid4())
        mp3_path = f"output_{file_id}.mp3"

        # Generate MP3 in the chosen language
        tts = gTTS(text=text, lang=lang)
        tts.save(mp3_path)

        # Read file bytes
        with open(mp3_path, "rb") as f:
            mp3_data = f.read()

        # Headers needed for Safari playback
        headers = {
            "Content-Type": "audio/mpeg",
            "Content-Disposition": 'inline; filename="speech.mp3"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(mp3_data))
        }

        return Response(content=mp3_data, headers=headers, media_type="audio/mpeg")

    except Exception as e:
        return {"error": str(e)}
    finally:
        # Cleanup generated file
        if mp3_path and os.path.exists(mp3_path):
            os.remove(mp3_path)


# -- quiz --
@app.post("/quiz")
async def generate_quiz(filename: str = Form(...), lang: str = Form("en")):
    # Fetch file chunks
    results = collection.get(where={"doc_id": filename})
    if not results["documents"]:
        return {"error": "File not uploaded or indexed"}
    
    all_text = " ".join(results["documents"])
    context = all_text[:4000]

    messages = [
        {"role": "system", "content": "You are a teacher who creates quizzes for students."},
        {"role": "user", "content": f"""
          Generate 5 multiple-choice questions from the text below.  
          Each question must have:
          - "question": the question as a string  
          - "options": a list of 4 answer choices (strings only, no dicts)  
          - "answer": the correct option text  

          Return ONLY a valid JSON array. No explanations, no markdown, no extra text.

          Text:
          {context}
        """}
    ]

    raw = query_llm(messages, max_tokens=1000)

    try:
        json_text = re.search(r"\[.*\]", raw, re.DOTALL).group(0)
        quiz = json.loads(json_text)

        # Translate if needed
        if lang != "en":
            for q in quiz:
                q["question"] = translate_text(q["question"], target_lang=lang)
                q["options"] = [translate_text(opt, target_lang=lang) for opt in q["options"]]
                q["answer"] = translate_text(q["answer"], target_lang=lang)

        return {"quiz": quiz}

    except Exception as e:
        return {"error": "Invalid JSON", "raw": raw, "exception": str(e)}


