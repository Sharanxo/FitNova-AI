import streamlit as st
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def nutrition_chat(user_id):
    st.subheader("🥗 Nutrition Assistant")

    mode = st.radio("Choose Input Mode:", ["Upload Meal Plan (PDF/Text)", "Ask a Nutrition Question"])

    if mode == "Upload Meal Plan (PDF/Text)":
        uploaded = st.file_uploader("Upload your meal plan file (PDF or TXT)", type=["pdf", "txt"])
        
        if uploaded:
            if uploaded.type == "application/pdf":
                try:
                    import fitz  
                    doc = fitz.open(stream=uploaded.read(), filetype="pdf")
                    text = "\n".join([page.get_text() for page in doc])
                except:
                    st.error("Failed to read PDF file. Please ensure it's a readable text-based PDF.")
                    return
            else:
                text = uploaded.read().decode("utf-8")

            st.text_area("📋 Meal Plan Content", value=text, height=200)

            if st.button("Analyze Nutrition"):
                prompt = f"Analyze this meal plan and give nutrition advice:\n\n{text}"

                with st.spinner("Analyzing..."):
                    try:
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.markdown("### 🍽️ Nutrition Summary")
                        st.success(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"⚠️ Failed to get response: {e}")

    elif mode == "Ask a Nutrition Question":
        query = st.text_area("Ask your question:", "How many calories are in 2 boiled eggs and a glass of milk?")
        
        if st.button("Get Answer") and query:
            with st.spinner("Thinking..."):
                try:
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": query}]
                    )
                    st.markdown("### 🧠 Nutrition Advice")
                    st.success(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"⚠️ Failed to get response: {e}")
