"""Simple unit tests for the PawPal system."""

from pawpal_system import Pet, Task, Scheduler


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


def _pet() -> Pet:
    return Pet(petName="Rex", breed="Lab", petAge=4, specialNote="")


def test_short_tasks_pack_into_one_slot_with_computed_times():
    """#1 packing: two short tasks share one slot at back-to-back times."""
    pet = _pet()
    # "play"/"brush" aren't in TASK_TIME_OF_DAY, so they're time-flexible and
    # just fill the earliest window in priority order.
    first = Task(taskType="play", priority=1, duration=10, taskNote="", pet=pet)
    second = Task(taskType="brush", priority=2, duration=15, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan([first, second], ["8:00 AM"], [])

    assert unplaced == []
    times = [scheduled.scheduleTime for scheduled in scheduler.plannedTasks]
    # second starts 10 min after the first (its duration), not at the same time.
    assert times == ["8:00 AM", "8:10 AM"]


def test_task_longer_than_slot_is_unplaced():
    """#1 overbooking: a task too long for any window is surfaced, not placed."""
    pet = _pet()
    big = Task(taskType="play", priority=1, duration=120, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan(
        [big], ["8:00 AM"], [], defaultSlotMinutes=60
    )

    assert big in unplaced
    assert scheduler.plannedTasks == []


def test_availability_is_ordered_chronologically():
    """#3 real ordering: earliest time wins even if given out of order."""
    pet = _pet()
    task = Task(taskType="play", priority=1, duration=10, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    scheduler.generatePlan([task], ["6:00 PM", "8:00 AM"], [])

    assert scheduler.plannedTasks[0].scheduleTime == "8:00 AM"


def test_walk_prefers_evening_over_an_earlier_morning_slot():
    """#4 time-of-day fit: a walk seeks its evening window, skipping morning."""
    pet = _pet()
    walk = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan([walk], ["8:00 AM", "6:00 PM"], [])

    assert unplaced == []
    assert scheduler.plannedTasks[0].scheduleTime == "6:00 PM"


def test_explicit_start_end_window_caps_capacity():
    """#1 explicit windows: a task longer than an explicit (start, end) range
    is unplaced even though the clock time itself is valid."""
    pet = _pet()
    long_task = Task(taskType="play", priority=1, duration=45, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    # A single 30-minute window; a 45-minute task cannot fit.
    unplaced = scheduler.generatePlan(
        [long_task], [("8:00 AM", "8:30 AM")], []
    )

    assert long_task in unplaced
    assert scheduler.plannedTasks == []


def test_non_consecutive_windows_are_both_usable():
    """#1 non-consecutive slots: tasks fill a morning and an evening window
    with a gap between them."""
    pet = _pet()
    feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="", pet=pet)
    walk = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan(
        [feeding, walk], [("8:00 AM", "9:00 AM"), ("6:00 PM", "7:00 PM")], []
    )

    assert unplaced == []
    times = {s.task.taskType: s.scheduleTime for s in scheduler.plannedTasks}
    assert times["feeding"] == "8:00 AM"   # morning window
    assert times["walk"] == "6:00 PM"      # evening window, after the gap


def test_range_string_form_is_accepted():
    """#1 a 'start - end' string is parsed the same as a (start, end) tuple."""
    pet = _pet()
    task = Task(taskType="play", priority=1, duration=20, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan([task], ["9:00 AM - 10:00 AM"], [])

    assert unplaced == []
    assert scheduler.plannedTasks[0].scheduleTime == "9:00 AM"


def test_plan_reads_in_clock_order_even_when_placed_out_of_order():
    """#2 chronological output: a preferred evening task is *placed* first but
    still displays after an earlier morning task."""
    pet = _pet()
    walk = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=pet)
    feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    # "walk" is preferred, so it sorts first and is placed into the evening slot
    # before feeding is placed into the morning slot.
    scheduler.generatePlan([walk, feeding], ["8:00 AM", "6:00 PM"], ["walk"])

    times = [scheduled.scheduleTime for scheduled in scheduler.plannedTasks]
    types = [scheduled.task.taskType for scheduled in scheduler.plannedTasks]
    assert times == ["8:00 AM", "6:00 PM"]  # morning before evening
    assert types == ["feeding", "walk"]     # despite walk being placed first


def test_detects_conflict_when_tasks_share_a_slot():
    """Two tasks packed into one slot yield a warning, not a crash."""
    pet = _pet()
    # Both flexible + short, only one availability slot -> both pack into it.
    first = Task(taskType="play", priority=1, duration=10, taskNote="", pet=pet)
    second = Task(taskType="brush", priority=2, duration=10, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    scheduler.generatePlan([first, second], ["8:00 AM"], [])

    warnings = scheduler.detectConflicts()
    assert len(warnings) == 1
    assert "8:00 AM" in warnings[0]
    assert "play" in warnings[0] and "brush" in warnings[0]


def test_no_conflict_when_tasks_use_separate_slots():
    """Tasks spread across distinct slots produce no warnings."""
    pet = _pet()
    # Distinct time-of-day types land in different windows (morning vs evening).
    feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="", pet=pet)
    walk = Task(taskType="walk", priority=2, duration=20, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    scheduler.generatePlan([feeding, walk], ["8:00 AM", "6:00 PM"], [])

    assert scheduler.detectConflicts() == []


def test_completing_recurring_task_spawns_next_occurrence():
    """A daily task, once done, queues a fresh pending copy on the pet."""
    pet = _pet()
    task = Task(
        taskType="feeding", priority=1, duration=10, taskNote="Kibble",
        pet=pet, recurrence="daily",
    )
    pet.addTask(task)

    nxt = task.markComplete()

    assert task.completed is True            # original is now history
    assert nxt is not None and nxt is not task
    assert nxt.completed is False            # next occurrence is pending
    assert nxt.recurrence == "daily"         # and still recurs
    assert nxt in pet.tasks                  # auto-attached to the pet
    assert len(pet.tasks) == 2


def test_completing_one_off_task_does_not_spawn():
    """A task with no recurrence just completes; nothing new is created."""
    pet = _pet()
    task = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=pet)
    pet.addTask(task)

    result = task.markComplete()

    assert result is None
    assert len(pet.tasks) == 1


def test_completing_twice_does_not_double_spawn():
    """Re-completing an already-done recurring task must not queue extras."""
    pet = _pet()
    task = Task(
        taskType="walk", priority=1, duration=20, taskNote="",
        pet=pet, recurrence="weekly",
    )
    pet.addTask(task)

    task.markComplete()
    second = task.markComplete()  # already completed -> no-op

    assert second is None
    assert len(pet.tasks) == 2  # original + exactly one spawned occurrence
