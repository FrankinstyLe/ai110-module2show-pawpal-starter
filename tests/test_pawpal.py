"""Simple unit tests for the PawPal system."""

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Scheduler


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


def test_completing_daily_task_creates_task_for_the_following_day():
    """Recurrence logic: completing a daily task dated today queues its next
    occurrence dated tomorrow (the literal 'following day')."""
    pet = _pet()
    today = date(2026, 7, 7)
    task = Task(
        taskType="feeding", priority=1, duration=10, taskNote="Kibble",
        pet=pet, recurrence="daily", dueDate=today,
    )
    pet.addTask(task)

    nxt = task.markComplete()

    assert nxt is not None
    assert nxt.completed is False
    assert nxt.dueDate == today + timedelta(days=1)   # advanced by one day
    assert nxt.dueDate == date(2026, 7, 8)            # ...i.e. the following day


def test_completing_weekly_task_advances_seven_days():
    """A weekly task's next occurrence is dated one week out."""
    pet = _pet()
    task = Task(
        taskType="grooming", priority=1, duration=20, taskNote="",
        pet=pet, recurrence="weekly", dueDate=date(2026, 7, 7),
    )

    nxt = task.markComplete()

    assert nxt is not None
    assert nxt.dueDate == date(2026, 7, 14)  # +7 days


def test_recurring_task_without_a_duedate_stays_undated():
    """An undated recurring task still spawns, and its copy stays dateless
    rather than crashing on date math."""
    pet = _pet()
    task = Task(
        taskType="feeding", priority=1, duration=10, taskNote="",
        pet=pet, recurrence="daily",
    )

    nxt = task.markComplete()

    assert nxt is not None
    assert nxt.dueDate is None


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


# --- Top group: empties, no-availability, and the headline sort rule. ---


def test_empty_task_list_produces_empty_plan():
    """Edge: planning zero tasks yields an empty plan and no unplaced items."""
    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan([], ["8:00 AM"], [])

    assert unplaced == []
    assert scheduler.plannedTasks == []


def test_no_availability_leaves_every_task_unplaced():
    """Edge: with no availability, tasks are surfaced as unplaced, not dropped
    and never crash."""
    pet = _pet()
    feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="", pet=pet)
    walk = Task(taskType="walk", priority=2, duration=20, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan([feeding, walk], [], [])

    assert scheduler.plannedTasks == []
    assert feeding in unplaced and walk in unplaced


def test_pet_with_no_tasks_contributes_nothing():
    """Edge: a task-less pet doesn't break aggregation; a pet with tasks still
    reports its pending work."""
    empty = Pet(petName="Ghost", breed="Sphynx", petAge=1, specialNote="")
    busy = Pet(petName="Rex", breed="Lab", petAge=4, specialNote="")
    task = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=busy)

    owner = Owner(ownerName="Alex")
    owner.addPet(empty)
    owner.addTask(task)  # also registers `busy`

    assert empty.tasks == []
    assert owner.getAllTasks() == [task]
    assert owner.pendingTasks() == [task]


def test_preference_outranks_priority():
    """Happy path: a preferred low-priority task is placed before a
    non-preferred high-priority one — preference is the top sort dimension."""
    pet = _pet()
    # feeding is preferred but least urgent; medication is unpreferred but most
    # urgent. Both flexible enough to share the single roomy morning window.
    feeding = Task(taskType="feeding", priority=3, duration=10, taskNote="", pet=pet)
    medication = Task(taskType="medication", priority=1, duration=5, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    # One wide window so both fit and placement order is decided purely by sort.
    unplaced = scheduler.generatePlan(
        [medication, feeding], [("8:00 AM", "12:00 PM")], ["feeding"]
    )

    assert unplaced == []
    types = [scheduled.task.taskType for scheduled in scheduler.plannedTasks]
    assert types == ["feeding", "medication"]  # preferred first despite lower urgency


# --- Recurrence normalization: casing/whitespace, unknown values, reopen. ---


def test_recurrence_casing_and_whitespace_still_recurs():
    """isRecurring() normalizes case and surrounding whitespace, so a messy
    recurrence value still spawns a next occurrence on completion."""
    pet = _pet()
    task = Task(
        taskType="feeding", priority=1, duration=10, taskNote="",
        pet=pet, recurrence="  Daily ",
    )

    assert task.isRecurring() is True

    nxt = task.markComplete()

    assert nxt is not None
    assert nxt.completed is False
    assert nxt.recurrence == "  Daily "  # value preserved verbatim on the copy


def test_unrecognized_recurrence_is_treated_as_one_off():
    """A recurrence value outside RECURRENCES (e.g. 'monthly') does not recur;
    completing it spawns nothing."""
    pet = _pet()
    task = Task(
        taskType="walk", priority=1, duration=20, taskNote="",
        pet=pet, recurrence="monthly",
    )
    pet.addTask(task)

    assert task.isRecurring() is False

    result = task.markComplete()

    assert result is None
    assert len(pet.tasks) == 1  # no next occurrence queued


def test_reopen_flips_completed_back_to_false():
    """reopen() undoes completion so a task can be re-planned."""
    pet = _pet()
    task = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=pet)

    task.markComplete()
    assert task.completed is True

    task.reopen()
    assert task.completed is False


# --- Boundary cases: exact fit, all-equal tie-break, unparseable label. ---


def test_task_exactly_filling_a_window_fits():
    """Boundary: capacity check is inclusive (>=), so a task whose duration
    equals the window length fits rather than being unplaced."""
    pet = _pet()
    task = Task(taskType="play", priority=1, duration=60, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    # Bare label -> a defaultSlotMinutes (60) window; a 60-min task exactly fits.
    unplaced = scheduler.generatePlan(
        [task], ["8:00 AM"], [], defaultSlotMinutes=60
    )

    assert unplaced == []
    assert scheduler.plannedTasks[0].scheduleTime == "8:00 AM"


def test_all_equal_sort_keys_preserve_insertion_order():
    """Tie-break: when preference, priority, and time-of-day all match, the sort
    is stable, so tasks keep the order they were handed in."""
    pet = _pet()
    # Same flexible type + same priority => identical sort keys.
    first = Task(taskType="play", priority=1, duration=10, taskNote="first", pet=pet)
    second = Task(taskType="play", priority=1, duration=10, taskNote="second", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan(
        [first, second], [("8:00 AM", "12:00 PM")], []
    )

    assert unplaced == []
    notes = [scheduled.task.taskNote for scheduled in scheduler.plannedTasks]
    assert notes == ["first", "second"]  # input order preserved on ties


def test_unparseable_availability_label_still_forms_a_window():
    """An availability entry the parser can't read (e.g. 'whenever') falls back
    to the 8:00 AM cursor and still yields a usable window."""
    pet = _pet()
    task = Task(taskType="play", priority=1, duration=10, taskNote="", pet=pet)

    scheduler = Scheduler(scheduleDate="2026-07-07")
    unplaced = scheduler.generatePlan([task], ["whenever"], [])

    assert unplaced == []
    assert scheduler.plannedTasks[0].scheduleTime == "8:00 AM"  # cursor anchor


# --- Documenting test: Task equality ignores pet & uid (see memory note). ---


def test_identical_tasks_on_different_pets_are_deduped():
    """Sharp edge, pinned deliberately: Task equality compares only
    type/priority/duration/note/completed/recurrence -- pet and uid are
    excluded. So two tasks with identical fields on *different* pets compare
    equal, and the owner's aggregation keeps only one. Each pet still holds its
    own task, but getAllTasks() collapses them. If this ever changes, it should
    be a deliberate, test-visible decision."""
    rex = Pet(petName="Rex", breed="Lab", petAge=4, specialNote="")
    milo = Pet(petName="Milo", breed="Tabby", petAge=2, specialNote="")
    rex_feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="kibble", pet=rex)
    milo_feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="kibble", pet=milo)

    assert rex_feeding == milo_feeding  # equal despite belonging to different pets

    owner = Owner(ownerName="Alex")
    owner.addTask(rex_feeding)
    owner.addTask(milo_feeding)

    # Each pet still holds its own task object...
    assert rex.tasks == [rex_feeding]
    assert milo.tasks == [milo_feeding]
    # ...but owner-level aggregation collapses the two equal tasks into one.
    assert len(owner.getAllTasks()) == 1


# --- Rubric coverage: explicit chronological-order check across 3 windows. ---


def test_plan_returned_in_chronological_order():
    """Sorting correctness: tasks handed in scrambled order come out of the
    planner sorted by real clock time across morning/afternoon/evening."""
    pet = _pet()
    feeding = Task(taskType="feeding", priority=1, duration=10, taskNote="", pet=pet)      # morning
    medication = Task(taskType="medication", priority=1, duration=5, taskNote="", pet=pet)  # afternoon
    walk = Task(taskType="walk", priority=1, duration=20, taskNote="", pet=pet)             # evening

    scheduler = Scheduler(scheduleDate="2026-07-07")
    # Input order is deliberately NOT chronological; availability is scrambled too.
    unplaced = scheduler.generatePlan(
        [walk, feeding, medication], ["6:00 PM", "8:00 AM", "1:00 PM"], []
    )

    assert unplaced == []
    times = [scheduled.scheduleTime for scheduled in scheduler.plannedTasks]
    assert times == ["8:00 AM", "1:00 PM", "6:00 PM"]  # sorted, not input order
    # And the ordering is genuinely by parsed minutes, not string luck.
    minutes = [Scheduler._parseTime(t) for t in times]
    assert minutes == sorted(minutes)
