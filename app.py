import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

Enter info about the owner, pet, and tasks below, then generate a care plan for the day.
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
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# Priority is a string in the UI but an int in the model, where a *lower*
# number means more urgent (see Scheduler.generatePlan). high -> 1 (most urgent).
PRIORITY_TO_INT = {"high": 1, "medium": 2, "low": 3}

st.subheader("Owner & Pet")
owner_name = st.text_input("Owner name", value="Jordan")

col_pet1, col_pet2 = st.columns(2)
with col_pet1:
    pet_name = st.text_input("Pet name", value="Mochi")
    breed = st.text_input("Breed", value="Shiba Inu")
with col_pet2:
    pet_age = st.number_input("Pet age (years)", min_value=0, max_value=50, value=3)
    species = st.selectbox("Species", ["dog", "cat", "other"])
special_note = st.text_input("Special note", value="")

st.markdown("### Availability & Preferences")
st.caption(
    "Availability = time slots for the day (one task per slot). "
    "Preferences = task types to prioritize (matched against a task's title)."
)
col_ap1, col_ap2 = st.columns(2)
with col_ap1:
    availability_str = st.text_input(
        "Availability slots (comma-separated)", value="Morning, Afternoon, Evening"
    )
with col_ap2:
    preferences_str = st.text_input(
        "Preferences (comma-separated task types)", value="Morning walk"
    )

st.markdown("### Tasks")
st.caption("Add a few tasks. These feed into the scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

task_note = st.text_input("Task note", value="")

col_add, col_clear = st.columns(2)
with col_add:
    if st.button("Add task"):
        st.session_state.tasks.append(
            {
                "title": task_title,
                "duration_minutes": int(duration),
                "priority": priority,
                "note": task_note,
            }
        )
with col_clear:
    if st.button("Clear tasks"):
        st.session_state.tasks = []

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Calls Scheduler.generatePlan() using the inputs above.")

schedule_date = st.date_input("Schedule date")

if st.button("Generate schedule"):
    if not st.session_state.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        # Build the object model from the UI inputs.
        pet = Pet(
            petName=pet_name,
            breed=breed,
            petAge=int(pet_age),
            specialNote=special_note,
        )
        owner = Owner(ownerName=owner_name)
        owner.addPet(pet)

        for item in st.session_state.tasks:
            task = Task(
                taskType=item["title"],
                priority=PRIORITY_TO_INT.get(item["priority"], 2),
                duration=int(item["duration_minutes"]),
                taskNote=item.get("note", ""),
                pet=pet,
            )
            owner.addTask(task)

        availability = [s.strip() for s in availability_str.split(",") if s.strip()]
        preferences = [p.strip() for p in preferences_str.split(",") if p.strip()]

        scheduler = Scheduler(scheduleDate=str(schedule_date))
        unplaced = scheduler.generatePlan(
            owner.pendingTasks(), availability, preferences
        )

        st.success(f"Plan for {scheduler.scheduleDate}")

        if scheduler.plannedTasks:
            plan_rows = [
                {
                    "Time": scheduled.scheduleTime,
                    "Task": scheduled.task.taskType,
                    "Duration (min)": scheduled.task.duration,
                    "Priority": scheduled.task.priority,
                    "Why": scheduled.reason,
                }
                for scheduled in scheduler.plannedTasks
            ]
            st.table(plan_rows)
        else:
            st.info("No tasks could be placed. Check your availability slots.")

        if unplaced:
            st.warning(
                f"{len(unplaced)} task(s) had no available slot: "
                + ", ".join(task.taskType for task in unplaced)
            )
