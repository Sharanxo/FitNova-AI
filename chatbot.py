import streamlit as st
from groq import Groq
import os
from db import query_db
import json
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_user_context(user_id):
    user = query_db("SELECT * FROM users WHERE id=%s", (user_id,), fetchone=True)
    if not user:
        return "No profile found."

    weight = user.get('weight') or 70.0
    height_cm = user.get('height') or 170.0

    try:
        height_m = height_cm / 100
        bmi = weight / (height_m ** 2)
    except Exception:
        bmi = 0
        category = "Unknown"
    else:
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

    goals = query_db("SELECT goal_type, current_value, target_value FROM goals WHERE user_id=%s", (user_id,))
    goal_info = "\n".join([f"- {g['goal_type']}: {g['current_value']}/{g['target_value']}" for g in goals]) or "No goals."

    workouts = query_db("SELECT exercise, duration FROM workouts WHERE user_id=%s ORDER BY date DESC LIMIT 5", (user_id,))
    workout_info = "\n".join([f"- {w['exercise']} for {w['duration']} mins" for w in workouts]) or "No workouts yet."

    return (
        f"User profile:\n"
        f"- Age: {user.get('age')} | Gender: {user.get('gender')}\n"
        f"- Weight: {weight} kg | Height: {height_cm} cm\n"
        f"- BMI: {bmi:.1f} ({category})\n\n"
        f"Goals:\n{goal_info}\n\n"
        f"Recent Workouts:\n{workout_info}"
    )


def is_goal_related(message):
    return any(word in message.lower() for word in ["i want to", "my goal is", "lose", "gain", "burn", "reduce", "increase"])

def extract_goal_from_message(message):
    prompt = f"""
Extract a structured fitness goal from this text:

"{message}"

Return in JSON format like:
{{
  "goal_type": "Weight Loss",
  "target_value": 5,
  "end_date": "2025-08-31"
}}

If no valid goal is found, return an empty JSON: {{}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        return {}

def fitness_chatbot(user_id):
    st.subheader("🤖 Personalized Fitness Chatbot")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "quick_ask_message" not in st.session_state:
        st.session_state.quick_ask_message = ""

    st.markdown("**Quick Ask:**")
    cols = st.columns(3)
    with cols[0]:
        if st.button("🏋️ Workout Tip"):
            st.session_state.quick_ask_message = "Give me a workout tip based on my current fitness."
    with cols[1]:
        if st.button("🥗 Diet Plan"):
            st.session_state.quick_ask_message = "Suggest a diet plan based on my goals and BMI."
    with cols[2]:
        if st.button("🎯 Progress Advice"):
            st.session_state.quick_ask_message = "Tell me how I'm progressing and what I can improve."

    user_msg = st.text_input("Ask your question...", value=st.session_state.quick_ask_message)

    if st.button("Send") and user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        st.session_state.quick_ask_message = ""

        context = get_user_context(user_id)

        goal_data = {}
        if is_goal_related(user_msg):
            goal_data = extract_goal_from_message(user_msg)

            if goal_data and all(k in goal_data for k in ["goal_type", "target_value", "end_date"]):
                try:
                    # Save to DB
                    query_db(
                        """INSERT INTO goals (user_id, goal_type, target_value, current_value, start_date, end_date, status)
                           VALUES (%s, %s, %s, 0, %s, %s, 'Active')""",
                        (user_id, goal_data["goal_type"], goal_data["target_value"], datetime.today(), goal_data["end_date"]),
                        commit=True
                    )
                    st.success(f"✅ New Goal Saved: {goal_data['goal_type']} - {goal_data['target_value']} by {goal_data['end_date']}")
                except Exception as e:
                    st.error(f"⚠️ Goal save failed: {e}")

        messages = [
            {"role": "system", "content": "You are Nova AI, a friendly fitness assistant. Provide helpful, personalized advice."},
            {"role": "system", "content": context}
        ] + st.session_state.chat_history[-5:]

        # AI reply
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )
        ai_reply = response.choices[0].message.content
        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})

        # Log chat
        query_db(
            "INSERT INTO chat_logs (user_id, user_message, bot_reply) VALUES (%s, %s, %s)",
            (user_id, user_msg, ai_reply), commit=True
        )

    for msg in st.session_state.chat_history:
        speaker = "🧍‍♂️ You" if msg["role"] == "user" else "🤖 Nova AI"
        st.markdown(f"**{speaker}:** {msg['content']}")

def show_chat_analytics(user_id):
    st.subheader("📊 Chatbot Usage")
    logs = query_db("SELECT user_message, timestamp FROM chat_logs WHERE user_id=%s ORDER BY timestamp DESC LIMIT 10", (user_id,))
    if logs:
        for log in logs:
            st.markdown(f"`{log['timestamp']}` — 🗨️ {log['user_message']}")
    else:
        st.info("No chatbot interactions yet.")
