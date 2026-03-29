---
layout: default
title: About Finally FOSS
permalink: /about/
---

## What?

We track source-available software as it transitions to open-source licenses.

Many projects use delayed open-source release strategies: they publish code
under a source-available license that
automatically converts to a recognized open-source license after a set
period. The most popular examples are 
[Business Source License](https://en.wikipedia.org/wiki/Business_Source_License),
[Functional Source License](https://fsl.software/), and the
[Fair Core License](https://fcl.dev/).

This site monitors those transitions and publishes a feed of releases that have crossed the threshold into open source.

### Why?

The [Fair Source Definition](https://fair.io/about/) explains why the believe in Delayed Open Source publication:

> The third point is also intended as a bright line, and a key differentiator
  of Fair Source from Open Core and other approaches. Delayed Open Source
  publication (DOSP) is a concept established by the Open Source Initiative
  (OSI). It is in keeping with OSI's public-benefit mandate to "persuade
  organizations and software authors to distribute source software freely
  they otherwise would not distribute." DOSP ensures that if a Fair Source
  company goes out of business, or develops its products in an undesired
  direction, the community or another company can pick up and move forward.
  Will this be meaningful in practice? Again, time will tell. 

This project is a way to collect data towards answering that question.

### Licenses we track

- **BUSL-1.1** Business Source License
- **FSL-1.1** Functional Source License
- **FCL-1.0** Fair Core License
- **BSL-1.0** the original Business Source License

Other licenses are welcome as well, see below.

### How it works

1. Each tracked project has a source definition in [`_data/sources/`](https://github.com/captn3m0/finally-foss/tree/main/_data/sources) specifying its license ranges and delay periods.
2. A daily GitHub Actions workflow fetches all git tags from each project via the GitHub GraphQL API.
3. Tags are matched against the version constraints and checked for whether the delay period has elapsed.
4. The highest fully-transitioned version for each project is written to `_data/releases.yml` with [PURL](https://github.com/package-url/purl-spec) identifiers.
5. Jekyll builds this site and the Atom feed from that data.

THis currently only support GitHub, but only because I couldn't find any relevant software that wasn't on GitHub.

### Identifiers

Each release is published with two [Package URL](https://github.com/package-url/purl-spec) identifiers:

- `pkg:github/owner/repo@tag` -- GitHub-type PURL
- `pkg:generic/owner/repo?vcs_url=...` -- Generic PURL with VCS URL qualifier

### Links

- [Atom Feed](/atom.xml)
- [GitHub Repository](https://github.com/captn3m0/finally-foss)