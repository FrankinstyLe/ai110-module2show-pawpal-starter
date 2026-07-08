import streamlit as st
from datetime import date, time
from pawpal_system import (
    Owner,
    Pet,
    Task,
    Scheduler,
    mergeSameActivities,
    findMergeableActivities,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

Add your pets and their care tasks, set the hours you're free, then generate a
care plan for the day.
"""
)

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

with st.expander("How it works", expanded=False):
    st.markdown(
        """
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent one or more pets and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
- Mark tasks done **in the generated schedule**; completing a **daily**/**weekly**
  task queues its next occurrence on the next date (+1 day / +7 days)
"""
    )

st.divider()

# Priority is a string in the UI but an int in the model, where a *lower*
# number means more urgent (see Scheduler.generatePlan). high -> 1 (most urgent).
PRIORITY_TO_INT = {"high": 1, "medium": 2, "low": 3}
RECURRENCE_OPTIONS = ["none", "daily", "weekly"]
# Common pet types for the selectbox; "Other" lets an owner type a free-form
# species without us trying to enumerate every animal.
PET_TYPE_OPTIONS = ["Dog", "Cat", "Bird", "Rabbit", "Fish", "Reptile", "Other"]


def fmt_time(t: time) -> str:
    """Format a datetime.time as an '8:00 AM' label (no leading zero)."""
    hour12 = t.hour % 12 or 12
    suffix = "AM" if t.hour < 12 else "PM"
    return f"{hour12}:{t.minute:02d} {suffix}"


def _recurrence_badge(task: Task) -> str:
    """Small label showing whether/how a task repeats."""
    return f"🔁 {task.recurrence}" if task.isRecurring() else "—"


def _due_badge(task: Task) -> str:
    """Small label showing the day a task is due, blank if it carries no date."""
    return f"📅 {task.dueDate:%b %d}" if task.dueDate else ""


def _type_options_for(current: str) -> list[str]:
    """Selectbox options that always include the pet's current type.

    Keeps a previously-saved custom type selectable instead of silently
    snapping it back to the first option on the next rerun.
    """
    if current and current not in PET_TYPE_OPTIONS:
        return [current] + PET_TYPE_OPTIONS
    return PET_TYPE_OPTIONS


# --- Persistent state (survives Streamlit reruns) ---------------------------
# Pets and their Task objects live here so completing a recurring task (which
# spawns its next occurrence) sticks across reruns. Availability windows are
# (start, end) label pairs and may be non-consecutive.
if "pets" not in st.session_state:
    # Start empty so the owner fills in their own pets, tasks, and availability.
    st.session_state.pets = []
if "slots" not in st.session_state:
    st.session_state.slots = []

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="")

# --- Pets -------------------------------------------------------------------
st.subheader("Pets")
st.caption("Add one or more pets. Every task belongs to a pet.")

# Widgets key on pet.uid (stable) rather than list index, so removing a pet
# never leaves another pet bound to a stale widget value.
for pet in st.session_state.pets:
    header = f"🐾 {pet.petName or 'Unnamed pet'}"
    if pet.petType:
        header += f" · {pet.petType}"
    with st.expander(
        header,
        expanded=len(st.session_state.pets) == 1,
    ):
        c1, c2 = st.columns(2)
        with c1:
            pet.petName = st.text_input("Name", value=pet.petName, key=f"pn_{pet.uid}")
            type_options = _type_options_for(pet.petType)
            pet.petType = st.selectbox(
                "Type",
                options=type_options,
                index=type_options.index(pet.petType) if pet.petType in type_options else 0,
                key=f"pt_{pet.uid}",
            )
            pet.breed = st.text_input("Breed", value=pet.breed, key=f"pb_{pet.uid}")
        with c2:
            pet.petAge = int(
                st.number_input(
                    "Age (years)", min_value=0, max_value=50,
                    value=pet.petAge, key=f"pa_{pet.uid}",
                )
            )
            pet.specialNote = st.text_input(
                "Special note", value=pet.specialNote, key=f"ps_{pet.uid}"
            )
        if st.button("Remove pet", key=f"prm_{pet.uid}"):
            st.session_state.pets = [
                p for p in st.session_state.pets if p.uid != pet.uid
            ]
            st.session_state.pop("plan", None)  # a removed pet's tasks may be gone
            st.rerun()

with st.form("add_pet", clear_on_submit=True):
    st.markdown("**Add a pet**")
    ac1, ac2 = st.columns(2)
    with ac1:
        new_name = st.text_input("Name", value="")
        new_type = st.selectbox("Type", options=PET_TYPE_OPTIONS, index=0)
        new_breed = st.text_input("Breed", value="")
    with ac2:
        new_age = st.number_input("Age (years)", min_value=0, max_value=50, value=1)
        new_note = st.text_input("Special note", value="")
    if st.form_submit_button("Add pet"):
        if new_name.strip():
            st.session_state.pets.append(
                Pet(petName=new_name.strip(), petType=new_type, breed=new_breed,
                    petAge=int(new_age), specialNote=new_note)
            )
            st.rerun()
        else:
            st.warning("Give the pet a name first.")

st.divider()

# Build the owner once from the current pets so the task list, the combine
# choices, and the scheduler all read the same hierarchy. Pet field edits above
# have already been applied to these same objects.
owner = Owner(ownerName=owner_name)
for pet in st.session_state.pets:
    owner.addPet(pet)

# The day we're planning for. Read from the (later) schedule-date widget's saved
# value so "due today" and the combine choices match what will be scheduled;
# defaults to today on the first run, before that widget has been created.
planning_day = st.session_state.get("schedule_date", date.today())

# Populated by the "Combine activities" picker below; consumed at generate time.
selected_merge_keys: set[str] = set()

# --- Tasks ------------------------------------------------------------------
st.subheader("Tasks")
if not st.session_state.pets:
    st.info("Add a pet above before creating tasks.")
else:
    st.caption(
        "Add tasks for a pet. You mark them done in the generated schedule "
        "below — completing a daily/weekly task queues its next occurrence on "
        "the next date (+1 day / +7 days)."
    )
    pets = st.session_state.pets
    # Index-based selection keeps the option values hashable for session_state.
    target_idx = st.selectbox(
        "Add task for",
        options=range(len(pets)),
        format_func=lambda i: pets[i].petName or f"Pet {i + 1}",
        key="task_target",
    )
    target_pet = pets[target_idx]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_title = st.text_input("Task title", value="")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    with col4:
        recurrence_choice = st.selectbox("Repeats", RECURRENCE_OPTIONS, index=0)
    task_note = st.text_input("Task note", value="")

    col_add, col_clear = st.columns(2)
    with col_add:
        if st.button("Add task"):
            if task_title.strip():
                target_pet.tasks.append(
                    Task(
                        taskType=task_title.strip(),
                        priority=PRIORITY_TO_INT.get(priority, 2),
                        duration=int(duration),
                        taskNote=task_note,
                        pet=target_pet,
                        recurrence=None if recurrence_choice == "none" else recurrence_choice,
                        # Dated to today so a completed recurring task's next
                        # occurrence lands on a *future* day instead of today.
                        dueDate=date.today(),
                    )
                )
            else:
                st.warning("Give the task a title first.")
    with col_clear:
        if st.button("Clear all tasks"):
            for p in pets:
                p.tasks.clear()
            st.session_state.pop("plan", None)
            st.rerun()

    st.markdown("#### Current tasks")
    all_pending = owner.pendingTasks()  # completed tasks drop off this list
    if all_pending:
        for pet in pets:
            pet_pending = [task for task in pet.tasks if not task.completed]
            if not pet_pending:
                continue
            st.markdown(f"**{pet.petName or 'Unnamed pet'}**")
            # Earliest-due first; undated tasks sort last.
            for task in sorted(
                pet_pending,
                key=lambda t: (t.dueDate or date.max, t.taskType.lower()),
            ):
                label_col, prio_col, meta_col, rm_col = st.columns(
                    [0.46, 0.16, 0.24, 0.14]
                )
                with label_col:
                    st.write(f"**{task.taskType}** — {task.duration} min")
                    if task.taskNote:
                        st.caption(task.taskNote)
                with prio_col:
                    st.write(f"priority {task.priority}")
                with meta_col:
                    badges = " ".join(
                        b for b in (_recurrence_badge(task), _due_badge(task)) if b and b != "—"
                    )
                    st.write(badges or "—")
                with rm_col:
                    if st.button("Remove", key=f"taskrm_{task.uid}"):
                        pet.tasks[:] = [t for t in pet.tasks if t.uid != task.uid]
                        st.session_state.pop("plan", None)
                        st.rerun()
    else:
        st.info("No pending tasks. Add one above.")

    # --- Combine activities (moved here, under Current tasks) ---------------
    # Offer to combine only genuinely identical activities (same type AND
    # duration) that more than one pet shares, among the tasks due for the day
    # we're planning. The owner picks which ones — not an all-or-nothing switch.
    due_pending = owner.pendingTasksDueBy(planning_day)
    merge_candidates = findMergeableActivities(due_pending)
    if merge_candidates:
        st.markdown("#### Combine activities")
        st.caption(
            "These identical activities are shared by more than one pet. Tick "
            "any you'd like to do together in a single time slot — your per-pet "
            "tasks stay unchanged."
        )
        for candidate in merge_candidates:
            label = (
                f"{candidate['taskType']} ({candidate['duration']} min) — "
                + ", ".join(candidate["pets"])
            )
            # Key on the stable activity id so each checkbox survives reruns.
            if st.checkbox(label, value=False, key=f"merge_{candidate['key']}"):
                selected_merge_keys.add(candidate["key"])

st.divider()

# --- Availability -----------------------------------------------------------
st.subheader("Availability")
st.caption(
    "Add the time windows you're free today. Windows can be non-consecutive; "
    "tasks pack into each window by duration until the next won't fit."
)

start_col, end_col, add_col = st.columns([0.4, 0.4, 0.2])
with start_col:
    slot_start = st.time_input("Start", value=time(8, 0), key="slot_start")
with end_col:
    slot_end = st.time_input("End", value=time(12, 0), key="slot_end")
with add_col:
    st.write("")  # nudge the button down to line up with the inputs
    st.write("")
    add_slot = st.button("Add slot")
if add_slot:
    if slot_end <= slot_start:
        st.warning("End time must be after start time.")
    else:
        st.session_state.slots.append((fmt_time(slot_start), fmt_time(slot_end)))
        st.session_state.pop("plan", None)
        st.rerun()

if st.session_state.slots:
    for index, (start_label, end_label) in enumerate(st.session_state.slots):
        row_col, remove_col = st.columns([0.8, 0.2])
        row_col.write(f"🕐 {start_label} – {end_label}")
        if remove_col.button("Remove", key=f"slotrm_{index}"):
            st.session_state.slots.pop(index)
            st.session_state.pop("plan", None)
            st.rerun()
else:
    st.info("No availability slots yet — add at least one.")

st.markdown("### Preferences")
preferences_str = st.text_input(
    "Preferences (comma-separated task types to prioritize)", value=""
)

st.divider()

# --- Build schedule ---------------------------------------------------------
st.subheader("Build Schedule")
st.caption(
    "Plans the tasks due for the chosen date. Mark tasks done here — a "
    "daily/weekly task then queues its next occurrence automatically."
)

# key= lets the Tasks section read this day back (see planning_day above).
schedule_date = st.date_input("Schedule date", key="schedule_date")
tasks_for_day = owner.pendingTasksDueBy(schedule_date)

st.markdown("#### 🔔 Still to do")
if tasks_for_day:
    st.info(f"{len(tasks_for_day)} task(s) due for {schedule_date}.")
else:
    st.success("Nothing due for this date. 🎉")

if st.button("Generate schedule"):
    if not tasks_for_day:
        st.warning("No tasks due for this date. Add some, or pick another date.")
        st.session_state.pop("plan", None)
    elif not st.session_state.slots:
        st.warning("Add at least one availability slot before generating.")
        st.session_state.pop("plan", None)
    else:
        preferences = [p.strip() for p in preferences_str.split(",") if p.strip()]

        # Merging is a scheduling-time view: collapse only the activity groups
        # the owner chose, leaving the per-pet tasks untouched.
        tasks_to_plan = mergeSameActivities(tasks_for_day, selected_merge_keys)

        scheduler = Scheduler(scheduleDate=str(schedule_date))
        unplaced = scheduler.generatePlan(
            tasks_to_plan, list(st.session_state.slots), preferences
        )

        # Stash the plan so it survives reruns. Each entry keeps references to
        # the real per-pet tasks it covers (a combined entry covers several via
        # Task.mergedFrom), so the "Done" control can complete them.
        st.session_state.plan = {
            "date": scheduler.scheduleDate,
            "entries": [
                {
                    "time": scheduled.scheduleTime,
                    "petName": scheduled.task.pet.petName,
                    "taskType": scheduled.task.taskType,
                    "duration": scheduled.task.duration,
                    "priority": scheduled.task.priority,
                    "recurrence": scheduled.task.recurrence,
                    "reason": scheduled.reason,
                    "tasks": scheduled.task.mergedFrom or [scheduled.task],
                }
                for scheduled in scheduler.plannedTasks
            ],
            "unplaced": [
                f"{task.pet.petName}: {task.taskType}" for task in unplaced
            ],
            "conflicts": scheduler.detectConflicts(),
        }

plan = st.session_state.get("plan")
if plan:
    st.success(f"Plan for {plan['date']}")
    entries = plan["entries"]
    if entries:
        # Header row for a table-like, professional layout.
        h = st.columns([0.1, 0.16, 0.44, 0.14, 0.16])
        for col, title in zip(h, ["Done", "Time", "Task", "Repeats", "Priority"]):
            col.markdown(f"**{title}**")
        for entry in entries:
            underlying = entry["tasks"]
            done = all(task.completed for task in underlying)
            done_col, time_col, task_col, repeat_col, prio_col = st.columns(
                [0.1, 0.16, 0.44, 0.14, 0.16]
            )
            with done_col:
                # Stable key across reruns from every underlying task's uid.
                checked = st.checkbox(
                    "done",
                    value=done,
                    key="plandone_" + "_".join(str(t.uid) for t in underlying),
                    label_visibility="collapsed",
                )
            with time_col:
                st.write(f"🕐 {entry['time']}")
            with task_col:
                label = f"{entry['petName']} — {entry['taskType']}"
                st.write(f"~~{label}~~" if done else f"**{label}**")
            with repeat_col:
                st.write(f"🔁 {entry['recurrence']}" if entry["recurrence"] else "—")
            with prio_col:
                st.write(f"priority {entry['priority']}")

            # Full-width explanation: why this task was chosen and when it lands.
            st.caption(f"💡 {entry['reason']}")

            # Completing here marks every underlying per-pet task done; each
            # recurring one queues its next occurrence on the +1/+7 date.
            if checked and not done:
                spawned = [
                    task.markComplete()
                    for task in underlying
                    if not task.completed
                ]
                spawned_dates = sorted(
                    {s.dueDate for s in spawned if s is not None and s.dueDate}
                )
                if spawned_dates:
                    when = ", ".join(f"{d:%b %d}" for d in spawned_dates)
                    st.session_state.last_spawn = (
                        f"Done: {entry['taskType']} for {entry['petName']}. "
                        f"Next occurrence queued for {when}."
                    )
                st.rerun()
            elif not checked and done:
                for task in underlying:
                    task.reopen()
                st.rerun()
    else:
        st.info("No tasks could be placed. Check your availability slots.")

    if st.session_state.get("last_spawn"):
        st.toast(st.session_state.pop("last_spawn"))

    # Soft conflicts: tasks packed back-to-back in one slot. The plan still
    # works, so frame these as a heads-up with a concrete next step rather than
    # an error the owner can't act on.
    conflicts = plan.get("conflicts", [])
    if conflicts:
        st.markdown("#### ⚠️ Heads up")
        st.caption(
            "These tasks still fit, but they're squeezed into the same window. "
            "Add another availability slot if you'd rather space them out."
        )
        for warning in conflicts:
            st.warning(warning)

    # Unplaced tasks genuinely won't get done — a harder problem than a
    # back-to-back conflict, so it gets an error, not another yellow warning.
    if plan["unplaced"]:
        st.error(
            f"❌ {len(plan['unplaced'])} task(s) had no available slot and "
            f"won't be scheduled: " + ", ".join(plan["unplaced"])
            + ". Add more availability to fit them in."
        )
