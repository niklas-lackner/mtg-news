import os
import requests
import datetime
import tenacity  # Make sure you have installed it: pip install tenacity

# --- Configuration ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
if not NEWS_API_KEY or not HUGGINGFACE_API_TOKEN:
    raise Exception("Missing API keys! Set NEWS_API_KEY and HUGGINGFACE_API_TOKEN as environment variables.")

POSTS_FOLDER = os.path.join("docs", "_posts")
os.makedirs(POSTS_FOLDER, exist_ok=True)

# --- Fetch MTG News from NewsAPI ---
query = "Magic: The Gathering"
url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
response = requests.get(url)
data = response.json()
if data.get("status") != "ok":
    raise Exception("Error fetching news:", data)
articles = data.get("articles", [])
if not articles:
    raise Exception("No articles found for query.")
selected_articles = articles[:5]
article_summaries = "\n".join(
    [f"- {article['title']} ({article['url']})" for article in selected_articles]
)

# --- Prepare the prompt ---
prompt = (
    "Generate a concise blog post (max 3 paragraphs) about Magic: The Gathering news. "
    "Include a brief introduction, a short summary for each news item, and a concise conclusion. "
    "Do not include any URLs or external references in the final output. "
    "News Headlines:\n" +
    article_summaries +
    "\n\nBlog Post:"
)

# --- Function to call Hugging Face API with retries ---
@tenacity.retry(
    wait=tenacity.wait_random_exponential(min=5, max=60),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type(Exception)
)
def generate_blog_post(prompt):
    API_URL = "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-2.7B"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 1000, "temperature": 0.7, "do_sample": True}
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()
    if "error" in result:
        raise Exception(result["error"])
    if isinstance(result, list) and "generated_text" in result[0]:
        return result[0]["generated_text"].strip()
    raise Exception("Unexpected response format from Hugging Face API", result)

try:
    blog_text = generate_blog_post(prompt)
except Exception as e:
    raise Exception("Failed to generate blog post after retries:", e)

# --- Optional: Remove Duplicate Lines ---
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

# --- Save the post as a Markdown file ---
today_str = datetime.date.today().isoformat()
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
