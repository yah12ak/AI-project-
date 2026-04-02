import streamlit as st
import pdfplumber
import requests
import google.generativeai as genai

# Load API keys
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]

# Title
st.title("📄 AI Document Orchestrator")

# Upload file
uploaded_file = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])

# User question
question = st.text_input("Ask a question about the document")

# Function to extract text
def extract_text(file):
    text = ""
    try:
        if file.name.lower().endswith(".pdf"):
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
        else:
            text = file.read().decode("utf-8", errors="replace")
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return ""
    return text.strip()

# Step 1 + 2
if uploaded_file and question:
    text = extract_text(uploaded_file)
    if not text:
        st.warning("No text was extracted from the uploaded document.")
    else:
        st.subheader("📌 Extracted Text Preview")
        st.write(text[:500])

        # Gemini Prompt
        prompt = f"""
Extract 5-8 important key-value pairs from this text based on the question below.
Return JSON only.
Question: {question}
Text: {text}
"""

        extracted_data = None
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            extracted_data = response.text
        except Exception as e:
            st.error(f"Error from Gemini API: {e}")

        if extracted_data:
            st.subheader("📊 Extracted JSON")
            st.code(extracted_data, language="json")

            # Email input
            email = st.text_input("Enter recipient email")

            # Button
            if st.button("Send Alert Mail"):
                if not email:
                    st.warning("Please enter a recipient email before sending.")
                else:
                    payload = {
                        "text": text,
                        "question": question,
                        "extracted_data": extracted_data,
                        "email": email,
                    }
                    try:
                        res = requests.post(WEBHOOK_URL, json=payload, timeout=30)
                        if res.status_code == 200:
                            data = res.json()
                            st.subheader("🧠 Final Answer")
                            st.write(data.get("final_answer", "(no final_answer returned)"))
                            st.subheader("📧 Email Body")
                            st.write(data.get("email_body", "(no email_body returned)"))
                            st.subheader("📢 Status")
                            st.success(data.get("status", "success"))
                        else:
                            st.error(f"Webhook failed: {res.status_code} {res.text}")
                    except Exception as e:
                        st.error(f"Webhook request error: {e}")
