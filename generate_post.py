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

# Define folders for posts and for duplicates
POSTS_FOLDER = os.path.join("docs", "_posts")
REDUNDANT_FOLDER = os.path.join("docs", "redundant")
os.makedirs(POSTS_FOLDER, exist_ok=True)
os.makedirs(REDUNDANT_FOLDER, exist_ok=True)

# --- Step 1: Fetch Relevant News Articles from NewsAPI ---
# Refine the query so that you get articles that are truly about Magic: The Gathering tournaments/news.
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

# We'll process the first 3 articles (or fewer, if less than 3 are available)
articles_to_process = articles[:3]

# --- Helper Functions ---
def extract_body(markdown_text):
    """Extracts the body content from a Markdown file, ignoring YAML front matter."""
    parts = markdown_text.split("---")
    if len(parts) >= 3:
        return parts[2].strip()
    return markdown_text.strip()

def is_duplicate(new_content, folder):
    """Checks if new_content already exists in any Markdown file in the specified folder."""
    for filename in os.listdir(folder):
        if filename.endswith(".md"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                body = extract_body(content)
                if body == new_content:
                    return True
    return False

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

def create_custom_title(summary):
    """Extracts a teaser from the summary to create a custom title."""
    if summary:
        # Extract first sentence if possible; otherwise, use the first 60 characters.
        if '.' in summary:
            teaser = summary.split('.')[0].strip()
        else:
            teaser = summary[:60].strip()
        # Optionally truncate the teaser to 50 characters.
        teaser = (teaser[:50] + '...') if len(teaser) > 50 else teaser
    else:
        teaser = "No summary available"
    return f"MTG News for {datetime.date.today().isoformat()} - {teaser}"

# --- Process Each Article ---
for idx, article in enumerate(articles_to_process, start=1):
    print(f"\nProcessing article {idx}...")
    headline = article.get('title', 'No Title')
    article_content = article.get('description') or article.get('content') or headline
    source_name = article.get('source', {}).get('name', 'Unknown Source')
    article_url = article.get('url', 'No URL')
    
    # Construct a prompt to generate a concise summary in 3 sentences.
    prompt = (
        "Summarize the following Magic: The Gathering news article in 3 concise sentences. "
        "Focus on capturing the key points and avoid altering the main details. "
        "Do not include any URLs or external references in your summary. \n\n"
        "Headline: " + headline + "\n\n"
        "Article Content: " + article_content + "\n\n"
        "Summary:"
    )
    
    try:
        generated_text = generate_blog_post(prompt)
    except Exception as e:
        raise Exception(f"Failed to generate blog post for article {idx} after retries:", e)
    
    # Remove the prompt from the generated text if it is included.
    if generated_text.startswith(prompt):
        summary = generated_text[len(prompt):].strip()
    else:
        summary = generated_text
    
    # Append the original article URL and source at the end.
    final_output = f"{summary}\n\nSource: {source_name} ({article_url})"
    
    # Create a custom title with a teaser extracted from the summary.
    custom_title = create_custom_title(summary)
    
    # Determine destination folder based on duplicate check.
    destination_folder = POSTS_FOLDER
    if is_duplicate(final_output, POSTS_FOLDER):
        print("Duplicate content detected. Saving to redundant folder instead.")
        destination_folder = REDUNDANT_FOLDER
    
    # Save the post.
    today_str = datetime.date.today().isoformat()  # e.g., "2025-02-05"
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    filename = os.path.join(destination_folder, f"{today_str}-{timestamp}-mtg-news.md")
    
    markdown_content = f"""---
title: "{custom_title}"
date: {today_str}
---

{final_output}
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"Blog post for article {idx} generated: {filename}")
