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

# Define folders
POSTS_FOLDER = os.path.join("docs", "_posts")
REDUNDANT_FOLDER = os.path.join("docs", "redundant")
os.makedirs(POSTS_FOLDER, exist_ok=True)
os.makedirs(REDUNDANT_FOLDER, exist_ok=True)

# --- Step 1: Fetch a Relevant News Article from NewsAPI ---
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

selected_article = articles[0]

# (Optional: Print key details for debugging)
print("Selected article details:")
print("Title:", selected_article.get('title', 'No Title'))
print("Description:", selected_article.get('description', 'No Description'))
print("Source:", selected_article.get('source', {}).get('name', 'Unknown Source'))
print("URL:", selected_article.get('url', 'No URL'))

headline = selected_article.get('title', 'No Title')
article_content = selected_article.get('description') or selected_article.get('content') or headline
source_name = selected_article.get('source', {}).get('name', 'Unknown Source')
article_url = selected_article.get('url', 'No URL')

# --- Step 2: Generate a Concise Summary Using Hugging Face Inference API ---
prompt = (
    "Summarize the following Magic: The Gathering news article in 3 concise sentences. "
    "Focus on capturing the key points and avoid altering the main details. "
    "Do not include any URLs or external references in your summary. \n\n"
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
            "max_new_tokens": 300,  # Allows for a concise summary.
            "temperature": 0.7,
            "do_sample": True,
            "stop": ["\n\n"]
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

if generated_text.startswith(prompt):
    summary = generated_text[len(prompt):].strip()
else:
    summary = generated_text

# Append the original article URL and source at the end.
final_output = f"{summary}\n\nSource: {source_name} ({article_url})"

# --- Duplicate Check Function ---
def extract_body(markdown_text):
    """
    Extracts the body content from a Markdown file, ignoring the YAML front matter.
    Assumes front matter is between the first two occurrences of '---'.
    """
    parts = markdown_text.split("---")
    if len(parts) >= 3:
        return parts[2].strip()
    return markdown_text.strip()

def is_duplicate(new_content, folder):
    """
    Checks if new_content (final_output) already exists in any Markdown file in the specified folder.
    """
    for filename in os.listdir(folder):
        if filename.endswith(".md"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                body = extract_body(content)
                if body == new_content:
                    return True
    return False

# --- Determine Destination Folder Based on Duplicate Check ---
destination_folder = POSTS_FOLDER
if is_duplicate(final_output, POSTS_FOLDER):
    print("Duplicate content detected. Saving to redundant folder instead.")
    destination_folder = REDUNDANT_FOLDER

# --- Step 3: Create a Custom Title with a Spoiler ---
if summary:
    if '.' in summary:
        teaser = summary.split('.')[0].strip()
    else:
        teaser = summary[:60].strip()
    teaser = (teaser[:50] + '...') if len(teaser) > 50 else teaser
else:
    teaser = "No summary available"

custom_title = f"MTG News for {datetime.date.today().isoformat()} - {teaser}"

# --- Step 4: Save the Summary as a Markdown File ---
today_str = datetime.date.today().isoformat()
timestamp = datetime.datetime.now().strftime("%H%M%S")
filename = os.path.join(destination_folder, f"{today_str}-{timestamp}-mtg-news.md")

markdown_content = f"""---
title: "{custom_title}"
date: {today_str}
---

{final_output}
"""
