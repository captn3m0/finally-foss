#!/usr/bin/env python3
"""List all tags for a GitHub repo as: tag,YYYY-MM-DD (one per line)."""

import os
import sys

import httpx

GITHUB_GRAPHQL = "https://api.github.com/graphql"

TAGS_QUERY = """
query($owner: String!, $repo: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    refs(refPrefix: "refs/tags/", first: 100, after: $after) {
      pageInfo {
        hasNextPage
        endCursor
      }
      edges {
        node {
          name
          target {
            ... on Tag {
              tagger { date }
            }
            ... on Commit {
              committedDate
            }
          }
        }
      }
    }
  }
}
"""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        print(f"Usage: {sys.argv[0]} owner/repo", file=sys.stderr)
        sys.exit(1)

    owner, repo = sys.argv[1].split("/", 1)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    after = None

    with httpx.Client(headers=headers, timeout=30) as client:
        while True:
            variables: dict = {"owner": owner, "repo": repo}
            if after:
                variables["after"] = after

            resp = client.post(
                GITHUB_GRAPHQL,
                json={"query": TAGS_QUERY, "variables": variables},
            )
            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
                break

            repo_data = (data.get("data") or {}).get("repository")
            if not repo_data:
                print("Repository not found", file=sys.stderr)
                break

            page = repo_data["refs"]
            for edge in page["edges"]:
                node = edge["node"]
                target = node["target"]
                tag_date = (
                    (target.get("tagger") or {}).get("date")
                    or target.get("committedDate")
                )
                tag_name = node["name"]
                dt = (tag_date or "")[:10]
                print(f"{tag_name},{dt}")

            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]


if __name__ == "__main__":
    main()
