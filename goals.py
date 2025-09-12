import streamlit as st
from db import query_db
from datetime import datetime
import os
from groq import Groq


client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def set_goal(user_id):
    st.subheader("🎯 Set a Goal")

    goal_type = st.selectbox("Goal Type", ["Weight Loss", "Calories Burned", "Workouts Logged"])
    target = st.number_input("Target Value", min_value=1.0)
    end_date = st.date_input("Target End Date")

    if st.button("Save Goal"):
        query_db(
            """
            INSERT INTO goals (user_id, goal_type, target_value, current_value, start_date, end_date, status)
            VALUES (%s, %s, %s, 0, %s, %s, 'Active')
            """,
            (user_id, goal_type, target, datetime.today(), end_date),
            commit=True
        )
        st.success("✅ Goal saved successfully!")

def view_goals(user_id):
    st.subheader("📈 Your Goals")

    goals = query_db("SELECT * FROM goals WHERE user_id=%s", (user_id,))
    if not goals:
        st.info("No goals set.")
        return

    for g in goals:
        pct = g["current_value"] / g["target_value"] * 100 if g["target_value"] else 0

        st.markdown(f"### {g['goal_type']}")
        st.write(f"Progress: {g['current_value']} / {g['target_value']} ({pct:.1f}%)")
        st.progress(min(pct / 100, 1.0)) 


        if g["status"] != "Completed" and pct >= 100:
            query_db("UPDATE goals SET status='Completed' WHERE id=%s", (g["id"],), commit=True)
            st.success(f"🎉 Goal '{g['goal_type']}' marked as Completed!")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(f"✏️ Update", key=f"upd{g['id']}"):
                new_val = st.number_input(
                    f"New Current Value for {g['goal_type']}",
                    value=float(g["current_value"]),
                    key=f"newval{g['id']}"
                )
                query_db("UPDATE goals SET current_value=%s WHERE id=%s", (new_val, g["id"]), commit=True)
                st.success("✅ Goal progress updated!")

        with col2:
            if st.button(f"🤖 AI Advice", key=f"ai{g['id']}"):
                prompt = f"My current goal is {g['goal_type']}: {g['current_value']} out of {g['target_value']}. Provide advice."
                try:
                    resp = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.info(resp.choices[0].message.content)
                except Exception as e:
                    st.error("⚠️ AI response failed. Check API key or internet connection.")
