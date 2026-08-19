const habitInput = document.getElementById("habitInput");
const addHabitBtn = document.getElementById("addHabit");
const habitList = document.getElementById("habitList");
const progressBar = document.getElementById("progress");
const progressText = document.getElementById("progressText");
const themeToggle = document.getElementById("themeToggle");

let habits = JSON.parse(localStorage.getItem("habits")) || [];

function updateProgress() {
    let completed = habits.filter(h => h.completed).length;
    let total = habits.length;
    let percent = total ? Math.round((completed / total) * 100) : 0;
    progressBar.style.width = percent + "%";
    progressText.textContent = `${percent}% completed`;
}

function saveHabits() {
    localStorage.setItem("habits", JSON.stringify(habits));
}

function renderHabits() {
    habitList.innerHTML = "";
    habits.forEach((habit, index) => {
        let li = document.createElement("li");
        li.className = habit.completed ? "completed" : "";

        let checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = habit.completed;
        checkbox.addEventListener("change", () => {
            habits[index].completed = checkbox.checked;
            saveHabits();
            updateProgress();
            renderHabits();
        });

        let span = document.createElement("span");
        span.textContent = habit.name;

        let deleteBtn = document.createElement("button");
        deleteBtn.textContent = "❌";
        deleteBtn.classList.add("delete-btn");
        deleteBtn.addEventListener("click", () => {
            habits.splice(index, 1);
            saveHabits();
            updateProgress();
            renderHabits();
        });

        li.appendChild(checkbox);
        li.appendChild(span);
        li.appendChild(deleteBtn);
        habitList.appendChild(li);
    });
    updateProgress();
}

addHabitBtn.addEventListener("click", () => {
    if (habitInput.value.trim() === "") return;
    habits.push({ name: habitInput.value, completed: false });
    habitInput.value = "";
    saveHabits();
    renderHabits();
});

themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark");
    themeToggle.textContent = document.body.classList.contains("dark") ? "☀ Light Mode" : "🌙 Dark Mode";
});

renderHabits();
const languageSelect = document.getElementById('languageSelect');
languageSelect.addEventListener('change', (e) => {
    const lang = e.target.value;
    console.log(`Language switched to: ${lang}`);
    // Future: Load translations dynamically based on language
});



// 🗓️ Show Current Date
const currentDate = document.getElementById('currentDate');
currentDate.textContent = new Date().toDateString();

// 🌗 Theme Toggle
const themeToggle = document.getElementById('themeToggle');
themeToggle.addEventListener('click', () => {
  document.body.classList.toggle('dark');
  themeToggle.textContent = document.body.classList.contains('dark') ? '☀️ Light Mode' : '🌙 Dark Mode';
});

// 🌐 Language Select
const languageSelect = document.getElementById('languageSelect');
languageSelect.addEventListener('change', (e) => {
  alert(`Language changed to: ${e.target.value}`);
});

// 🔍 Simple Goal Search (example)
const searchGoal = document.getElementById('searchGoal');
const achievements = document.getElementById('Achievements');
searchGoal.addEventListener('input', () => {
  const filter = searchGoal.value.toLowerCase();
  [...achievements.children].forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(filter) ? '' : 'none';
  });
});
