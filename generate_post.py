import os
import requests
import datetime

# --- Configuration ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
if not NEWS_API_KEY or not HUGGINGFACE_API_TOKEN:
    raise Exception("Missing API keys! Set NEWS_API_KEY and HUGGINGFACE_API_TOKEN as environment variables.")

hf_response = requests.post(API_URL, headers=headers, json=payload)
hf_response_json = hf_response.json()
print("Raw Hugging Face response:", hf_response_json)


# Folder to store blog posts (for Jekyll, posts are usually in _posts)
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
# Refine the prompt to avoid repeated information.
prompt = (
    "Write a short, engaging blog post summarizing the latest Magic: The Gathering news. "
    "The blog post should include a brief introduction, a short summary for each news item, "
    "and a concise conclusion. Do not repeat any headlines or information. "
    "Here are the news headlines and links:\n\n" +
    article_summaries + "\n\n" +
    "Keep it concise and fun."
)

API_URL = "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-2.7B"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
# Adjust parameters as needed; lower max_new_tokens and temperature to help control length and repetition.
payload = {"inputs": prompt, "parameters": {"max_new_tokens": 200, "temperature": 0.5}}

hf_response = requests.post(API_URL, headers=headers, json=payload)
hf_response_json = hf_response.json()

if isinstance(hf_response_json, list) and "generated_text" in hf_response_json[0]:
    blog_text = hf_response_json[0]["generated_text"].strip()
else:
    raise Exception("Unexpected response format from Hugging Face API", hf_response_json)

# --- Optional Step: Remove Duplicate Lines ---
def remove_duplicate_lines(text):
    seen = set()
    unique_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped not in seen:
            unique_lines.append(line)
            seen.add(stripped)
    return "\n".join(unique_lines)

blog_text = remove_duplicate_lines(blog_text)

# --- Step 3: Save the Post as a Markdown File ---
# Use the current date and time for the filename so that each run produces a unique file.
today_str = datetime.date.today().isoformat()  # Format: YYYY-MM-DD
timestamp = datetime.datetime.now().strftime("%H%M%S")
filename = os.path.join(POSTS_FOLDER, f"{today_str}-{timestamp}-mtg-news.md")

markdown_content = f"""---
title: "MTG News for {today_str}"
date: {today_str}
---

{blog_text}
"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"Blog post generated: {filename}")
