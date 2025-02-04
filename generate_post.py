import os
import requests
import openai
import datetime

# --- Configuration ---
NEWS_API_KEY = "90402f09ec9441a2bf43d6a9514f596a"        # Get from https://newsapi.org/
OPENAI_API_KEY = "org-Ep72tR5nXleYxu51SrCtWjWM"      # Get from https://platform.openai.com/
openai.api_key = OPENAI_API_KEY

# Folder to store blog posts (ensure this folder exists in your repo)
POSTS_FOLDER = "posts"

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

# Create a summary list of articles (title and URL)
article_summaries = "\n".join(
    [f"- {article['title']} ({article['url']})" for article in selected_articles]
)

# --- Step 2: Generate Blog Post with OpenAI ---
prompt = (
    f"Write a short, engaging blog post summarizing the latest Magic: The Gathering news. "
    f"Include an introduction, a brief summary of each news item, and a conclusion. "
    f"Here are the news headlines and links:\n\n{article_summaries}\n\n"
    f"Keep it concise and fun."
)

openai_response = openai.Completion.create(
    engine="text-davinci-003",
    prompt=prompt,
    max_tokens=300,
    temperature=0.7,
)

blog_text = openai_response.choices[0].text.strip()

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
