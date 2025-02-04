---
layout: default
title: Home
---

# Welcome to MTG News!

This site automatically generates daily blog posts about Magic: The Gathering news.

## Latest Posts

<ul>
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      <small>{{ post.date | date: "%B %-d, %Y" }}</small>
    </li>
  {% endfor %}
</ul>
