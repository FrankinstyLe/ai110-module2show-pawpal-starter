# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- A pet care system to track owner's caring activities for their pets. User should be able to add pet's name, preferences, and availabilities. The app then will suggest, keep track of activities for the pet(s) accordingly.
- There will be 4 classes: 
    - Owner: include onwerName(str), can addPet(), addTime(), addPreferences(). Can have multiple pets and activities.
    - Pet: include petName(str), breed(str), petAge(int), specialNote(str). Can have multiple activities and preferences.
    - Task: include taskType(str), priority(int), duration(int), taskNote(str). Can have multiple tasks and preferences.
    - Scheduler: include scheduleDate(str), scheduleTime(str), scheduleTask(Task). Can have multiple schedules and tasks.

**b. Design changes**

Yes, my design changed in a few important ways as I re-read the requirements and started building the class skeleton.


1. **Preferences belong to the Owner, not the Pet.** I briefly moved `preferences` onto `Pet`, but the README describes them as *owner* preferences (a scheduling constraint), so I moved them back to `Owner` alongside `availability`.

2. **Added a `ScheduledTask` class instead of storing the plan in dictionaries.** I originally planned to store each task's time and reason in `dict[Task, str]` maps on `Scheduler`. This does not work in Python: dictionary keys must be hashable, but a mutable `@dataclass` (Task) is not hashable, so using a Task as a key raises `TypeError`. So AI recommended to introduce a small `ScheduledTask` class holding `scheduleTime`, `task`, and `reason`, and `Scheduler.plannedTasks` is now a list of these. This keeps tasks editable, avoids keeping several parallel maps in sync, and maps cleanly to the respected output.

3. **A Task now belongs to a Pet.** To capture the "a pet has many tasks" relationship in code, I added a `pet` reference on `Task` so every task is tied to the pet it is for.

4. **`generatePlan()` returns the tasks it could not place.** Rather than silently dropping tasks when availability runs out, the scheduler returns the unplaced tasks so the UI can surface conflicts to the user.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- My scheduler considers time, priority, and preferences.
- I decided that preference constraints are more important than priority. 

**b. Tradeoffs**

- One tradeoff I made was to prioritize preference constraints over task priority. This means that even if a task has a higher priority, it will not be scheduled if it violates the owner's preferences.
- This is because the owner may have specific needs for their pet that must be respected, and violating those preferences could lead to negative outcomes for the pet's well-being.

---

## 3. AI Collaboration

**a. How you used AI**

- I used AI to help me brainstorm the initial design and to generate code snippets for the classes and methods. I also used AI to help me debug issues and to suggest improvements to my code.
- The kind of prompts I used were mostly descriptive, asking the AI to generate code based on my design and to explain how to implement certain features.

**b. Judgment and verification**

- AI's suggestions were mostly helpful, but it tended to leave a flagged issues at the end of the suggestions. Based on that and my desired design, I had to steer it away from the rabbit hole or continue with the suggestions.
- I verified the AI's suggestions by running tests and checking the output against my expectations. I also reviewed the code to ensure it met my design requirements and made adjustments as needed.
---

## 4. Testing and Verification

**a. What you tested**

- The behaviors I tested were the scheduling logic, including the handling of constraints and priorities, as well as the generation of the daily plan. I also tested the ability to add and edit tasks, and to mark tasks as complete.
- They were important because they ensured that the core functionality of the app was working as expected and that the scheduling logic was producing valid plans.

**b. Confidence**

- 4
- I would test maximum of pets and tasks to see if the app can handle large inputs. I would also test where recurring tasks are scheduled correctly and that the next occurrence is queued properly.

---

## 5. Reflection

**a. What went well**

- Finishing it

**b. What you would improve**

- Rework the system design and its logic to be more efficient and scalable.

**c. Key takeaway**

- Working with AI without having a domain knowledge of the problem can be challenging. It is important to have a clear understanding of the requirements and constraints before starting to design and implement the system. It also cost me a lot of time and tokens to debug and fix issues that arose from AI's suggestions, so I learned to be more careful and critical when using AI for code generation.
