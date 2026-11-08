const eaten = window.eaten;
const goals = window.goals;
const activities = window.activities;

function renderNutrition() {
    const nutritionList = document.getElementById('nutrition-list');
    nutritionList.innerHTML = "";

    const rem = window.remaining || {calories:0, protein:0, carbs:0, fat:0};
    const remainingLi = document.createElement('li');
    remainingLi.className = "sum";
    remainingLi.innerHTML = `<b>Remaining today:</b>
      ${rem.calories} kcal | ${rem.protein}g Protein | ${rem.carbs}g Carbs | ${rem.fat}g Fat`;
    nutritionList.appendChild(remainingLi);
}


// Activities summary
function renderActivities() {
    const activityList = document.getElementById('activity-list');
    activityList.innerHTML = "";

    let totalCalories = 0;
    activities.forEach(item => {
        totalCalories += item.calories_burned || 0;
        const li = document.createElement('li');
        li.innerHTML = `<span class="entry-title">${item.activity}</span>
        <span class="entry-detail">${item.calories_burned} kcal burned</span>`;
        activityList.appendChild(li);
    });

    // Show total calories burned
    if (activities.length) {
        const sumLi = document.createElement('li');
        sumLi.className = "sum";
        sumLi.innerHTML = `<b>Total burned:</b> ${totalCalories} kcal`;
        activityList.prepend(sumLi);
    }
}

renderNutrition();
renderActivities();
