#!/usr/bin/env python3
"""Fetch GitHub releases for tracked projects and compute OSS transition status."""

import os
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import yaml
from packaging.version import Version, InvalidVersion

SOURCES_DIR = Path("_data/sources")
RELEASES_FILE = Path("_data/releases.yml")
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


def _try_parse(ver_str: str) -> Version | None:
    try:
        return Version(ver_str)
    except InvalidVersion:
        return None


def parse_version(tag: str) -> Version | None:
    """Extract a PEP 440 Version from a git tag.

    Accepted (no prefix):
      v1.2.3  1.2.3  v1246  20210728  190927A
      v1.2.3-rc1  1.2.3-beta.4  0.3.4-hotfix1

    Accepted (with prefix — version part must contain a dot):
      release/1.2.3  maxscale-23.02.1  self-hosted-24.2.1  trp-14v12p01

    Rejected:
      @scope/pkg@1.0.0          (npm scoped monorepo tags)
      untagged-abc123           (GitHub draft artifacts)
      flutter_sanity_text-v1.0  (underscore in prefix = sub-package)
      old-stable-website-2021   (prefix + no dot in version)
    """
    if tag.startswith(("untagged-", "@")):
        return None

    had_prefix = False

    # Try direct match (no prefix): v1.2.3, 1246, 190927A, 1.0.0-rc1
    m = re.fullmatch(r"[vV]?(\d[\d.a-zA-Z-]*)", tag)

    if not m:
        # Try with prefix (letters/digits/dashes, no underscores)
        m = re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]*[/-][vV]?(\d[\d.a-zA-Z-]*)", tag)
        had_prefix = True

    if not m:
        return None

    raw = m.group(1).lower()

    # Normalise pre-release markers to PEP 440
    raw = re.sub(r"[-.]?hotfix[-.]?(\d*)", r".post\1", raw)
    raw = re.sub(r"[-.]?beta[-.]?(\d*)", r"b\1", raw)
    raw = re.sub(r"[-.]?alpha[-.]?(\d*)", r"a\1", raw)
    # rc is already PEP 440 compatible

    version = _try_parse(raw)

    # Fallback: replace mid-version letter separators with dots (14v12p01 → 14.12.01)
    # Only for known separator letters (v=version, p=patch/point, r=release).
    if version is None and re.fullmatch(r"\d+(?:[vpr]\d+)+", raw):
        dotted = re.sub(r"(?<=\d)[vpr](?=\d)", ".", raw)
        version = _try_parse(dotted)
        raw = dotted

    if version is None:
        return None

    # When a prefix was stripped, require at least one dot in the version.
    # This prevents 'old-stable-website-20210728' from matching as version
    # 20210728 while still allowing bare tags like v1246 or 20210728.
    if had_prefix and "." not in raw:
        return None

    return version


def parse_gem_constraints(constraint_str: str) -> list[tuple[str, Version]]:
    """Convert a Gem::Requirement string into (op, Version) pairs.

    Supported operators: >=, <=, >, <, !=, =, ~>
    The ~> pessimistic operator is expanded:
      ~> X.Y   => >= X.Y, < (X+1).0
      ~> X.Y.Z => >= X.Y.Z, < X.(Y+1).0
    """
    result = []
    for part in constraint_str.split(","):
        part = part.strip()
        m = re.match(r"^(~>|>=|<=|!=|>|<|=)\s*(.+)$", part)
        if not m:
            continue
        op, ver_str = m.group(1), m.group(2).strip()

        if op == "~>":
            try:
                lower = Version(ver_str)
            except InvalidVersion:
                continue
            parts = ver_str.split(".")
            if len(parts) >= 2:
                # Increment second-to-last component and drop the last
                parts[-2] = str(int(parts[-2]) + 1)
                parts = parts[:-1]
                try:
                    upper = Version(".".join(parts))
                    result.append((">=", lower))
                    result.append(("<", upper))
                except InvalidVersion:
                    result.append((">=", lower))
            else:
                result.append((">=", lower))
        else:
            if op == "=":
                op = "=="
            try:
                result.append((op, Version(ver_str)))
            except InvalidVersion:
                continue

    return result


def version_matches(version: Version, constraint_str: str | None) -> bool:
    """Return True if version satisfies the constraint string (or if no constraint)."""
    if not constraint_str:
        return True

    constraints = parse_gem_constraints(constraint_str)
    if not constraints:
        return True

    ops = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    return all(ops[op](version, v) for op, v in constraints)


def fetch_all_tags(client: httpx.Client, owner: str, repo: str) -> list[dict]:
    """Page through git tags, returning dicts with 'name' and 'date' keys."""
    tags = []
    after = None

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
            print(f"  GraphQL errors: {data['errors']}", file=sys.stderr)
            break

        repo_data = (data.get("data") or {}).get("repository")
        if not repo_data:
            break

        page = repo_data["refs"]
        for edge in page["edges"]:
            node = edge["node"]
            target = node["target"]
            # Annotated tag → tagger.date; lightweight tag → committedDate
            tag_date = (
                (target.get("tagger") or {}).get("date")
                or target.get("committedDate")
            )
            if not tag_date:
                continue
            tags.append({"name": node["name"], "date": tag_date})

        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    return tags


def add_years(d: date, years: int) -> date:
    """Add years to a date, handling Feb 29 edge case."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def make_purls(owner: str, repo: str, tag: str, repo_url: str) -> list[str]:
    """Return [pkg:github PURL, pkg:generic PURL] for a release.

    pkg:github: namespace and name must be lowercased; version is the tag.
    pkg:generic: uses vcs_url qualifier per the PURL generic type spec, with
                 '+' encoded as %2B and '@' encoded as %40.
    """
    ns = owner.lower()
    nm = repo.lower()

    github_purl = f"pkg:github/{ns}/{nm}@{tag}"

    base = repo_url.rstrip("/").replace("http://", "https://")
    if not base.endswith(".git"):
        base += ".git"
    # Encode only the characters that are special within a qualifier value
    vcs_url_encoded = f"git%2B{base}%40{tag}"
    generic_purl = f"pkg:generic/{ns}/{nm}?vcs_url={vcs_url_encoded}"

    return [github_purl, generic_purl]


def highest_transitioned_tag(
    source: dict,
    owner: str,
    repo: str,
    repo_url: str,
    tags: list[dict],
    today: date,
) -> dict | None:
    """Return the highest-version transitioned tag for this source, or None."""
    ranges = source.get("ranges", [])
    best_version: Version | None = None
    best_tag_name: str = ""
    best_license: str = ""
    best_original_license: str = ""
    best_delay_yrs: int = 0
    best_notes: str = ""
    best_transition_date: date | None = None

    for tag_info in tags:
        tag_name = tag_info["name"]
        version = parse_version(tag_name)
        if version is None:
            continue

        tag_date = date.fromisoformat(tag_info["date"][:10])

        matched = None
        for r in ranges:
            if version_matches(version, r.get("versions")):
                matched = r
                break

        if matched is None:
            continue

        transition_date = add_years(tag_date, matched["delay_yrs"])
        if transition_date > today:
            continue

        if best_version is None or version > best_version:
            best_version = version
            best_tag_name = tag_name
            best_license = matched["oss_license"]
            best_original_license = matched["original_license"]
            best_delay_yrs = matched["delay_yrs"]
            best_notes = matched.get("notes", "")
            best_transition_date = transition_date

    if best_version is None:
        return None

    record: dict = {
        "identifiers": make_purls(owner, repo, best_tag_name, repo_url),
        "original_license": best_original_license,
        "license": best_license,
        "delay_yrs": best_delay_yrs,
        "release_date": str(best_transition_date),
    }
    if source.get("description"):
        record["description"] = source["description"]
    if source.get("website"):
        record["website"] = source["website"]
    if source.get("tags"):
        record["tags"] = source["tags"]
    if best_notes:
        record["notes"] = best_notes.strip()
    return record


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    sources = [
        yaml.safe_load(f.read_text())
        for f in sorted(SOURCES_DIR.glob("*.yml"))
    ]
    today = date.today()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    all_releases: list[dict] = []

    with httpx.Client(headers=headers, timeout=30) as client:
        for source in sources:
            repo_url = source.get("repo", "")
            m = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
            if not m:
                print(f"Skipping {source['name']}: cannot parse GitHub URL", file=sys.stderr)
                continue

            owner, repo = m.group(1), m.group(2)
            print(f"Fetching {owner}/{repo} ...", flush=True)

            try:
                tags = fetch_all_tags(client, owner, repo)
                record = highest_transitioned_tag(source, owner, repo, repo_url, tags, today)
                if record:
                    print(f"  {len(tags)} tags → {record['identifiers'][0]}")
                    all_releases.append(record)
                else:
                    print(f"  {len(tags)} tags → none transitioned yet")
            except httpx.HTTPStatusError as exc:
                print(f"  HTTP {exc.response.status_code}: {exc}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                print(f"  Error: {exc}", file=sys.stderr)

    all_releases.sort(key=lambda r: r["identifiers"][0])

    RELEASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    RELEASES_FILE.write_text(
        "# Auto-generated by src/main.py — do not edit by hand\n"
        + yaml.dump(all_releases, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    print(f"\nWrote {len(all_releases)} transitioned releases to {RELEASES_FILE}")


if __name__ == "__main__":
    main()
