document.getElementById("updateButton").addEventListener("click", async () => {   
    const getValueOrDefault = (id, defaultValue) => {
        const val = document.getElementById(id).value.trim();
        return val === "" ? defaultValue : val;
    }; 
    const data = {
        calories: parseFloat(getValueOrDefault("calories", 0)),
        protein: parseFloat(getValueOrDefault("protein", 0)),
        carbs: parseFloat(getValueOrDefault("carbs", 0)),
        fat: parseFloat(getValueOrDefault("fat", 0)),
        allergies: getValueOrDefault("allergies", "none"),
        height: parseFloat(getValueOrDefault("height", 0)),
        weight: parseFloat(getValueOrDefault("weight", 0)),
        hated_ingredients: getValueOrDefault("hated_ingredients", "")
    };

    const response = await fetch("/updateUserStats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: 'same-origin'
    });

    if (response.ok) {
        alert("Profile updated successfully!");
    } else {
        alert("Failed to update profile.");
    }
});


