import os
import requests
import datetime

# --- Configuration ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
if not NEWS_API_KEY or not HUGGINGFACE_API_TOKEN:
    raise Exception("Missing API keys! Set NEWS_API_KEY and HUGGINGFACE_API_TOKEN as environment variables.")

# For Jekyll, place posts in the _posts folder inside docs
POSTS_FOLDER = os.path.join("docs", "_posts")
os.makedirs(POSTS_FOLDER, exist_ok=True)

# --- Step 1: Fetch a News Headline from NewsAPI ---
query = "Magic: The Gathering"
url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
response = requests.get(url)
data = response.json()

if data.get("status") != "ok":
    raise Exception("Error fetching news:", data)

articles = data.get("articles", [])
if not articles:
    raise Exception("No articles found for query.")

# Use only one article for a concise summary.
selected_article = articles[0]
article_summary = f"- {selected_article['title']}"
# Extract the news source from the selected article
source_name = selected_article.get('source', {}).get('name', 'Unknown Source')

# --- Step 2: Generate a Very Concise Summary Using Hugging Face ---
# Construct a prompt that asks for a one-paragraph summary without including URLs.
prompt = (
    "Generate a very concise summary (one short paragraph) of the following Magic: The Gathering news headline. "
    "Do not include any URLs or references in the final output. "
    "News Headline:\n" +
    article_summary +
    "\n\nSummary:"
)

# Use a model that fits within the context window; here we use EleutherAI/gpt-neo-2.7B.
API_URL = "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-2.7B"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

payload = {
    "inputs": prompt,
    "parameters": {
        "max_new_tokens": 1337,  # Adjust as needed so total tokens (prompt + output) <= 2048
        "temperature": 0.7,
        "do_sample": True,
        "stop": ["\n\n"],
    }
}

hf_response = requests.post(API_URL, headers=headers, json=payload)
hf_response_json = hf_response.json()

# Debug: Uncomment the next line to print the raw response for troubleshooting.
# print("Raw Hugging Face response:", hf_response_json)

if isinstance(hf_response_json, list) and "generated_text" in hf_response_json[0]:
    generated_text = hf_response_json[0]["generated_text"].strip()
else:
    raise Exception("Unexpected response format from Hugging Face API", hf_response_json)

# Remove the prompt from the generated text if it is included.
if generated_text.startswith(prompt):
    summary = generated_text[len(prompt):].strip()
else:
    summary = generated_text

# Append the news source at the end of the summary.
final_output = f"{summary}\n\nSource: {source_name}"

# --- Step 3: Save the Summary as a Markdown File ---
today_str = datetime.date.today().isoformat()  # e.g., "2025-02-05"
timestamp = datetime.datetime.now().strftime("%H%M%S")
filename = os.path.join(POSTS_FOLDER, f"{today_str}-{timestamp}-mtg-news.md")

markdown_content = f"""---
title: "MTG News for {today_str}"
date: {today_str}
---

{final_output}
"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"Blog post generated: {filename}")
