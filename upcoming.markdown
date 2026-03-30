---
layout: default
title: Upcoming
permalink: /upcoming/
---

Next 10 releases transitioning to open-source licenses.

{% assign upcoming = site.data.upcoming | sort: "release_date" | slice: 0, 10 %}

{% for entry in upcoming %}
{% assign github_purl = entry.identifiers[0] %}
{% assign org_repo = github_purl | remove: "pkg:github/" | split: "@" | first %}
{% assign tag = github_purl | split: "@" | last %}
<article>
  <h3><a href="https://github.com/{{ org_repo }}/releases/tag/{{ tag }}">{{ org_repo }}</a><code>@{{tag}}</code> <span class="release-license">{{ entry.original_license }}</span></h3>
  <p><time datetime="{{ entry.release_date }}">{{ entry.release_date | date_to_long_string: "ordinal" }}</time></p>
  {% if entry.description %}<blockquote>{{ entry.description }}{% if entry.website %} — <a href="{{ entry.website }}">{{ entry.website | remove: "https://" | remove: "http://" | split: "/" | first }}</a>{% endif %}</blockquote>{% endif %}
  <p>{{ org_repo }} <code>{{ tag }}</code> transitions {{ entry.release_date | timeago }} from {{ entry.original_license }} to <strong>{{ entry.license }}</strong> after a {{ entry.delay_yrs }}-year delay. Source on <a href="https://github.com/{{ org_repo }}">GitHub</a>.</p>
  {% if entry.notes %}<p class="release-notes">{{ entry.notes }}</p>{% endif %}
</article>
{% endfor %}
