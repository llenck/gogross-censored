// changesMade wird auf true gesetzt, wenn Änderungen an den Kategorien vorgenommen werden
let changesMade = false;
// Array für gelöschte Kategorien
let deletedCategories = [];

let shop_id = new URLSearchParams(window.location.search).get("shop");

function markChangesMade() {
  changesMade = true;
}

// Kategorie löschen und sofort im HMTL entfernen
function deleteCategory(category) {
  var elem = document.getElementById(category);
  if (elem) {
    elem.parentNode.removeChild(elem);
    deletedCategories.push(category);
    markChangesMade();
  }
}

// Popup für neue Kategorie anzeigen
document
  .getElementById("addCategoryBtn")
  .addEventListener("click", function () {
    document.getElementById("popup").style.display = "block";
  });

// Neue Kategorie speichern
function saveNewCategory() {
  var newCategory = document.getElementById("newCategoryName").value;
  if (newCategory) {

    // neue li-Element erstellen
    var li = document.createElement("li");
    li.id = newCategory;
    li.textContent = newCategory + " ";

    var deleteButton = document.createElement("button");

    // Icon für den Button erstellen
    var icon = document.createElement("i");
    icon.className = "fa-solid fa-trash-can";
    icon.style.color = "#161a30";

    // Icon zum Button hinzufügen
    deleteButton.appendChild(icon);

    
    deleteButton.onclick = function () {
      deleteCategory(newCategory);
    };

    // Button zum li-Element hinzufügen
    li.appendChild(deleteButton);

    document.getElementById("categoryList").appendChild(li);
    markChangesMade();
    cancelNewCategory(); // Popup schließen
  }
}

// Popup abbrechen
function cancelNewCategory() {
  document.getElementById("newCategoryName").value = "";
  document.getElementById("popup").style.display = "none";
}

// Änderungen speichern
function submitCategories() {
  var categories = [];
  document
    .getElementById("categoryList")
    .querySelectorAll("li")
    .forEach(function (item) {
      categories.push(item.textContent.trim().replace("Delete", "").trim()); // Kategorie ohne 'Delete' und Leerzeichen speichern
    });

  console.log("Gespeicherte Kategorien:", categories);

  // Wenn Änderungen vorgenommen wurden und deleted categories bestätigt wurden, wird ein POST-Request an den Server gesendet
  if (changesMade) {
    let shouldProceed = true;

    if (deletedCategories.length > 0) {
      const confirmationMessage = `Are you sure to delete these categories: ${deletedCategories.join(
        ", "
      )}? This will cause that the products in these categories will also be removed.`;
      shouldProceed = confirm(confirmationMessage); // Zeigt den Bestätigungsdialog an und speichert die Benutzerwahl
    }

    if (shouldProceed) {
      // Der Benutzer hat auf "OK" geklickt oder es gab nichts zu bestätigen
      fetch("/category-management?shop=" + shop_id, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ categories: categories }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Success:", data);
          alert("Categories updated successfully!");
          window.location.href = "/products?shop=" + shop_id;
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("An error occured. Please try again or ask a developer for help :)");
        });
    } else {
      // Der Benutzer hat auf "Cancel" geklickt
      console.log("Category update cancelled by the user.");
    }
  } else {
    // Wenn keine Änderungen vorgenommen wurden, wird der Benutzer zur Seite '/products' weitergeleitet
    window.location.href = "/products?shop=" + shop_id;
  }
}

function cancelChanges() {
  if (changesMade) {
    alert("Category change canceled!");
    // Setzt das Flag zurück, da die Änderungen jetzt verworfen werden
    changesMade = false;
  }
  // Leitet den Benutzer zur Seite '/products?shop=<id>' weiter
  window.location.href = "/products?shop=" + shop_id;
}
