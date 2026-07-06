"""PawPal system class skeleton.

Generated from diagrams/uml.mmd. Data-only objects (Pet, Task) use
dataclasses; classes with behavior (Owner, Schedule) are regular classes.
Method bodies are stubs to be implemented later.
"""

from dataclasses import dataclass, field


@dataclass
class Pet:
    petName: str
    breed: str
    petAge: int
    specialNote: str


@dataclass
class Task:
    taskType: str
    priority: int
    duration: int
    taskNote: str
    pet: Pet  # UML: Pet "1" --> "*" Task — every task belongs to a pet


@dataclass
class Owner:
    ownerName: str
    availability: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def addPet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def addTask(self, task: Task) -> None:
        """Add a task defined by this owner."""
        pass

    def addTime(self, slot: str) -> None:
        """Add an availability time slot."""
        pass

    def addPreferences(self, preference: str) -> None:
        """Add a scheduling preference."""
        pass


@dataclass
class ScheduledTask:
    scheduleTime: str
    task: Task
    reason: str


@dataclass
class Schedule:
    scheduleDate: str
    plannedTasks: list[ScheduledTask] = field(default_factory=list)

    def generatePlan(
        self,
        tasks: list[Task],
        availability: list[str],
        preferences: list[str],
    ) -> list[Task]:
        """Build a plan by assigning tasks to available slots.

        Returns the tasks that could NOT be placed (e.g. no slot large
        enough, or availability exhausted), so callers can surface conflicts.

        TODO: availability is list[str] of opaque labels — there is no slot
        length to compare against Task.duration, so overbooking cannot be
        detected yet. Decide whether slots should carry start/end times.
        """
        pass

    def assignTask(self, task: Task, scheduleTime: str, reason: str) -> None:
        """Place a single task at a time and record why (appends a ScheduledTask)."""
        self.plannedTasks.append(
            ScheduledTask(scheduleTime=scheduleTime, task=task, reason=reason)
        )
