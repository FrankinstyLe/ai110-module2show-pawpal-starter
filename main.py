"""PawPal demo script.

Builds a small owner/pet/task setup, generates a plan with the Scheduler,
and prints Today's Schedule to the terminal.
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
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

    # Add at least three tasks with different times/priorities to the pets.
    owner.addTask(Task(taskType="feeding", priority=1, duration=10,
                       taskNote="Morning kibble", pet=rex))
    owner.addTask(Task(taskType="walk", priority=2, duration=30,
                       taskNote="Neighborhood loop", pet=rex))
    owner.addTask(Task(taskType="medication", priority=1, duration=5,
                       taskNote="Give with lunch", pet=milo))

    # Generate the plan for today.
    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan(
        tasks=owner.getAllTasks(),
        availability=owner.availability,
        preferences=owner.preferences,
    )

    # Print Today's Schedule.
    print(f"Today's Schedule ({scheduler.scheduleDate}) for {owner.ownerName}")
    print("=" * 48)
    for scheduled in scheduler.plannedTasks:
        task = scheduled.task
        print(f"{scheduled.scheduleTime:>9}  {task.pet.petName}: "
              f"{task.taskType} ({task.duration} min)")
        print(f"           - {task.taskNote}")
        print(f"           - why: {scheduled.reason}")

    if unplaced:
        print("\nUnscheduled (no available slot):")
        for task in unplaced:
            print(f"  - {task.pet.petName}: {task.taskType}")


if __name__ == "__main__":
    main()
