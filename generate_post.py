import os
import requests
import datetime

# --- Configuration ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
if not NEWS_API_KEY or not HUGGINGFACE_API_TOKEN:
    raise Exception("Missing API keys! Set NEWS_API_KEY and HUGGINGFACE_API_TOKEN as environment variables.")

# Folder to store blog posts (ensure this folder exists in your repo)
POSTS_FOLDER = os.path.join("docs", "_posts")
os.makedirs(POSTS_FOLDER, exist_ok=True)

# --- Step 1: Fetch MTG News from NewsAPI ---
query = "Magic: The Gathering"
url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
response = requests.get(url)
data = response.json()

if data.get("status") != "ok":
    raise Exception("Error fetching news:", data)

articles = data.get("articles", [])
if not articles:
    raise Exception("No articles found for query.")

# Select top 5 articles (or fewer if less are available)
selected_articles = articles[:5]
article_summaries = "\n".join(
    [f"- {article['title']} ({article['url']})" for article in selected_articles]
)

# --- Step 2: Generate Blog Post with Hugging Face Inference API ---
prompt = (
    f"Write a short, engaging blog post summarizing the latest Magic: The Gathering news. "
    f"Include an introduction, a brief summary of each news item, and a conclusion. "
    f"Here are the news headlines and links:\n\n{article_summaries}\n\n"
    f"Keep it concise and fun."
)

# Set the API endpoint (you can try other models if desired)
API_URL = "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-2.7B"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
payload = {"inputs": prompt, "parameters": {"max_new_tokens": 300}}

hf_response = requests.post(API_URL, headers=headers, json=payload)
hf_response_json = hf_response.json()

# Check the response format and extract generated text
if isinstance(hf_response_json, list) and "generated_text" in hf_response_json[0]:
    blog_text = hf_response_json[0]["generated_text"].strip()
else:
    raise Exception("Unexpected response format from Hugging Face API", hf_response_json)

# --- Step 3: Save the Post as a Markdown File ---
today_str = datetime.date.today().isoformat()  # e.g., "2025-02-04"
filename = os.path.join(POSTS_FOLDER, f"{today_str}-mtg-news.md")

markdown_content = f"""---
title: "MTG News for {today_str}"
date: {today_str}
---

{blog_text}
"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"Blog post generated: {filename}")
