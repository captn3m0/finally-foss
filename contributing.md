---
layout: default
title: Contributing
permalink: /contributing/
---

## Contributing

Finally FOSS is open to contributions. The easiest way to help is by adding or updating tracked projects.

### Adding a new project

Create a new YAML file in `_data/sources/` named `org-repo.yml` (e.g. `hashicorp-terraform.yml`) with the following structure:

```yaml
name: org/repo
repo: https://github.com/org/repo
stars: 1000
ranges:
  - versions: ">= 1.0"
    original_license: BUSL-1.1
    oss_license: Apache-2.0
    delay_yrs: 4
    notes: "Optional context about the licensing."
```

**Fields:**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | `org/repo` identifier |
| `repo` | Yes | GitHub repository URL |
| `stars` | No | Approximate star count |
| `ranges[]` | Yes | One or more licensing windows |
| `ranges[].versions` | No | [Gem::Requirement](https://ruby-doc.org/stdlib/libdoc/rubygems/rdoc/Gem/Requirement.html)-style constraint (e.g. `">= 1.0, < 3.0"`). Omit to match all versions. |
| `ranges[].original_license` | Yes | SPDX identifier of the source-available license |
| `ranges[].oss_license` | Yes | SPDX identifier of the target open-source license |
| `ranges[].delay_yrs` | Yes | Years until conversion |
| `ranges[].notes` | No | Additional context |

### Version constraints

Version constraints follow Gem::Requirement syntax:

- `">= 1.0"` -- at or above 1.0
- `">= 1.0, < 3.0"` -- range
- `"~> 2.0"` -- pessimistic (>= 2.0, < 3.0)

If a project changed its license terms at different versions, add multiple ranges:

```yaml
ranges:
  - versions: ">= 10.0.0, < 23.11.0"
    original_license: BUSL-1.1
    oss_license: Apache-2.0
    delay_yrs: 3
  - versions: ">= 23.11.0"
    original_license: FSL-1.1-ALv2
    oss_license: Apache-2.0
    delay_yrs: 2
```

### Running locally

```bash
# Install Python dependencies
uv sync

# Fetch releases (requires GITHUB_TOKEN)
export GITHUB_TOKEN=ghp_...
uv run python src/main.py


# Build the Jekyll site
bundle exec jekyll serve -w

# This is a debug command
# List all tags for a specific repo
uv run python src/all-releases.py org/repo
```

### Guidelines

- One project per file in `_data/sources/`
- Use SPDX license identifiers
- Add notes for anything non-obvious (forks, revenue thresholds, proprietary reversions)
