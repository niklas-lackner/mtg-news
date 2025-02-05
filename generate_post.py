import os
import requests
import datetime
import tenacity  # Ensure you've installed it: pip install tenacity
import urllib.parse

# --- Configuration ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
if not NEWS_API_KEY or not HUGGINGFACE_API_TOKEN:
    raise Exception("Missing API keys! Set NEWS_API_KEY and HUGGINGFACE_API_TOKEN as environment variables.")

# For Jekyll, place posts in the _posts folder inside docs
POSTS_FOLDER = os.path.join("docs", "_posts")
os.makedirs(POSTS_FOLDER, exist_ok=True)

# --- Step 1: Fetch a News Article from NewsAPI ---
query = '"Magic: The Gathering" AND competitive'
encoded_query = urllib.parse.quote(query)
url = f"https://newsapi.org/v2/everything?q={encoded_query}&sortBy=relevancy&language=en&apiKey={NEWS_API_KEY}"
response = requests.get(url)
data = response.json()
if data.get("status") != "ok":
    raise Exception("Error fetching news:", data)

articles = data.get("articles", [])
if not articles:
    raise Exception("No articles found for query.")

# Use only one article for the summary.
selected_article = articles[0]
headline = selected_article.get('title', 'No Title')
article_content = selected_article.get('description') or selected_article.get('content') or headline
source_name = selected_article.get('source', {}).get('name', 'Unknown Source')
article_url = selected_article.get('url', 'No URL')

# --- Step 2: Generate a Detailed Summary Using Hugging Face Inference API ---
prompt = (
    "Summarize the following Magic: The Gathering news article completely without altering its content too much. "
    "Ensure that all key points are included and maintain the article's original details. "
    "Your summary should be comprehensive, using up to 1000 tokens if necessary. "
    "Do not omit any important information. \n\n"
    "Headline: " + headline + "\n\n"
    "Article Content: " + article_content + "\n\n"
    "Summary:"
)

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
        "parameters": {
            "max_new_tokens": 1000,
            "temperature": 0.7,
            "do_sample": True,
            # "stop": ["\n\n"]  # Optional: uncomment if needed.
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()
    if "error" in result:
        raise Exception(result["error"])
    if isinstance(result, list) and "generated_text" in result[0]:
        return result[0]["generated_text"].strip()
    raise Exception("Unexpected response format from Hugging Face API", result)

try:
    generated_text = generate_blog_post(prompt)
except Exception as e:
    raise Exception("Failed to generate blog post after retries:", e)

# Remove the prompt from the generated text if it is included.
if generated_text.startswith(prompt):
    summary = generated_text[len(prompt):].strip()
else:
    summary = generated_text

# --- Create a Custom Title with a Spoiler ---
# Extract the first sentence from the summary. If there's no period, use the first 60 characters.
if '.' in summary:
    custom_excerpt = summary.split('.')[0].strip()
else:
    custom_excerpt = summary[:60].strip()

custom_title = f"MTG News for {datetime.date.today().isoformat()} - {custom_excerpt}"

# Append the news source and URL at the end of the summary.
final_output = f"{summary}\n\nSource: {source_name} ({article_url})"

# --- Step 3: Save the Summary as a Markdown File ---
today_str = datetime.date.today().isoformat()  # e.g., "2025-02-05"
timestamp = datetime.datetime.now().strftime("%H%M%S")
filename = os.path.join(POSTS_FOLDER, f"{today_str}-{timestamp}-mtg-news.md")

markdown_content = f"""---
title: "{custom_title}"
date: {today_str}
---

{final_output}
"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"Blog post generated: {filename}")
