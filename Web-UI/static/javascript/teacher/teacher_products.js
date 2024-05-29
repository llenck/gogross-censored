/* ----Gibt die ShopID des aktuell ausgewählten Shops wieder---- */
function saveShopID() {
    var queryString = window.location.search; /**/
    var params = new URLSearchParams(queryString);

    return params.get('shop')
}

/* ----Shopabhängige Elemente werden sichtbar nach Shopauswahl---- */
if (saveShopID() != null) {
    document.getElementById("hide").style.display = "block";
} else {
    document.getElementById("hide").style.display = "none";
}

function checkCat() {
    if (saveCategoryID() == null) {
        alert("Please select or create a category in which the products are to be imported")
    } else {
        console.log(saveCategoryID)
        document.getElementById('importProduct').click();
    }
}


/* ----Class header: Ausgewählter Shop wird in der Selektion angezeigt---- */
if (document.getElementById(saveShopID()) != null) {
    var shopToSelect = document.getElementById(saveShopID());
    shopToSelect.selected = true;
}


/* ----Select category-filter: Ausgewählte Kategorie wird in der Kategorie-Selektion angezeigt---- */
if (document.getElementById("cat" + saveCategoryID()) != null) {
    var categoryToSelect = document.getElementById("cat" + saveCategoryID());
    categoryToSelect.selected = true;
}


/* ----Gibt die CategoryID der aktuell ausgewählten Kategorie wieder----- */
function saveCategoryID() {
    var queryString = window.location.search;
    var params = new URLSearchParams(queryString);

    return params.get('category')
}

/* ----Kategoriefilter, Weiterleitung zu entsprechender URL mit Parametern: ShopID und KategorieID---- */
function filterCategory(id) {
    if (id == 'all-category') {
        window.location.href="/products?shop=" + saveShopID()
    } else {
        window.location.href="/products?shop=" + saveShopID() + '&category=' + id
    }
}

/* ----Kategoriemanagement, Weiterleitung zu entsprechender URL mit ShopID Parameter---- */
function navigateToCM() {
        window.location.href="/category-management?shop=" + saveShopID()
}

/* ----Add Product, Weiterleitung zu entsprechender URL mit ShopID Parameter---- */
// function navigateToAddP() {
//         window.location.href="/products/add?shop=" + saveShopID()
// }

function navToEdit(productID) {
    window.location.href="/products/edit?shop=" + saveShopID() + "&product=" + productID;
}


/* ----Produkt löschen, Parameter: CanonID und KategorieID---- */
function deleteProduct(canonID, catID) {

        /*Produkt welches gelöscht wird, ProduktID, ShopID, KategorieID*/
        var deleteData = {
            canon_id: canonID,
            vendor_id: saveShopID(),
            category: catID
        };

        /* POST request, mit JSON Datei mit dem zu löschenden Produkt */
        fetch("/products/del?shop=" + saveShopID(), {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(deleteData)
        })
        /*Erfolg Abfrage durch Antwort vom Server*/
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert("Product deleted successfully");
                location.reload();
            } else {
                alert("An error occurred while deleting the product");
                location.reload();
            }
        })
}



/* ----Import von Produkten, POST request mit JSON-File, Parameter event (File Upload Input)----- */
function importProducts(event) {

        /* File vom File-Input speichern */
        var input = event.target;
        var file = input.files[0];

        /*POST request JS Fetch API, mit uploaded file*/
        if (file) {
            fetch("/products/import?shop=" + saveShopID() + "&category=" + saveCategoryID(), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
            },
            body: file
        })
            /*Erfolg Abfrage durch Antwort vom Server*/
            .then(response => response.json())
            .then(data => {
              if (data.status !== "success") {
                location.reload();
                throw data.message;
              }
                location.reload();
                throw data.message;
            })
            .catch(error => {
              console.error("Error:", error);
              alert(error);
            });
        } else {
            alert("Please select a file to import");
        }
}


/* ----Export der ausgewählten Produkte mit anschließendem Download der JSON-Datei---- */
function exportSelectedProducts() {

        /* Start Liste, Liste mit allen Checkboxen auf der Seite*/
        var selectedProducts = [];
        var checkboxes = document.querySelectorAll('input[type="checkbox"]');

        /* Überprüft jede Checkbox ob sie ausgewählt ist, wenn ja,
        dann wird das Produkt mit seinen Attribute als Dictionary in eine Liste hinzugefügt  */
        checkboxes.forEach(function(checkbox) {
            if (checkbox.checked) {
                if (checkbox.getAttribute("picture") == '') {
                    var product = {
                        canon_id: checkbox.getAttribute("canon_id"),
                        name: checkbox.getAttribute("name"),
                        manufacturer: checkbox.getAttribute("manufacturer"),
                        description: checkbox.getAttribute("description"),
                        price: checkbox.getAttribute("price"),
                        };
                } else {
                    var product = {
                        canon_id: checkbox.getAttribute("canon_id"),
                        name: checkbox.getAttribute("name"),
                        manufacturer: checkbox.getAttribute("manufacturer"),
                        description: checkbox.getAttribute("description"),
                        price: checkbox.getAttribute("price"),
                        picture: checkbox.getAttribute("picture").slice(2, -1),
                        };
                }


                selectedProducts.push(product);
            }
        });

        /* Wenn die Liste leer ist (keine Produkte ausgewählt sind), dann alert mit keine Produkte ausgewählt.*/
        if (selectedProducts.length === 0) {
            alert("No products selected. Please select products.");
            return; // Funktion abbrechen
        }

        /* Liste wird in JSON-String Konvertiert.*/
        var jsonString = JSON.stringify(selectedProducts);

        /* Binäres Datenobjekt wird erzeugt, die den JSON-String enthält.*/
        var exported_json = new Blob([jsonString], { type: "application/json" });
        
        /* Download-Link wird erzeugt.*/
        var link = document.createElement('a');
        var currentDate = new Date().toISOString().slice(0, 10);
        link.href = window.URL.createObjectURL(exported_json);
        link.download = "exported_products_" + currentDate + ".json";
        link.click();
}