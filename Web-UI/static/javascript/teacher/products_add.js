
document.addEventListener("DOMContentLoaded", () => {
    var shop_id = new URLSearchParams(window.location.search).get("shop");
    const dragArea = document.querySelector(".drag-area");
    const fileInput = dragArea.querySelector('input[type="file"]');
    const button = dragArea.querySelector("button");
    let uploadedImageBase64; // Variable zum Speichern vom base64 encoded img

    // Heilfsfunktion zum updaten der drag area ansicht
    function updateDragArea(file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.src = event.target.result;
        img.onload = () => {
          dragArea.innerHTML = "";
          dragArea.appendChild(img);
          dragArea.classList.add("uploaded");
          uploadedImageBase64 = event.target.result; // speichern von base64 encoded img
        };
      };
      reader.readAsDataURL(file);
    }

    // drag and drop
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dragArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    // active class hinzufügen
    ["dragenter", "dragover"].forEach((eventName) => {
      dragArea.addEventListener(
        eventName,
        () => dragArea.classList.add("active"),
        false
      );
    });

    // entfernen von active class
    ["dragleave", "drop"].forEach((eventName) => {
      dragArea.addEventListener(
        eventName,
        () => dragArea.classList.remove("active"),
        false
      );
    });

    // img hochladen
    dragArea.addEventListener("drop", (event) => {
      const file = event.dataTransfer.files[0];
      if (file) {
        updateDragArea(file);
      }
    });

    // klicken zum Auswählen von img
    button.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (file) {
        updateDragArea(file);
      }
    });

    const productForm  = document.querySelector("#product-info-form"); 
    const cancelButton = document.querySelector("#cancel-button"); 

    productForm.addEventListener("submit", submitProduct);
    cancelButton.addEventListener("click", cancelAdding);

    // hinzufügen von Produkt
    function submitProduct(ev) {
      ev.preventDefault();

      let price_str = document.querySelector("#price + .form-control").value;
      if (!price_str.includes(".") && !price_str.includes(",")) {
        price_str += ".00";
      }
      let price = price_str.replace(".", "").replace(",", "") - 0;

      // speichern von Produktinfo
      const productInfo = {
        name: document.querySelector("#name + .form-control").value,
        category: document.querySelector("#categories").value,
        itemNumber: document.querySelector("#item-number + .form-control").value,
        description: document.querySelector("#decription + .form-control").value,
        price: price,
        manufacturer: document.querySelector("#manufacturer + .form-control")
          .value,
      };
      
      if (uploadedImageBase64){
        let img = uploadedImageBase64.split("base64,")[1];
        let img_sz_mb = img.length * 3 / 4 / 1024 / 1024;
        if (img_sz_mb > 3) {
          if (!confirm("You're about to upload an image of size "+ Math.round(img_sz_mb * 10) / 10 + "MiB. Are you sure that you want to burden your students' bandwidth with this rather large file?")) {
            return;
          }
        }

        productInfo.image = img;
      }

      sendProductInfo(productInfo);
    }

    // sendet Produktinfo an den Server
    function sendProductInfo(productInfo) {
      console.log("Sending product info:", productInfo);

      fetch("/products/add?shop=" + shop_id, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(productInfo),
      })
        .then(response => response.json())
        .then(data => {
          if (data.status !== "success") {
            throw data.message;
          }
          console.log("Success:", data);
          alert(data["message"]);
          window.location.href = "/products?shop=" + shop_id;
        })
        .catch(error => {
          console.error("Error:", error);
          alert("Es ist ein Fehler aufgetreten: " + error);
        });
    }

    function cancelAdding(ev) {
      ev.preventDefault();
      console.log("Adding cancelled");
       // Leitet den Benutzer zur Seite '/products?shop=<id>' weiter
      window.location.href = "/products?shop=" + shop_id;
    }
  });

