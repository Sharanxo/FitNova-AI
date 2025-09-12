from fpdf import FPDF
from db import query_db
from groq import Groq
from datetime import datetime
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def clean_text(text):
    """Ensure text contains only Latin-1 characters for PDF"""
    if not text:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, clean_text("Nova AI – Fitness Report"), ln=True, align='C')
        self.set_font("Arial", '', 10)
        self.cell(0, 10, clean_text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True, align='C')
        self.ln(10)

def generate_user_report(user_id, username):
    pdf = PDF()
    pdf.add_page()
    u = query_db("SELECT * FROM users WHERE id=%s", (user_id,), fetchone=True)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_text("User Profile"), ln=True)
    pdf.set_font("Arial", '', 10)
    for key in ['name', 'email', 'age', 'gender', 'weight', 'height']:
        pdf.cell(0, 8, clean_text(f"{key.title()}: {u[key]}"), ln=True)

    workouts = query_db("SELECT * FROM workouts WHERE user_id=%s", (user_id,))
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_text("Workouts"), ln=True)
    pdf.set_font("Arial", '', 10)
    for w in workouts:
        workout_line = f"{w['date']} - {w['exercise']} ({w['duration']} min, {w['calories_burned']} cal)"
        pdf.cell(0, 8, clean_text(workout_line), ln=True)

    goals = query_db("SELECT * FROM goals WHERE user_id=%s", (user_id,))
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_text("Goals"), ln=True)
    pdf.set_font("Arial", '', 10)
    for g in goals:
        goal_line = f"{g['goal_type']}: {g['current_value']}/{g['target_value']} ({g['status']})"
        pdf.cell(0, 8, clean_text(goal_line), ln=True)

    # AI Summary
    gtext = "\n".join([f"{g['goal_type']}: {g['current_value']}/{g['target_value']}" for g in goals])
    wtext = "\n".join([f"{w['date']} {w['exercise']}" for w in workouts])
    prompt = f"Summarize this user's progress.\nGoals:\n{gtext}\nWorkouts:\n{wtext}"

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Updated from deprecated llama3-8b-8192
        messages=[{"role": "user", "content": prompt}]
    )
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_text("AI Summary"), ln=True)
    pdf.set_font("Arial", '', 10)
    for line in response.choices[0].message.content.split('\n'):
        pdf.multi_cell(0, 8, clean_text(line))

    filename = f"{username.replace(' ', '_')}_fitness_report.pdf"
    pdf.output(filename)
    return filename
