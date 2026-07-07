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

from dataclasses import dataclass, field


@dataclass
class Pet:
    petName: str
    breed: str
    petAge: int
    specialNote: str
    # UML: Pet "1" --> "*" Task. Kept out of eq/repr so the Task<->Pet
    # back-reference below cannot cause infinite recursion.
    tasks: list["Task"] = field(default_factory=list, compare=False, repr=False)

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

    def markComplete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def reopen(self) -> None:
        """Mark this task as not yet done."""
        self.completed = False


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
        """
        seen: list[Task] = []
        for pet in self.pets:
            for task in pet.tasks:
                if task not in seen:
                    seen.append(task)
        # Include any tasks registered on the owner but not yet on a pet.
        for task in self.tasks:
            if task not in seen:
                seen.append(task)
        return seen

    def pendingTasks(self) -> list[Task]:
        """Return all outstanding (not completed) tasks across pets."""
        return [task for task in self.getAllTasks() if not task.completed]


@dataclass
class ScheduledTask:
    scheduleTime: str
    task: Task
    reason: str


@dataclass
class Scheduler:
    scheduleDate: str
    plannedTasks: list[ScheduledTask] = field(default_factory=list)

    def generatePlan(
        self,
        tasks: list[Task],
        availability: list[str],
        preferences: list[str],
    ) -> list[Task]:
        """Build a plan by assigning tasks to available slots.

        Ordering rules (highest to lowest influence):
          1. Tasks whose taskType matches an owner preference go first.
          2. Then by priority, treating a *lower* number as more urgent.
          3. Then longer tasks before shorter ones, so big jobs claim a slot.

        Completed tasks are skipped. Each available slot holds one task;
        remaining tasks that have no slot are returned so the caller can
        surface the conflict.

        Scope note: availability entries are simple labels, and capacity is
        one task per slot by design. Duration-based overbooking (a task too
        long for its slot) is intentionally out of scope — task duration is
        owner-provided data used only for ordering, not for slot-length
        validation, which would require a full time model.
        """
        preferred = {pref.strip().lower() for pref in preferences}

        def sort_key(task: Task):
            is_preferred = task.taskType.strip().lower() in preferred
            # 0 sorts before 1, so preferred tasks come first.
            return (0 if is_preferred else 1, task.priority, -task.duration)

        pending = sorted(
            (task for task in tasks if not task.completed), key=sort_key
        )

        unplaced: list[Task] = []
        for index, task in enumerate(pending):
            if index < len(availability):
                slot = availability[index]
                self.assignTask(task, slot, self._explain(task, preferred))
            else:
                unplaced.append(task)
        return unplaced

    def assignTask(self, task: Task, scheduleTime: str, reason: str) -> None:
        """Place a single task at a time and record why (appends a ScheduledTask)."""
        self.plannedTasks.append(
            ScheduledTask(scheduleTime=scheduleTime, task=task, reason=reason)
        )

    @staticmethod
    def _explain(task: Task, preferred: set[str]) -> str:
        """Human-readable justification for why a task landed where it did."""
        parts = []
        if task.taskType.strip().lower() in preferred:
            parts.append("matches an owner preference")
        parts.append(f"priority {task.priority}")
        parts.append(f"{task.duration} min for {task.pet.petName}")
        return "; ".join(parts)
