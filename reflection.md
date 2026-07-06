# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- A pet care system to track owner's caring activites for their pets. User should be able to add pet's name, preferences, and availabilities. The app then will suggest, keep track of activities for the pet(s) accordingly.
- There will be 4 classes: 
    - Owner: include onwerName(str), can addPet(), addTime(), addPreferences(). Can have multiple pets and activities.
    - Pet: include petName(str), breed(str), petAge(int), specialNote(str). Can have multiple activities and preferences.
    - Task: include taskType(str), priority(int), duration(int), taskNote(str). Can have multiple tasks and preferences.
    - Schedule: include scheduleDate(str), scheduleTime(str), scheduleTask(Task). Can have multiple schedules and tasks.

**b. Design changes**

Yes, my design changed in a few important ways as I re-read the requirements and started building the class skeleton.


1. **Preferences belong to the Owner, not the Pet.** I briefly moved `preferences` onto `Pet`, but the README describes them as *owner* preferences (a scheduling constraint), so I moved them back to `Owner` alongside `availability`.

2. **Added a `ScheduledTask` class instead of storing the plan in dictionaries.** I originally planned to store each task's time and reason in `dict[Task, str]` maps on `Schedule`. This does not work in Python: dictionary keys must be hashable, but a mutable `@dataclass` (Task) is not hashable, so using a Task as a key raises `TypeError`. So AI recommended to introduce a small `ScheduledTask` class holding `scheduleTime`, `task`, and `reason`, and `Schedule.plannedTasks` is now a list of these. This keeps tasks editable, avoids keeping several parallel maps in sync, and maps cleanly to the repected output.

3. **A Task now belongs to a Pet.** To capture the "a pet has many tasks" relationship in code, I added a `pet` reference on `Task` so every task is tied to the pet it is for.

4. **`generatePlan()` returns the tasks it could not place.** Rather than silently dropping tasks when availability runs out, the scheduler returns the unplaced tasks so the UI can surface conflicts to the user.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
