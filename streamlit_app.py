# 🚀 Advanced Personal Finance Tracker with Multi-AI Fallback

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import time
import requests

# Optional Gemini
try:
    from google import genai
except:
    genai = None

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Finance AI Tracker Pro", layout="wide")

# ---------------- SESSION INIT ----------------
if "expenses" not in st.session_state:
    st.session_state.expenses = pd.DataFrame(columns=["Date","Category","Amount","Note"])

if "budget" not in st.session_state:
    st.session_state.budget = {
        "Food":5000, "Rent":15000, "Transport":2000,
        "Entertainment":3000, "Shopping":4000, "Other":3000
    }

if "ai_calls" not in st.session_state:
    st.session_state.ai_calls = 0

if "last_call" not in st.session_state:
    st.session_state.last_call = 0

# ---------------- HELPER ----------------
def monthly_filter(df):
    now = datetime.now()
    return df[(pd.to_datetime(df['Date']).dt.month == now.month)]

# ---------------- AI LAYERS ----------------
def gemini_ai(prompt):
    try:
        if not genai: return None
        client = genai.Client(api_key=st.secrets.get("GOOGLE_API_KEY"))
        res = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return res.text
    except:
        return None


def openrouter_ai(prompt):
    try:
        key = st.secrets.get("OPENROUTER_API_KEY")
        if not key: return None

        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen/qwen-2.5-7b-instruct",
                "messages": [{"role":"user","content":prompt}]
            }
        )
        return r.json()['choices'][0]['message']['content']
    except:
        return None


def local_ai(df, budget):
    insights = []
    total = df['Amount'].sum()

    for cat in budget:
        spent = df[df['Category']==cat]['Amount'].sum()
        if spent > budget[cat]:
            insights.append(f"⚠️ Overspending in {cat}")
        else:
            insights.append(f"✅ Good in {cat}")

    insights.append(f"💰 Total spent: ₹{total}")
    return "\n".join(["- "+i for i in insights])


def get_ai(df, budget):
    if time.time() - st.session_state.last_call < 20:
        return "⏳ Wait before next AI call"

    st.session_state.last_call = time.time()

    summary = df.groupby('Category')['Amount'].sum().sort_values(ascending=False).head(5)

    prompt = "Analyze this spending:\n"
    for c,a in summary.items():
        prompt += f"{c}: ₹{a}\n"

    # Try Gemini
    res = gemini_ai(prompt)
    if res: return res

    # Try OpenRouter
    res = openrouter_ai(prompt)
    if res: return res

    return local_ai(df, budget)

# ---------------- UI ----------------
st.title("💰 Finance Tracker Pro")

# Sidebar
st.sidebar.header("⚙️ Settings")
salary = st.sidebar.number_input("Monthly Income", value=30000)

# Budget Editor
st.sidebar.subheader("Budget")
for k in list(st.session_state.budget.keys()):
    st.session_state.budget[k] = st.sidebar.number_input(k, value=st.session_state.budget[k])

# Add Expense
st.subheader("➕ Add Expense")
with st.form("exp"):
    col1,col2,col3 = st.columns(3)
    date = col1.date_input("Date")
    cat = col2.selectbox("Category", list(st.session_state.budget.keys()))
    amt = col3.number_input("Amount", min_value=1.0)
    note = st.text_input("Note")

    if st.form_submit_button("Add"):
        new = pd.DataFrame([[date,cat,amt,note]], columns=["Date","Category","Amount","Note"])
        st.session_state.expenses = pd.concat([st.session_state.expenses,new])
        st.success("Added")

# Data
if not st.session_state.expenses.empty:
    df = monthly_filter(st.session_state.expenses)

    st.subheader("📊 Overview")
    total = df['Amount'].sum()
    savings = salary - total

    c1,c2,c3 = st.columns(3)
    c1.metric("Income", salary)
    c2.metric("Spent", total)
    c3.metric("Savings", savings)

    # Charts
    st.subheader("📈 Charts")

    pie = px.pie(df, names='Category', values='Amount')
    st.plotly_chart(pie, use_container_width=True)

    bar = px.bar(df.groupby('Category')['Amount'].sum().reset_index(), x='Category', y='Amount')
    st.plotly_chart(bar, use_container_width=True)

    # AI
    st.subheader("🤖 AI Insights")
    if st.button("Generate Insights"):
        with st.spinner("Thinking..."):
            out = get_ai(df, st.session_state.budget)
            st.markdown(out)

    st.subheader("📑 Data")
    st.dataframe(st.session_state.expenses)
else:
    st.info("Add some expenses to start 🚀")
