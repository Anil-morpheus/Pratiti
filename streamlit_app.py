# pratiti_mvp_app.py

import streamlit as st
import requests
import os
import textwrap
import traceback
import json
from datetime import datetime
import re

# --- Config ---
st.set_page_config(page_title="Pratiti - Business Insight Engine")
st.title("Pratiti")
st.markdown("Paste a business news article to generate contextual insights and supporting research links.")

# Paths
INSIGHT_DB_PATH = "insights.json"

# --- Utility: Load or Save Insight ---
def load_insights():
    if os.path.exists(INSIGHT_DB_PATH):
        with open(INSIGHT_DB_PATH, "r") as f:
            return json.load(f)
    return []

def save_insight(entry):
    insights = load_insights()
    insights.append(entry)
    with open(INSIGHT_DB_PATH, "w") as f:
        json.dump(insights, f, indent=2)

# --- Utility: Query OpenRouter API ---
def query_openrouter(prompt, role_description="You are a helpful assistant."):
    headers = {
        "Authorization": f"Bearer {st.secrets.get('OPENROUTER_API_KEY', os.getenv('OPENROUTER_API_KEY'))}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [
            {"role": "system", "content": role_description},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

# --- Input: Paste Text Only ---
article_text = st.text_area("Paste the full article text:", height=300)

# --- LLM Prompt Templates ---
def generate_prompt(article_text, research_context=""):
    return f"""
You are Pratiti – an advanced financial research analyst. Your job is to read the news article below and produce a single blended narrative insight.

Your insight must include:
- A one-line summary of \"Why This Matters\"
- Contextual summary of the article
- Historical or global comparisons if relevant
- Sector or market impact
- Forward-looking commentary with reasoning

Article:
{article_text}

Relevant research context:
{research_context}
"""

def generate_research_prompt(article_text):
    return f"""
You are a senior research analyst. Based on the article below, list the most relevant and credible publicly available research papers, policy briefs, or news articles from the internet that provide supporting context or critical background.

Each recommendation must include:
- Title or brief summary
- Source
- Link

Do not invent links. Only suggest links that are available publicly and are highly relevant.

Article:
{article_text}
"""

def generate_tag_prompt(article_text):
    return f"""
You are a financial analyst assistant. Categorize the article below into relevant business topics or sectors such as Finance, Energy, Technology, Policy, ESG, etc. 
Respond with a comma-separated list of 3 to 6 tags.

Article:
{article_text}
"""

def generate_sentiment_prompt(article_text):
    return f"""
Analyze the overall sentiment of the following article. Classify it as Positive, Negative, or Neutral. Provide only the label.

Article:
{article_text}
"""

def generate_explanation_prompt(insight):
    return f"""
Explain how the following insight was derived, focusing only on:
- Sector and market impact
- Forward-looking commentary with reasoning

For each, identify what parts of the article contributed to the conclusions, and any assumptions or signals used.

Insight:
{insight}
"""

def highlight_keywords(text, keywords):
    for word in keywords:
        text = re.sub(f"\\b{re.escape(word)}\\b", f"**{word}**", text, flags=re.IGNORECASE)
    return text

# --- Sentiment Sidebar ---
sentiment = ""
if article_text:
    try:
        sentiment_prompt = generate_sentiment_prompt(article_text)
        sentiment = query_openrouter(sentiment_prompt, role_description="You are a sentiment classifier.")
    except:
        sentiment = "Error detecting sentiment."

if sentiment:
    with st.sidebar:
        st.subheader("Sentiment Analysis")
        st.markdown(f"**Sentiment:** {sentiment}")
        st.caption("Sentiment is classified by an LLM based on tone, language, and economic signals in the article.")

# --- Generate Insight With Research ---
if article_text and st.button("Generate Insight with Research"):
    with st.spinner("Running research agent and generating insights..."):
        try:
            research_prompt = generate_research_prompt(article_text)
            research_output = query_openrouter(research_prompt, role_description="You are a research analyst helping senior executives.")

            tag_prompt = generate_tag_prompt(article_text)
            tags_response = query_openrouter(tag_prompt, role_description="You are a tagging assistant.")
            tags = [tag.strip() for tag in tags_response.split(",")]

            insight_prompt = generate_prompt(article_text, research_context=research_output)
            insight = query_openrouter(insight_prompt, role_description="You are a financial research assistant.")

            insight_lines = insight.split("\n")
            why_matters = insight_lines[0] if insight_lines else "N/A"
            full_insight = "\n".join(insight_lines)

            explanation_prompt = generate_explanation_prompt(full_insight)
            explanation = query_openrouter(explanation_prompt, role_description="You explain AI-generated insights clearly.")

            st.subheader("Why This Matters")
            st.write(why_matters)

            st.subheader("Full Insight")
            keywords = tags + ["growth", "inflation", "fiscal deficit", "trade", "market", "RBI", "Fed"]
            highlighted = highlight_keywords(full_insight, keywords)
            st.markdown(highlighted)

            st.subheader("How This Insight Was Derived")
            st.write(explanation)

            st.subheader("Related Research & References")
            st.markdown(research_output)

            st.download_button("Download Insight", full_insight, file_name="pratiti_insight.txt")

            save_insight({
                "timestamp": datetime.now().isoformat(),
                "article": article_text,
                "insight": full_insight,
                "research": research_output,
                "why_matters": why_matters,
                "tags": tags,
                "sentiment": sentiment
            })

        except Exception as e:
            st.error(f"Error generating research-backed insight: {e}")
            st.code(traceback.format_exc(), language="python")
