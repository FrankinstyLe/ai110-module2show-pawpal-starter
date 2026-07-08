# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```text
Tasks as added (insertion order, unsorted):
  - Rex: walk (priority 2, pending)
  - Milo: medication (priority 1, pending)
  - Rex: grooming (priority 1, done)
  - Rex: feeding (priority 1, pending)
  - Milo: feeding (priority 1, pending)

Filtering (pendingTasks): 5 total -> 4 pending; 1 completed task(s) skipped.

Today's Schedule (2026-07-07) for Alex
================================================
  8:00 AM  Rex: feeding (10 min)
           - Morning kibble
           - why: matches an owner preference; priority 1; 10 min for Rex; scheduled in the morning to fit its routine
  8:10 AM  Milo: feeding (10 min)
           - Morning wet food
           - why: matches an owner preference; priority 1; 10 min for Milo; scheduled in the morning to fit its routine
 12:30 PM  Milo: medication (5 min)
           - Give with lunch
           - why: priority 1; 5 min for Milo; scheduled in the afternoon to fit its routine
  6:00 PM  Rex: walk (30 min)
           - Neighborhood loop
           - why: priority 2; 30 min for Rex; scheduled in the evening to fit its routine

(Note: 'walk' was added first but scheduled last, and the completed 'grooming' task is absent.)

[!] Schedule warnings:
  - 2 tasks share your 8:00 AM slot and will run back-to-back: Rex's feeding, Milo's feeding.
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov

# Run a single test file:
pytest tests/test_pawpal.py
```

### Brief description of what the tests cover:
* Task & recurrence basics

  * markComplete flips status; addTask grows a pet's task list
  * Daily task spawns a next occurrence; one-off tasks don't; completing twice never double-spawns
  * Dated recurrence: daily → next day, weekly → +7 days, undated stays undated
  * Casing/whitespace recurrence still recurs; unrecognized value ("monthly") treated as one-off; reopen() un-completes

* Scheduling / packing

  * Short tasks pack back-to-back with computed times; a too-long task is unplaced
  * Explicit (start, end) windows and "start - end" strings cap capacity; non-consecutive windows both usable
  * Exact-fit task (duration == window) fits (inclusive boundary)

* Sorting

  * Chronological output across three windows even from scrambled input
  * Availability ordered by real time; preferred task placed first still displays in clock order
  * Preference outranks priority; all-equal keys preserve insertion order

* Conflict detection

  * Shared slot → one warning naming the slot + tasks; separate slots → no warning

* Edge cases / documented behavior

  * Empty task list → empty plan; no availability → everything unplaced; task-less pet contributes nothing
  * Unparseable availability label falls back to the 8:00 AM cursor
  * Identical-field tasks on different pets compare equal and collapse in owner aggregation (pinned as a known sharp edge)

### Sample test output:

```text
============================================================= test session starts ==============================================================
platform win32 -- Python 3.13.1, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Frankinstyle\CodePath\AI110\Project 2\ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 30 items                                                                                                                              

tests\test_pawpal.py ..............................                                                                                       [100%]

============================================================== 30 passed in 0.09s ==============================================================
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.generatePlan` (`sort_key`), then `plannedTasks.sort()` | places by preference > priority > time-of-day, then re-sorts the finished plan into chronological order |
| Filtering | `Owner.pendingTasks`, `Owner.getAllTasks`, `Scheduler._findWindow` | skip completed tasks; aggregate/scope by pet; drop tasks that fit no slot (returned as unplaced) |
| Conflict handling | `Scheduler.detectConflicts`, `Scheduler._buildWindows` | warns (never raises) when tasks share a slot; window capacity flags overbooking |
| Recurring tasks | `Task.markComplete`, `Task._spawnNextOccurrence` | completing a `daily`/`weekly` task auto-queues its next pending occurrence on the pet |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
