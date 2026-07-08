import streamlit as st
from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler

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
- Mark tasks done; completing a **daily**/**weekly** task queues its next occurrence
"""
    )

st.divider()

# Priority is a string in the UI but an int in the model, where a *lower*
# number means more urgent (see Scheduler.generatePlan). high -> 1 (most urgent).
PRIORITY_TO_INT = {"high": 1, "medium": 2, "low": 3}
RECURRENCE_OPTIONS = ["none", "daily", "weekly"]


def fmt_time(t: time) -> str:
    """Format a datetime.time as an '8:00 AM' label (no leading zero)."""
    hour12 = t.hour % 12 or 12
    suffix = "AM" if t.hour < 12 else "PM"
    return f"{hour12}:{t.minute:02d} {suffix}"


def _recurrence_badge(task: Task) -> str:
    """Small label showing whether/how a task repeats."""
    return f"🔁 {task.recurrence}" if task.isRecurring() else "—"


# --- Persistent state (survives Streamlit reruns) ---------------------------
# Pets and their Task objects live here so completing a recurring task (which
# spawns its next occurrence) sticks across reruns. Availability windows are
# (start, end) label pairs and may be non-consecutive.
if "pets" not in st.session_state:
    st.session_state.pets = [
        Pet(petName="Mochi", breed="Shiba Inu", petAge=3, specialNote="")
    ]
if "slots" not in st.session_state:
    st.session_state.slots = [("8:00 AM", "12:00 PM"), ("5:00 PM", "8:00 PM")]

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")

# --- Pets -------------------------------------------------------------------
st.subheader("Pets")
st.caption("Add one or more pets. Every task belongs to a pet.")

# Widgets key on pet.uid (stable) rather than list index, so removing a pet
# never leaves another pet bound to a stale widget value.
for pet in st.session_state.pets:
    with st.expander(
        f"🐾 {pet.petName or 'Unnamed pet'}",
        expanded=len(st.session_state.pets) == 1,
    ):
        c1, c2 = st.columns(2)
        with c1:
            pet.petName = st.text_input("Name", value=pet.petName, key=f"pn_{pet.uid}")
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
        new_breed = st.text_input("Breed", value="")
    with ac2:
        new_age = st.number_input("Age (years)", min_value=0, max_value=50, value=1)
        new_note = st.text_input("Special note", value="")
    if st.form_submit_button("Add pet"):
        if new_name.strip():
            st.session_state.pets.append(
                Pet(petName=new_name.strip(), breed=new_breed,
                    petAge=int(new_age), specialNote=new_note)
            )
            st.rerun()
        else:
            st.warning("Give the pet a name first.")

st.divider()

# --- Tasks ------------------------------------------------------------------
st.subheader("Tasks")
if not st.session_state.pets:
    st.info("Add a pet above before creating tasks.")
else:
    st.caption(
        "Add tasks for a pet, tick them off as done, and set a recurrence so "
        "completing one automatically queues the next occurrence."
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
        task_title = st.text_input("Task title", value="Morning walk")
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
            target_pet.tasks.append(
                Task(
                    taskType=task_title,
                    priority=PRIORITY_TO_INT.get(priority, 2),
                    duration=int(duration),
                    taskNote=task_note,
                    pet=target_pet,
                    recurrence=None if recurrence_choice == "none" else recurrence_choice,
                )
            )
    with col_clear:
        if st.button("Clear all tasks"):
            for p in pets:
                p.tasks.clear()
            st.session_state.pop("plan", None)

    st.markdown("#### Current tasks")
    if any(p.tasks for p in pets):
        for pet in pets:
            if not pet.tasks:
                continue
            st.markdown(f"**{pet.petName or 'Unnamed pet'}**")
            # Snapshot: completing a recurring task appends to pet.tasks, and we
            # don't want to mutate the list we're iterating.
            for task in list(pet.tasks):
                done_col, label_col, prio_col, repeat_col = st.columns(
                    [0.12, 0.5, 0.18, 0.2]
                )
                with done_col:
                    checked = st.checkbox(
                        "done",
                        value=task.completed,
                        # task.uid is stable; id() would be recycled after a
                        # task is cleared, letting a new task inherit stale state.
                        key=f"done_{task.uid}",
                        label_visibility="collapsed",
                    )
                with label_col:
                    title = (
                        f"~~{task.taskType}~~" if task.completed
                        else f"**{task.taskType}**"
                    )
                    st.write(f"{title} — {task.duration} min")
                    if task.taskNote:
                        st.caption(task.taskNote)
                with prio_col:
                    st.write(f"priority {task.priority}")
                with repeat_col:
                    st.write(_recurrence_badge(task))

                # Reconcile the checkbox with the model. markComplete() is a
                # no-op if already done, so this only fires on a real
                # not-done -> done transition.
                if checked and not task.completed:
                    spawned = task.markComplete()
                    if spawned is not None:
                        st.session_state.last_spawn = (
                            f"Completed '{task.taskType}' for {pet.petName} — "
                            f"queued its next {spawned.recurrence} occurrence."
                        )
                        st.rerun()  # re-render so the new occurrence shows
                elif not checked and task.completed:
                    task.reopen()

        if st.session_state.get("last_spawn"):
            st.toast(st.session_state.pop("last_spawn"))
    else:
        st.info("No tasks yet. Add one above.")

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
    "Preferences (comma-separated task types to prioritize)", value="feeding"
)

st.divider()

# --- Build schedule ---------------------------------------------------------
st.subheader("Build Schedule")
st.caption("Calls Scheduler.generatePlan() with every pet's pending tasks.")

schedule_date = st.date_input("Schedule date")

# Aggregate pending tasks across all pets via the Owner's filtering method.
owner = Owner(ownerName=owner_name)
for pet in st.session_state.pets:
    owner.addPet(pet)
pending = owner.pendingTasks()

st.markdown("#### 🔔 Still to do today")
if pending:
    st.warning(f"{len(pending)} task(s) not done yet:")
    for task in pending:
        st.write(
            f"- **{task.pet.petName}** — {task.taskType} "
            f"({task.duration} min) {_recurrence_badge(task)}"
        )
else:
    st.success("All caught up — nothing pending. 🎉")

if st.button("Generate schedule"):
    if not pending:
        st.warning("No pending tasks to schedule. Add some (or un-check completed ones).")
        st.session_state.pop("plan", None)
    elif not st.session_state.slots:
        st.warning("Add at least one availability slot before generating.")
        st.session_state.pop("plan", None)
    else:
        preferences = [p.strip() for p in preferences_str.split(",") if p.strip()]

        scheduler = Scheduler(scheduleDate=str(schedule_date))
        unplaced = scheduler.generatePlan(
            pending, list(st.session_state.slots), preferences
        )

        # Stash the result so it survives later reruns (e.g. ticking a checkbox).
        st.session_state.plan = {
            "date": scheduler.scheduleDate,
            "rows": [
                {
                    "Time": scheduled.scheduleTime,
                    "Pet": scheduled.task.pet.petName,
                    "Task": scheduled.task.taskType,
                    "Duration (min)": scheduled.task.duration,
                    "Priority": scheduled.task.priority,
                    "Repeats": _recurrence_badge(scheduled.task),
                    "Why": scheduled.reason,
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
    if plan["rows"]:
        st.table(plan["rows"])
    else:
        st.info("No tasks could be placed. Check your availability slots.")
    for warning in plan.get("conflicts", []):
        st.warning(f"⚠ {warning}")
    if plan["unplaced"]:
        st.warning(
            f"{len(plan['unplaced'])} task(s) had no available slot: "
            + ", ".join(plan["unplaced"])
        )
