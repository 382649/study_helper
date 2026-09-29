import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader

MODEL = "gemini-2.5-flash"
MAX_QUESTIONS = 30
MAX_NOTES_CHARS = 60000

st.set_page_config(page_title="Study Helper", page_icon="📚")
st.title("📚 Study Helper")
st.caption("Upload your notes, then ask questions or get quizzed.")

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

SYSTEM = """You are a friendly study helper.
Answer ONLY using the student's notes below. If the answer is not in the notes, say so.
Explain simply. If asked for a quiz, ask ONE question at a time, wait for the answer,
say if it is right and explain why, then ask the next one.

--- NOTES ---
{notes}
--- END NOTES ---"""


def read_file(f):
    if f.name.lower().endswith(".pdf"):
        return "\n".join(p.extract_text() or "" for p in PdfReader(f).pages)
    return f.read().decode("utf-8", errors="ignore")


uploaded = st.file_uploader("Upload PDF or text notes", type=["pdf", "txt", "md"])
pasted = st.text_area("...or paste notes here", height=120)

notes = (read_file(uploaded) if uploaded else pasted).strip()[:MAX_NOTES_CHARS]

if "history" not in st.session_state:
    st.session_state.history = []
    st.session_state.count = 0

if not notes:
    st.info("Add your notes to begin.")
    st.stop()

col1, col2 = st.columns(2)
quick = None
if col1.button("🎯 Quiz me"):
    quick = "Quiz me on my notes. Ask the first question."
if col2.button("📝 Summarize"):
    quick = "Summarize my notes briefly."

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.write(m["content"])

prompt = st.chat_input("Ask a question or answer the quiz...") or quick

if prompt:
    if st.session_state.count >= MAX_QUESTIONS:
        st.warning("Question limit reached for this session. Refresh to start again.")
        st.stop()
    st.session_state.count += 1
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        try:
            contents = [
                types.Content(
                    role="user" if m["role"] == "user" else "model",
                    parts=[types.Part(text=m["content"])],
                )
                for m in st.session_state.history
            ]
            r = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM.format(notes=notes),
                    max_output_tokens=2000,
                ),
            )
            answer = r.text or "No answer was returned. Please try again."
        except Exception as e:
            answer = f"Error: {e}"
        st.write(answer)
    st.session_state.history.append({"role": "assistant", "content": answer})
