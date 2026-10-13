# Archived documents

Prose that no longer describes how AnyJev currently works, kept because it explains a decision or a
version that someone may still need to look up. Nothing here is maintained. If a page here disagrees
with `docs/`, `docs/` wins.

**What does not belong here.** Result JSON and the per-run tables under `bench/results_*/` stay where
they are, whatever their age: `AGENTS.md` rule 1 says every number in prose names the JSON it came
from, so moving a run would strand the claims that cite it. `docs/research_log.md` also stays out
permanently — it is the record of what has been tried and closed, and its job is to stop work being
repeated on a dead end. A superseded *study* keeps its page in `docs/` with a header pointing at what
replaced it, because the page that replaced it cites it as its origin.

So a document lands here when all three hold: nothing in `README.md`, `ROADMAP.md`, `CHANGELOG.md` or
`docs/` links to it; it describes behaviour or a release that is no longer current; and it is not the
source of a number quoted anywhere. A document that is *internal* rather than merely old — work
assigned between people, notes on what to show publicly — does not belong in this folder either. It
belongs outside the repository.

## What is here

| file | what it was | why it is here |
|---|---|---|
| `release-notes-v0.0.2.md` | the release body published for 0.0.2, kept verbatim | superseded by `CHANGELOG.md`, which the file itself names as the record; nothing links to it |
