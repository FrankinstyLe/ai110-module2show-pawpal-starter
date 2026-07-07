"""Simple unit tests for the PawPal system."""

from pawpal_system import Pet, Task


def test_mark_complete_changes_status():
    """Task Completion: markComplete() flips a task's status to done."""
    pet = Pet(petName="Mochi", breed="Shiba", petAge=3, specialNote="")
    task = Task(
        taskType="walk",
        priority=1,
        duration=20,
        taskNote="Morning walk",
        pet=pet,
    )

    assert task.completed is False  # starts out not done

    task.markComplete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet increases its task count."""
    pet = Pet(petName="Mochi", breed="Shiba", petAge=3, specialNote="")
    task = Task(
        taskType="feed",
        priority=2,
        duration=5,
        taskNote="Breakfast",
        pet=pet,
    )

    assert len(pet.tasks) == 0  # no tasks yet

    pet.addTask(task)

    assert len(pet.tasks) == 1
