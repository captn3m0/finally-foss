#!/usr/bin/env python3
"""One-off script: add repo description, topics, and homepage from GitHub, remove stars."""

import os
import sys
from pathlib import Path

import httpx
import yaml

SOURCES_DIR = Path("_data/sources")
GITHUB_GRAPHQL = "https://api.github.com/graphql"

REPO_QUERY = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    description
    homepageUrl
    repositoryTopics(first: 20) {
      nodes {
        topic { name }
      }
    }
  }
}
"""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN required", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    files = sorted(SOURCES_DIR.glob("*.yml"))
    print(f"Found {len(files)} source files")

    with httpx.Client(headers=headers, timeout=30) as client:
        for path in files:
            data = yaml.safe_load(path.read_text())
            name = data["name"]
            parts = name.split("/")
            if len(parts) != 2:
                print(f"  SKIP {name}: not owner/repo")
                continue

            owner, repo = parts
            print(f"  {name} ...", end=" ", flush=True)

            resp = client.post(
                GITHUB_GRAPHQL,
                json={"query": REPO_QUERY, "variables": {"owner": owner, "repo": repo}},
            )
            resp.raise_for_status()
            result = resp.json()

            repo_data = (result.get("data") or {}).get("repository")
            if not repo_data:
                print("not found")
                continue

            description = (repo_data.get("description") or "").strip()
            topics = [
                n["topic"]["name"]
                for n in repo_data.get("repositoryTopics", {}).get("nodes", [])
            ]

            # Remove stars
            data.pop("stars", None)

            homepage = (repo_data.get("homepageUrl") or "").strip()

            # Add description, homepage, and tags
            if description:
                data["description"] = description
            if homepage:
                data["website"] = homepage
            if topics:
                data["tags"] = topics

            # Rebuild with desired key order
            ordered: dict = {}
            for key in ("name", "repo", "website", "description", "tags", "ranges"):
                if key in data:
                    ordered[key] = data[key]
            # Preserve any other keys
            for key in data:
                if key not in ordered:
                    ordered[key] = data[key]

            path.write_text(
                yaml.dump(ordered, default_flow_style=False, sort_keys=False, allow_unicode=True)
            )
            print(f"ok ({len(topics)} tags)")

    print("Done")


if __name__ == "__main__":
    main()
