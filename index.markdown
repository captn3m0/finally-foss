---
layout: default
permalink: /
---

{% assign releases = site.data.releases | sort: "release_date" | reverse %}

{% for entry in releases %}
{% assign github_purl = entry.identifiers[0] %}
{% assign org_repo = github_purl | remove: "pkg:github/" | split: "@" | first %}
{% assign tag = github_purl | split: "@" | last %}
<article>
  <h3><a href="https://github.com/{{ org_repo }}/releases/tag/{{ tag }}">{{ org_repo }}</a><code>@{{tag}}</code> <span class="release-license">{{ entry.license }}</span></h3>
  <p><time datetime="{{ entry.release_date }}">{{ entry.release_date | date_to_long_string: "ordinal" }}</time></p>
  {% if entry.description %}<blockquote>{{ entry.description }}{% if entry.website %} — <a href="{{ entry.website }}">{{ entry.website | remove: "https://" | remove: "http://" | split: "/" | first }}</a>{% endif %}</blockquote>{% endif %}
  <p>{{ org_repo }} <code>{{ tag }}</code> transitioned {{ entry.release_date | timeago }} from {{ entry.original_license }} to <strong>{{ entry.license }}</strong> after a {{ entry.delay_yrs }}-year delay. Source on <a href="https://github.com/{{ org_repo }}">GitHub</a>.</p>
  {% if entry.notes %}<p class="release-notes">{{ entry.notes }}</p>{% endif %}
  <details>
    <summary>Show Identifiers</summary>
    <ul>
      {% for purl in entry.identifiers %}
      <li><code>{{ purl }}</code></li>
      {% endfor %}
    </ul>
  </details>
</article>
{% endfor %}