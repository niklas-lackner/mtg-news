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

# For Jekyll, posts go into the _posts folder inside docs
POSTS_FOLDER = os.path.join("docs", "_posts")
os.makedirs(POSTS_FOLDER, exist_ok=True)

# --- Step 1: Fetch a Relevant News Article from NewsAPI ---
# Use a refined query to target Magic: The Gathering tournament/competitive news.
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

# Optional: Print details for debugging
print("Selected article details:")
print("Title:", selected_article.get('title', 'No Title'))
print("Description:", selected_article.get('description', 'No Description'))
print("Source:", selected_article.get('source', {}).get('name', 'Unknown Source'))
print("URL:", selected_article.get('url', 'No URL'))

headline = selected_article.get('title', 'No Title')
# Use description if available; if not, use content or fall back to headline.
article_content = selected_article.get('description') or selected_article.get('content') or headline
source_name = selected_article.get('source', {}).get('name', 'Unknown Source')
article_url = selected_article.get('url', 'No URL')

# --- Step 2: Generate a Detailed Summary Using Hugging Face Inference API ---
# This prompt instructs the model to summarize the article completely without omitting key details.
prompt = (
    "Summarize the following Magic: The Gathering news article completely without altering its main details. "
    "Ensure that all key points are captured. You may use up to 1000 tokens if needed. "
    "Do not include any URLs or external references in the final output. \n\n"
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
            # Optionally, specify a stop sequence if you need it:
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

# Remove the prompt from the generated text if it is included.
if generated_text.startswith(prompt):
    summary = generated_text[len(prompt):].strip()
else:
    summary = generated_text

# --- Create a Custom Title with a Spoiler ---
# Extract the first sentence (or first 50 characters) as a teaser for the title.
if '.' in summary:
    teaser = summary.split('.')[0].strip()
else:
    teaser = summary[:50].strip()

# Optionally, truncate the teaser if it's too long:
teaser = (teaser[:50] + '...') if len(teaser) > 50 else teaser

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
