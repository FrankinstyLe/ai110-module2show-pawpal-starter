"""PawPal demo script.

Builds a small owner/pet/task setup, generates a plan with the Scheduler,
and prints Today's Schedule to the terminal.

Tasks are added deliberately OUT OF ORDER (and one is pre-completed) so the
terminal output shows the system's filtering method (Owner.pendingTasks drops
completed tasks) and sorting logic (Scheduler.generatePlan reorders by
preference, then priority, then duration) actually working.
"""

from datetime import date

from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
    # The day this plan is for; reused as the due date of dated tasks below.
    today = date(2026, 7, 7)

    # Create an owner with availability and scheduling preferences.
    owner = Owner(ownerName="Alex")
    owner.addTime("8:00 AM")
    owner.addTime("12:30 PM")
    owner.addTime("6:00 PM")
    owner.addPreferences("feeding")

    # Create at least two pets.
    rex = Pet(petName="Rex", breed="Labrador", petAge=4,
              specialNote="Loves long walks")
    milo = Pet(petName="Milo", breed="Tabby Cat", petAge=2,
               specialNote="Needs medication with food")
    owner.addPet(rex)
    owner.addPet(milo)

    # Add tasks OUT OF ORDER on purpose: a low-priority walk first, then a
    # high-priority med, a task that's already done, and the preferred feeding
    # last. If sorting/filtering work, the plan below will NOT match this order.
    owner.addTask(Task(taskType="walk", priority=2, duration=30,
                       taskNote="Neighborhood loop", pet=rex))
    owner.addTask(Task(taskType="medication", priority=1, duration=5,
                       taskNote="Give with lunch", pet=milo))
    groomed = Task(taskType="grooming", priority=1, duration=20,
                   taskNote="Already brushed this morning", pet=rex)
    groomed.markComplete()  # this one should get filtered out of the plan
    owner.addTask(groomed)
    # Rex's breakfast is a daily routine, dated to today, so completing it later
    # queues tomorrow's occurrence (see the Recurrence section at the end).
    rex_breakfast = Task(taskType="feeding", priority=1, duration=10,
                         taskNote="Morning kibble", pet=rex,
                         recurrence="daily", dueDate=today)
    owner.addTask(rex_breakfast)
    # Milo also needs breakfast: two feedings compete for the one morning slot,
    # which the Scheduler should flag as a same-slot conflict (below).
    owner.addTask(Task(taskType="feeding", priority=1, duration=10,
                       taskNote="Morning wet food", pet=milo))

    # --- Filtering: show every task as entered, then the pending-only set. ---
    print("Tasks as added (insertion order, unsorted):")
    for task in owner.tasks:
        status = "done" if task.completed else "pending"
        print(f"  - {task.pet.petName}: {task.taskType} "
              f"(priority {task.priority}, {status})")

    pending = owner.pendingTasks()  # filtering method: skips completed tasks
    dropped = len(owner.tasks) - len(pending)
    print(f"\nFiltering (pendingTasks): {len(owner.tasks)} total -> "
          f"{len(pending)} pending; {dropped} completed task(s) skipped.\n")

    # --- Sorting: generatePlan sorts the pending tasks before placing them. ---
    scheduler = Scheduler(scheduleDate=today.isoformat())
    unplaced = scheduler.generatePlan(
        tasks=pending,
        availability=owner.availability,
        preferences=owner.preferences,
    )

    # Print Today's Schedule (now in sorted / scheduled order).
    print(f"Today's Schedule ({scheduler.scheduleDate}) for {owner.ownerName}")
    print("=" * 48)
    for scheduled in scheduler.plannedTasks:
        task = scheduled.task
        print(f"{scheduled.scheduleTime:>9}  {task.pet.petName}: "
              f"{task.taskType} ({task.duration} min)")
        print(f"           - {task.taskNote}")
        print(f"           - why: {scheduled.reason}")

    # The walk was added first but, being lowest priority, is scheduled last —
    # proof the sort ran. Grooming never appears — proof the filter ran.
    print("\n(Note: 'walk' was added first but scheduled last, and the "
          "completed 'grooming' task is absent.)")

    # Lightweight conflict detection: warn (don't crash) when a slot is shared.
    # ASCII-only marker so this prints on a default Windows console (cp1252).
    conflicts = scheduler.detectConflicts()
    if conflicts:
        print("\n[!] Schedule warnings:")
        for warning in conflicts:
            print(f"  - {warning}")

    if unplaced:
        print("\nUnscheduled (no available slot):")
        for task in unplaced:
            print(f"  - {task.pet.petName}: {task.taskType}")

    # --- Recurrence: completing a daily task queues tomorrow's occurrence. ---
    # Done after the schedule prints so it doesn't disturb today's plan.
    print(f"\nRecurrence ({rex.petName}'s {rex_breakfast.taskType}):")
    print(f"  today's occurrence due {rex_breakfast.dueDate}; marking done...")
    next_breakfast = rex_breakfast.markComplete()
    if next_breakfast is not None:
        print(f"  -> queued next occurrence due {next_breakfast.dueDate} "
              f"(pending, still recurs {next_breakfast.recurrence}).")


if __name__ == "__main__":
    main()
