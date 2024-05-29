document.addEventListener("DOMContentLoaded", () => {
  const dragArea = document.querySelector(".drag-area");
  const fileInput = dragArea.querySelector('input[type="file"]');
  const button = dragArea.querySelector("button");
  let uploadedImageBase64;


  function updateDragArea(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      img.onload = () => {
        dragArea.innerHTML = "";
        dragArea.appendChild(img);
        dragArea.classList.add("uploaded");
        uploadedImageBase64 = event.target.result;
      };
    };
    reader.readAsDataURL(file);
  }

  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dragArea.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    dragArea.addEventListener(
      eventName,
      () => dragArea.classList.add("active"),
      false
    );
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dragArea.addEventListener(
      eventName,
      () => dragArea.classList.remove("active"),
      false
    );
  });

  dragArea.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) {
      updateDragArea(file);
    }
  });

  button.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) {
      updateDragArea(file);
    }
  });

  const vendorForm = document.querySelector("#vendor-info-form");
  const cancelButton = document.querySelector("#cancel-button");

  vendorForm.addEventListener("submit", submitVendor);
  cancelButton.addEventListener("click", cancelAdding);

  // sendet die Produktinformationen an den Server

  function submitVendor(ev) {
    ev.preventDefault();

    let skonto_str = document.querySelector("#skonto + .form-control").value;
    if (!skonto_str.includes(".") && !skonto_str.includes(",")) {
      skonto_str += ".0";
    }
    let skonto = skonto_str.replace(".", "").replace(",", "").replace("%", "") - 0;

    const vendorInfo = {
      name: document.querySelector("#name + .form-control").value,
      iban: document.querySelector("#iban + .form-control").value,
      invoice_notes: document.querySelector("#invoice_notes + .form-control")
        .value,
      skonto: skonto,
      skonto_period: document.querySelector("#skonto-period + .form-control").value,
    };

    if (uploadedImageBase64){
      let img = uploadedImageBase64.split("base64,")[1];
      let img_sz_mb = img.length * 3 / 4 / 1024 / 1024;
      if (img_sz_mb > 3) {
        if (!confirm("You're about to upload an image of size "+ Math.round(img_sz_mb * 10) / 10 + "MiB. Are you sure that you want to burden your students' bandwidth with this rather large file?")) {
          return;
        }
      }
      
      vendorInfo.img = img;
    }

    sendVendorInfo(vendorInfo);
  }


  // Funktion zum Senden der Produktinformationen an den Server

  function sendVendorInfo(vendorInfo) {
    console.log("Sending Shop info:", vendorInfo);

    fetch("/administration/add-vendor", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(vendorInfo),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status !== "success") {
          throw data.message;
        }
        console.log("Success:", data);
        //alert("Shop added successfully!"); Wird schon ausgegeben
        window.location.href = "/administration";
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("Es ist ein Fehler aufgetreten: " + error);
      });
  }

  function cancelAdding(ev) {
    ev.preventDefault();
    console.log("Adding cancelled");
    window.location.href = "/administration";
  }
});
