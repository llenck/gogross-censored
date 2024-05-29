document.addEventListener("DOMContentLoaded", function () {
    let sidebar = document.querySelector(".sidebar");
    let layout = document.querySelector(".layout");
  
    // Initialisiere das padding basierend auf local storage
    if (localStorage.getItem("isPadding") === "false") {
      layout.style.paddingLeft = "108px";
    }
  
    sidebar.addEventListener("mouseover", function () {
      layout.style.paddingLeft = "250px";
    });
  
    sidebar.addEventListener("mouseout", function () {
      layout.style.paddingLeft = "108px";
    });
  
    // Setze das padding auf 108px, wenn ein Link in der Sidebar geklickt wird
    document.querySelectorAll(".menu a").forEach(function (link) {
      link.addEventListener("click", function () {
        layout.style.paddingLeft = "108px";
        localStorage.setItem("isPadding", "false");
      });
    });
  });
  