import os
import requests
import datetime
import tenacity  # Ensure you've installed it: pip install tenacity
import urllib.parse
import re

# --- Configuration ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
if not NEWS_API_KEY or not HUGGINGFACE_API_TOKEN:
    raise Exception("Missing API keys! Set NEWS_API_KEY and HUGGINGFACE_API_TOKEN as environment variables.")

# For Jekyll, posts go into the _posts folder inside docs
POSTS_FOLDER = os.path.join("docs", "_posts")
os.makedirs(POSTS_FOLDER, exist_ok=True)

# --- Step 1: Fetch a Relevant News Article from NewsAPI ---
# Using a refined query to get articles that are truly about Magic: The Gathering tournaments/news.
query = '"Magic: The Gathering" AND tournament'
encoded_query = urllib.parse.quote(query)
url = f"https://newsapi.org/v2/everything?q={encoded_query}&sortBy=relevancy&language=en&apiKey={NEWS_API_KEY}"
response = requests.get(url)
data = response.json()
if data.get("status") != "ok":
    raise Exception("Error fetching news:", data)
articles = data.get("articles", [])
if not articles:
    raise Exception("No articles found for query.")

# Select the first article
selected_article = articles[0]

# Optional: Print key details for debugging
print("Selected article details:")
print("Title:", selected_article.get('title', 'No Title'))
print("Description:", selected_article.get('description', 'No Description'))
print("Source:", selected_article.get('source', {}).get('name', 'Unknown Source'))
print("URL:", selected_article.get('url', 'No URL'))

headline = selected_article.get('title', 'No Title')
# Prefer description if available; if not, fall back to content or headline.
article_content = selected_article.get('description') or selected_article.get('content') or headline
source_name = selected_article.get('source', {}).get('name', 'Unknown Source')
article_url = selected_article.get('url', 'No URL')

# --- Step 2: Generate a Concise Summary Using Hugging Face Inference API ---
# Construct a prompt that instructs the model to generate exactly 3 distinct sentences.
prompt = (
    "Summarize the following Magic: The Gathering news article in exactly 3 concise sentences. "
    "Each sentence should capture a different key point of the article. "
    "Do not include any URLs or external references. \n\n"
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
            "max_new_tokens": 300,  # Allow up to 300 tokens for the summary.
            "temperature": 0.7,
            "do_sample": True,
            # Optionally, specify a stop sequence if desired.
            # "stop": ["\n\n"]
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

# --- Post-process the generated text ---
# Remove the prompt from the generated text if it is included.
if generated_text.startswith(prompt):
    generated_text = generated_text[len(prompt):].strip()

# Split the text into sentences using a simple regex.
sentences = re.split(r'(?<=[.!?])\s+', generated_text)
# Keep only the first three sentences.
summary_sentences = sentences[:3]
summary = " ".join(summary_sentences).strip()

# --- Create a Custom Title with a Spoiler ---
# Use the first sentence as a teaser (limit to 50 characters for brevity).
if summary:
    teaser = summary.split('.')[0].strip()
    teaser = (teaser[:50] + '...') if len(teaser) > 50 else teaser
else:
    teaser = "No summary available"
custom_title = f"MTG News for {datetime.date.today().isoformat()} - {teaser}"

# Append the source and original URL at the end of the summary.
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
