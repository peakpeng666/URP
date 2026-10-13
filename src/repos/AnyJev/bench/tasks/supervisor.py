"""The agent-supervisor scenario: the two decisions a router makes on every request.

A multi-agent system puts a classifier in front of N specialist agents. Today that
classifier is an LLM call per request whose free text has to be parsed back into an
agent name; it is the one responsibility in an agent system that is pure decision, so
taking it away from a generating model costs nothing.

Two questions, both on real assistant traffic:

- `massive_route`: which of 18 skills handles this utterance. MASSIVE is Amazon's
  virtual-assistant corpus and its `scenario` field is the skill, so the routing label
  is the dataset's own, not a grouping we invented.
- `clinc_escalate`: can the system handle this at all, or does it go to a human.
  CLINC150 ships 1,200 deliberately out-of-scope queries next to its 150 in-scope
  intents, which is exactly the escalation channel a supervisor needs.
"""
from __future__ import annotations

from anyjev.question import Question
from bench.tasks.base import Task, register

# MASSIVE's 18 scenario codes, in the dataset's own spelling, with the name a
# supervisor would show for the agent that owns them.
SKILLS = [
    ("alarm", "alarm"),
    ("audio", "audio and volume"),
    ("calendar", "calendar"),
    ("cooking", "cooking"),
    ("datetime", "date and time"),
    ("email", "email"),
    ("general", "general chit-chat"),
    ("iot", "smart home"),
    ("lists", "lists"),
    ("music", "music"),
    ("news", "news"),
    ("play", "play media"),
    ("qa", "question answering"),
    ("recommendation", "recommendations"),
    ("social", "social media"),
    ("takeaway", "food ordering"),
    ("transport", "transport"),
    ("weather", "weather"),
]

ROUTE_TEXT = ("A user message has arrived at a virtual assistant. Which specialist agent "
              "should handle it?")

# The same 18 skills with Chinese names, for the Chinese split of the same corpus. A Chinese
# request deserves Chinese option strings: an English option list on a Chinese state measures
# the model's translation, not its routing.
ESCALATE_TEXT = ("A user message has arrived at a task assistant that covers banking, credit "
                 "cards, travel, work, home, auto, dining, utilities, small talk and its own "
                 "settings. Can one of those agents handle this message?")


def route_question(skills=None) -> Question:
    """The routing question over `skills` (a list of (code, label) pairs; default all 18)."""
    return Question.choice(ROUTE_TEXT, [label for _, label in (skills or SKILLS)], name="route")


def _load_route(name: str, config: str, skills, text: str) -> Task:
    from datasets import load_dataset

    ds = load_dataset("mteb/amazon_massive_scenario", config)
    index = {code: i for i, (code, _) in enumerate(skills)}
    items = [(row["text"], index[row["label_text"]])
             for split in ("test", "validation", "train")
             for row in ds[split] if row["label_text"] in index]
    q = Question.choice(text, [label for _, label in skills], name="route")
    return Task(name, q, items, license="CC-BY-4.0",
                source="https://huggingface.co/datasets/mteb/amazon_massive_scenario",
                notes=f"18 skills, the dataset's own scenario field; {len(items)} utterances",
                meta={"skills": skills, "config": config})


@register("massive_route")
def load_route() -> Task:
    return _load_route("massive_route", "en", SKILLS, ROUTE_TEXT)



@register("clinc_escalate")
def load_escalate() -> Task:
    from datasets import load_dataset

    ds = load_dataset("clinc_oos", "plus")
    oos = ds["train"].features["intent"].names.index("oos")
    # option 0 = "Yes" (an agent can handle it) = in scope
    items = [(row["text"], 1 if int(row["intent"]) == oos else 0)
             for split in ("test", "validation", "train") for row in ds[split]]
    return Task("clinc_escalate", Question.noul(ESCALATE_TEXT, name="escalate"), items,
                license="CC-BY-3.0",
                source="https://huggingface.co/datasets/clinc_oos",
                notes=f"in-scope vs out-of-scope; {len(items)} queries")
