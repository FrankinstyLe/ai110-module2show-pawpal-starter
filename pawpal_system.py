"""PawPal system classes.

Generated from diagrams/uml.mmd. Data-only objects (Pet, Task) use
dataclasses; classes with behavior (Owner, Scheduler) are regular classes.

Object model
------------
- Task        : a single pet-care activity (what, how long, how urgent) plus
                its completion status. Every task belongs to one Pet.
- Pet         : pet details and the list of tasks that belong to it.
- Owner       : manages many pets and exposes access to all of their tasks,
                plus the owner's availability and scheduling preferences.
- Scheduler   : the "brain" that reads tasks/availability/preferences and lays
                them out into a concrete plan of ScheduledTasks.
"""

import itertools
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

# Process-unique id sources for Task and Pet, so a UI (e.g. Streamlit) can key
# widgets on a stable identifier rather than id(), which Python recycles for
# freed objects (a recycled id lets a new object inherit stale widget state).
_task_ids = itertools.count(1)
_pet_ids = itertools.count(1)

# Recurrence values a Task understands. A recurring task spawns its next
# pending occurrence when it is completed (see Task.markComplete).
RECURRENCES = ("daily", "weekly")

# How many days forward each recurrence advances a dated task's dueDate when it
# spawns its next occurrence (see Task._spawnNextOccurrence).
RECURRENCE_DAYS = {"daily": 1, "weekly": 7}

# Sensible defaults for when each task type is typically best scheduled. Used
# by the Scheduler to bias a task toward a matching time-of-day window (see
# generatePlan). A type that is absent is treated as flexible (any time). These
# are heuristics an owner could reasonably tweak.
TASK_TIME_OF_DAY = {
    "feeding": "morning",
    "walk": "evening",
    "medication": "afternoon",
    "grooming": "afternoon",
    "enrichment": "afternoon",
}

# Chronological rank of each time-of-day bucket. Used to break scheduling ties
# by *time* after preference and priority (see Scheduler.generatePlan); flexible
# tasks (no bucket) sort after the fixed ones.
BUCKET_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}


@dataclass
class Pet:
    petName: str
    breed: str
    petAge: int
    specialNote: str
    # Species/kind of animal (e.g. "Dog", "Cat", "Bird"). Defaulted so existing
    # keyword constructions that predate this field keep working.
    petType: str = "Dog"
    # UML: Pet "1" --> "*" Task. Kept out of eq/repr so the Task<->Pet
    # back-reference below cannot cause infinite recursion.
    tasks: list["Task"] = field(default_factory=list, compare=False, repr=False)
    # Process-unique identity for stable UI keys; compare/repr excluded so it
    # never affects Pet equality.
    uid: int = field(
        default_factory=lambda: next(_pet_ids), compare=False, repr=False
    )

    def addTask(self, task: "Task") -> None:
        """Attach a task to this pet (no-op if already attached)."""
        if task not in self.tasks:
            self.tasks.append(task)


@dataclass
class Task:
    taskType: str
    priority: int
    duration: int
    taskNote: str
    # UML: Pet "1" --> "*" Task — every task belongs to a pet. Excluded from
    # eq/repr to break the Pet<->Task reference cycle.
    pet: Pet = field(compare=False, repr=False)
    completed: bool = False
    # "" / None means one-off; "daily" or "weekly" makes the task recurring, so
    # completing it queues up the next occurrence (see markComplete).
    recurrence: str | None = None
    # Optional calendar date this occurrence is due. When set on a recurring
    # task, completing it advances the spawned copy to the next cycle's date
    # (daily -> +1 day, weekly -> +7). None means the task carries no date, in
    # which case the next occurrence is simply an undated pending copy.
    dueDate: date | None = None
    # Process-unique identity for stable UI keys. compare/repr excluded so it
    # never affects Task equality or the de-dup logic in Owner/Pet.
    uid: int = field(
        default_factory=lambda: next(_task_ids), compare=False, repr=False
    )
    # For a *combined* task produced by mergeSameActivities: the real per-pet
    # tasks it stands in for, so completing the combined schedule entry can
    # complete (and respawn) each underlying task. Empty for ordinary tasks.
    # Excluded from eq/repr like the other bookkeeping fields.
    mergedFrom: "list[Task]" = field(
        default_factory=list, compare=False, repr=False
    )

    def isRecurring(self) -> bool:
        """True if this task repeats (a recognized recurrence was set)."""
        return (self.recurrence or "").strip().lower() in RECURRENCES

    def markComplete(self) -> "Task | None":
        """Mark this task as done.

        If the task is recurring, a fresh pending copy for the next occurrence
        is created and attached to the same pet, then returned. Completing an
        already-completed task is a no-op and never double-spawns.
        """
        if self.completed:
            return None
        self.completed = True
        if self.isRecurring():
            return self._spawnNextOccurrence()
        return None

    def reopen(self) -> None:
        """Mark this task as not yet done."""
        self.completed = False

    def _spawnNextOccurrence(self) -> "Task":
        """Create the next pending copy of this recurring task.

        The copy keeps every attribute (type, priority, duration, note, pet,
        recurrence) but starts not-completed, and is attached to the pet so the
        owner picks it up via getAllTasks()/pendingTasks(). If this task has a
        dueDate, the copy's dueDate is advanced to the next cycle (daily -> the
        following day, weekly -> +7 days); an undated task stays undated.
        """
        nextDue = self.dueDate
        if nextDue is not None:
            step = RECURRENCE_DAYS.get((self.recurrence or "").strip().lower(), 0)
            nextDue = nextDue + timedelta(days=step)
        # Fresh uid so the new occurrence is a distinct identity from its
        # completed parent (otherwise UI widget keys would collide).
        nextTask = replace(
            self, completed=False, dueDate=nextDue, uid=next(_task_ids)
        )
        if self.pet is not None:
            self.pet.addTask(nextTask)
        return nextTask


@dataclass
class Owner:
    ownerName: str
    availability: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def addPet(self, pet: Pet) -> None:
        """Add a pet to this owner (no-op if already added)."""
        if pet not in self.pets:
            self.pets.append(pet)

    def addTask(self, task: Task) -> None:
        """Register a task with this owner and with its pet.

        Keeps the owner's flat task list and the pet's task list in sync so
        the Scheduler can read tasks from either side.
        """
        if task not in self.tasks:
            self.tasks.append(task)
        if task.pet is not None:
            self.addPet(task.pet)
            task.pet.addTask(task)

    def addTime(self, slot: str) -> None:
        """Add an availability time slot (no-op if already present)."""
        if slot not in self.availability:
            self.availability.append(slot)

    def addPreferences(self, preference: str) -> None:
        """Add a scheduling preference (no-op if already present)."""
        if preference not in self.preferences:
            self.preferences.append(preference)

    def getAllTasks(self) -> list[Task]:
        """Return every task across all of this owner's pets.

        Aggregated from the pets so the result reflects the true owner ->
        pet -> task hierarchy, de-duplicated while preserving order.

        De-dup is by identity (uid), not value equality: the goal is only to
        avoid listing the *same* task twice (a task can appear both on its pet
        and in the owner's flat list). Two different pets can legitimately have
        value-identical tasks (e.g. both need a 20-min walk) -- Task equality
        excludes `pet`, so a value-based de-dup would wrongly collapse them and
        drop one pet's task from the schedule entirely.
        """
        seen: list[Task] = []
        seen_uids: set[int] = set()
        for source in (*(pet.tasks for pet in self.pets), self.tasks):
            for task in source:
                if task.uid not in seen_uids:
                    seen_uids.add(task.uid)
                    seen.append(task)
        return seen

    def pendingTasks(self) -> list[Task]:
        """Return all outstanding (not completed) tasks across pets."""
        return [task for task in self.getAllTasks() if not task.completed]

    def pendingTasksDueBy(self, when: date) -> list[Task]:
        """Pending tasks due on or before ``when``.

        A task with no dueDate is treated as always due (it carries no calendar
        constraint). A recurring occurrence spawned for a future date therefore
        stays out of an earlier day's list instead of piling onto "today" -- so
        completing today's walk doesn't immediately re-list tomorrow's.
        """
        return [
            task
            for task in self.pendingTasks()
            if task.dueDate is None or task.dueDate <= when
        ]


def mergeKey(task: Task) -> str:
    """Stable id for a mergeable activity: same type AND same duration.

    Duration is part of the key on purpose, so a 20-minute walk never folds
    into a 45-minute walk -- only genuinely identical activities combine.
    """
    return f"{task.taskType.strip().lower()}|{task.duration}"


def _distinctPets(tasks: list[Task]) -> list[Pet]:
    """The distinct pets (by identity, order-preserving) a group touches."""
    pets: list[Pet] = []
    for task in tasks:
        if task.pet is not None and all(task.pet is not p for p in pets):
            pets.append(task.pet)
    return pets


def findMergeableActivities(tasks: list[Task]) -> list[dict]:
    """List the activities the owner *could* combine, for the UI to offer.

    A candidate is an activity type + duration that two or more *distinct* pets
    share (e.g. a 20-min walk for both Rex and Milo). Returns one dict per
    candidate group, in first-appearance order, with:

    - ``"key"``   -- stable id to pass back in ``selectedKeys`` (see mergeSameActivities),
    - ``"taskType"`` -- display label (original casing of the first task),
    - ``"duration"`` -- the shared duration in minutes,
    - ``"pets"``  -- participating pet names, in order.

    Groups tied to a single pet are not candidates and are omitted.
    """
    groups: dict[str, list[Task]] = {}
    order: list[str] = []
    for task in tasks:
        key = mergeKey(task)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(task)

    candidates: list[dict] = []
    for key in order:
        group = groups[key]
        pets = _distinctPets(group)
        if len(pets) >= 2:
            candidates.append(
                {
                    "key": key,
                    "taskType": group[0].taskType,
                    "duration": group[0].duration,
                    "pets": [pet.petName or "Unnamed pet" for pet in pets],
                }
            )
    return candidates


def mergeSameActivities(
    tasks: list[Task], selectedKeys: "set[str] | None" = None
) -> list[Task]:
    """Collapse *chosen* same-activity groups into one combined task each.

    An activity is mergeable when the same type AND the same duration are shared
    by two or more distinct pets (see mergeKey), so the owner can do it once for
    several pets -- e.g. walk all the dogs together. Only groups whose key is in
    ``selectedKeys`` are combined; every other task passes through unchanged.
    ``selectedKeys=None`` combines every eligible group (convenience for callers
    that want them all); pass an empty set to merge nothing.

    For a combined task:

    - **duration** is the shared duration (identical across the group by
      definition -- doing them together takes that long, not the sum);
    - **priority** is the MOST urgent (lowest number) in the group;
    - the **pet** is a display-only aggregate whose name lists every
      participant ("Rex & Milo"); the real per-pet tasks are left untouched so
      completion and recurrence keep tracking per pet;
    - **recurrence** is preserved only if the whole group agrees, else dropped.

    This is a scheduling-time transform: it neither mutates nor replaces the
    tasks stored on the pets, so the choice is made per plan.
    """
    groups: dict[str, list[Task]] = {}
    order: list[str] = []
    for task in tasks:
        key = mergeKey(task)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(task)

    merged: list[Task] = []
    for key in order:
        group = groups[key]
        pets = _distinctPets(group)
        chosen = selectedKeys is None or key in selectedKeys
        if len(pets) <= 1 or not chosen:
            merged.extend(group)  # nothing to combine, or the owner said no
            continue

        names = " & ".join(pet.petName or "Unnamed pet" for pet in pets)
        recurrences = {task.recurrence for task in group}
        merged.append(
            Task(
                taskType=group[0].taskType,
                priority=min(task.priority for task in group),
                duration=group[0].duration,  # shared across the group by key
                taskNote=f"Combined for {len(pets)} pets: {names}",
                pet=Pet(petName=names, breed="", petAge=0, specialNote=""),
                recurrence=recurrences.pop() if len(recurrences) == 1 else None,
                # Remember the real per-pet tasks so completing this combined
                # entry can complete (and respawn) each of them.
                mergedFrom=list(group),
            )
        )
    return merged


@dataclass
class ScheduledTask:
    scheduleTime: str
    task: Task
    reason: str
    # The availability slot this task was packed into (the window's label).
    # Tasks sharing a slot run back-to-back; used by Scheduler.detectConflicts.
    slot: str = ""


@dataclass
class _Window:
    """One availability slot expressed as a real time window.

    `start`/`end` are minutes since midnight; `clock` is a moving cursor that
    advances as tasks are packed in, so back-to-back tasks get successive
    start times instead of all sharing the slot's label.
    """

    start: int
    end: int
    bucket: str
    clock: int


@dataclass
class Scheduler:
    scheduleDate: str
    plannedTasks: list[ScheduledTask] = field(default_factory=list)

    def generatePlan(
        self,
        tasks: list[Task],
        availability: "list[str | tuple[str, str]]",
        preferences: list[str],
        defaultSlotMinutes: int = 60,
    ) -> list[Task]:
        """Build a plan by packing tasks into time-aware availability windows.

        Ordering rules (highest to lowest influence) decide *which* task is
        placed first:
          1. Tasks whose taskType matches an owner preference go first.
          2. Then by priority, treating a *lower* number as more urgent.
          3. Then by time of day (morning -> afternoon -> evening), so ties
             break toward earlier routines. Duration is *not* an ordering
             factor — it only decides whether a task fits a slot.

        Placement rules decide *where* each task lands:
          - Availability entries are parsed into real time windows and sorted,
            so the earliest usable window is genuinely the earliest time of day
            (#3: real ordering). An entry may be an explicit ``(start, end)``
            range or a single label whose end is inferred from the next slot.
          - Each window has a capacity in minutes (its end minus its start, or
            the gap to the next slot for a bare label). Multiple short tasks pack
            into one window until the next task's duration no longer fits; a
            task too long for any remaining window is returned as unplaced
            (#1: duration-aware packing and overbooking detection).
          - A task prefers a window whose time-of-day matches its type (e.g. a
            walk seeks an evening slot even when a morning slot is free); it
            falls back to the earliest window with room if none match
            (#4: time-of-day fit). Types absent from TASK_TIME_OF_DAY are
            flexible and take the earliest window with room.

        The finished plan is sorted chronologically by start time, so the
        schedule always reads top-to-bottom in real clock order regardless of
        the order tasks were placed. Completed tasks are skipped. Remaining
        tasks that find no window are returned so the caller can surface the
        conflict.
        """
        preferred = {pref.strip().lower() for pref in preferences}
        windows = self._buildWindows(availability, defaultSlotMinutes)

        def sort_key(task: Task):
            """Rank a task by preference, then priority, then time of day."""
            is_preferred = task.taskType.strip().lower() in preferred
            tod = TASK_TIME_OF_DAY.get(task.taskType.strip().lower())
            # preference (0 before 1) > priority (lower = more urgent) > time of
            # day (earlier bucket first; flexible tasks last). Duration is left
            # out on purpose — it is a fit constraint, not an ordering factor.
            return (
                0 if is_preferred else 1,
                task.priority,
                BUCKET_ORDER.get(tod or "", len(BUCKET_ORDER)),
            )

        # Filter completed tasks here even though callers like Owner.pendingTasks
        # already do to keep generatePlan correct for any task list it is handed
        pending = sorted(
            (task for task in tasks if not task.completed), key=sort_key
        )

        unplaced: list[Task] = []
        for task in pending:
            window = self._findWindow(task, windows)
            if window is None:
                unplaced.append(task)
                continue
            start = window.clock
            window.clock += task.duration
            scheduleTime = self._formatTime(start)
            self.assignTask(
                task,
                scheduleTime,
                self._explain(task, preferred, window, scheduleTime),
                slot=self._formatTime(window.start),
            )

        # Item #2: present the plan in real clock order, not placement order (a
        # preferred evening task can be *placed* before a morning one).
        self.plannedTasks.sort(key=lambda s: self._parseTime(s.scheduleTime) or 0)
        return unplaced

    def assignTask(
        self, task: Task, scheduleTime: str, reason: str, slot: str = ""
    ) -> None:
        """Place a single task at a time and record why (appends a ScheduledTask).

        `slot` is the label of the availability window the task landed in, so
        detectConflicts can spot several tasks sharing one slot.
        """
        self.plannedTasks.append(
            ScheduledTask(
                scheduleTime=scheduleTime, task=task, reason=reason, slot=slot
            )
        )

    def detectConflicts(self) -> list[str]:
        """Return soft-conflict warnings about the current plan; never raises.

        The plan runs on a single timeline (the owner can't be two places at
        once), so tasks are packed back-to-back rather than stacked. When more
        than one task lands in the same availability slot, that slot is doing
        double duty — worth flagging so the owner can rebalance. Returns an
        empty list when there is nothing to warn about.
        """
        by_slot: dict[str, list[ScheduledTask]] = {}
        for scheduled in self.plannedTasks:
            by_slot.setdefault(scheduled.slot, []).append(scheduled)

        warnings: list[str] = []
        for slot, items in by_slot.items():
            if len(items) > 1:
                names = ", ".join(
                    f"{s.task.pet.petName}'s {s.task.taskType}" for s in items
                )
                warnings.append(
                    f"{len(items)} tasks share your {slot} slot and will run "
                    f"back-to-back: {names}."
                )
        return warnings

    def _buildWindows(
        self, availability: "list[str | tuple[str, str]]", defaultSlotMinutes: int
    ) -> list["_Window"]:
        """Turn availability entries into chronologically sorted time windows.

        Each entry is either an explicit ``(start, end)`` range or a single
        label. For a range the capacity is ``end - start``; for a lone label the
        end is inferred as the gap to the next slot (or `defaultSlotMinutes` for
        the last one). Windows may be non-consecutive. Unparseable starts fall
        back to a running cursor so they still form windows in the order given.
        """
        cursor = 8 * 60  # 8:00 AM anchor for entries we cannot parse.
        entries: list[tuple[int, int | None]] = []
        for item in availability:
            start, end = self._parseSlot(item)
            if start is None:
                start = cursor
            cursor = (end if end is not None else start) + defaultSlotMinutes
            entries.append((start, end))

        entries.sort(key=lambda pair: pair[0])
        windows: list[_Window] = []
        for index, (start, end) in enumerate(entries):
            if end is None:
                if index + 1 < len(entries):
                    end = entries[index + 1][0]
                else:
                    end = start + defaultSlotMinutes
            if end <= start:  # guard against zero-length / inverted windows
                end = start + defaultSlotMinutes
            windows.append(
                _Window(start=start, end=end, bucket=self._bucket(start), clock=start)
            )
        return windows

    @staticmethod
    def _parseSlot(item: object) -> "tuple[int | None, int | None]":
        """Normalize one availability entry to ``(start, end)`` minutes.

        Accepts a ``(start, end)`` pair, a ``"start - end"`` range string, or a
        single label (end is None, meaning "infer from the next slot").
        """
        if isinstance(item, (tuple, list)) and len(item) == 2:
            return Scheduler._parseTime(str(item[0])), Scheduler._parseTime(str(item[1]))
        if isinstance(item, str) and "-" in item:
            left, _, right = item.partition("-")
            start = Scheduler._parseTime(left)
            end = Scheduler._parseTime(right)
            if start is not None and end is not None:
                return start, end
        return Scheduler._parseTime(str(item)), None

    def _findWindow(self, task: Task, windows: list["_Window"]) -> "_Window | None":
        """Pick the best window for a task, or None if it fits nowhere.

        Windows are sorted earliest-first, so `[0]` is always the earliest
        candidate. A task prefers a time-of-day match; otherwise it takes the
        earliest window that still has room for its duration.
        """
        tod = TASK_TIME_OF_DAY.get(task.taskType.strip().lower())

        def fits(window: "_Window") -> bool:
            """True if the window has enough remaining minutes for this task."""
            return (window.end - window.clock) >= task.duration

        matching = [
            window
            for window in windows
            if (tod is None or window.bucket == tod) and fits(window)
        ]
        if matching:
            return matching[0]
        fallback = [window for window in windows if fits(window)]
        return fallback[0] if fallback else None

    @staticmethod
    def _parseTime(label: str) -> "int | None":
        """Parse a label to minutes since midnight, or None if unrecognized.

        Accepts clock times ("8:00 AM", "8 PM", "14:30") and named buckets
        ("Morning", "Afternoon", "Evening", "Night").
        """
        text = label.strip().lower()
        keywords = {
            "morning": 8 * 60,
            "afternoon": 13 * 60,
            "evening": 18 * 60,
            "night": 20 * 60,
        }
        if text in keywords:
            return keywords[text]
        for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
            try:
                parsed = datetime.strptime(label.strip(), fmt)
                return parsed.hour * 60 + parsed.minute
            except ValueError:
                continue
        return None

    @staticmethod
    def _formatTime(minutes: int) -> str:
        """Format minutes-since-midnight as a 12-hour label, e.g. '8:10 AM'."""
        minutes %= 24 * 60
        hour24, minute = divmod(minutes, 60)
        suffix = "AM" if hour24 < 12 else "PM"
        hour12 = hour24 % 12 or 12
        return f"{hour12}:{minute:02d} {suffix}"

    @staticmethod
    def _bucket(minutes: int) -> str:
        """Classify a time into a coarse time-of-day bucket."""
        if minutes < 12 * 60:
            return "morning"
        if minutes < 17 * 60:
            return "afternoon"
        return "evening"

    @staticmethod
    def _explain(
        task: Task, preferred: set[str], window: "_Window", scheduleTime: str
    ) -> str:
        """A full 'why + when' sentence for a placed task.

        States when/where it lands (time and time-of-day window) and why it was
        chosen and ordered there: owner preference, priority, and how its type's
        usual time of day matched (or didn't match) the window it took.
        """
        reasons: list[str] = []
        if task.taskType.strip().lower() in preferred:
            reasons.append("it matches an owner preference")

        # Name the urgency for the common levels; a lower number is more urgent.
        urgency = {1: "high", 2: "medium", 3: "low"}.get(task.priority)
        reasons.append(
            f"it's {urgency}-priority (level {task.priority})"
            if urgency
            else f"it's priority {task.priority}"
        )

        tod = TASK_TIME_OF_DAY.get(task.taskType.strip().lower())
        if tod is None:
            reasons.append("it's flexible, so it took the earliest window with room")
        elif tod == window.bucket:
            reasons.append(f"the {window.bucket} suits its usual routine")
        else:
            reasons.append(
                f"its usual {tod} was full, so it took the earliest window with room"
            )

        why = "; ".join(reasons)
        return (
            f"Scheduled at {scheduleTime} in your {window.bucket} window "
            f"({task.duration} min for {task.pet.petName}) because {why}."
        )
