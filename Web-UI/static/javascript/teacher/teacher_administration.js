/*----Deeplink URL, Clipboard copy und Popup----*/
function importShop() {
    /*----JSON-File aus File Upload---*/
    var inputFile = document.getElementById("vendor-jsonFile");
    var shopFile = inputFile.files[0];

    /*----POST request mit JSON Datei mittels Fetch API---*/
    if(shopFile) {
        fetch("/administration/import-vendor", {
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
            },
            body: shopFile
        })
        /*----Server Anwort handling---*/
        .then(response => response.json())
        .then(data => {
            if (data.status !== "success") {
                throw data.message;
            }
            alert(data.message);
            window.location.reload();
        })
        .catch(error => {
             console.error("Error:", error);
             alert(error);
        });
    }
}

/*---Shop löschen Funktion, send JSON mit entsprechender ShopID----*/
function deleteVendor(vendorID) {
    /*----ShopID des zu löschenden Shops---*/
    var deleteShop = {vendor_id: vendorID};

    /*----POST request als JSON mit ShopID---*/
    fetch("/administration/delete-vendor", {
        method: "POST",
        headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(deleteShop)
    })
    /*----Server Anwort handling---*/
    .then(response => response.json())
    .then(data => {
        if (data.status !== "success") {
            throw data.message;
        }
        location.reload()
    })
}

/*----Delete Account Funktionen---*/
/*----Delete Account, POST request---*/
function submitDeleteAcc() {
        fetch("/administration/delete", {
        method: "POST"         
        })
        /*----Server Antwort handling---*/
        .then(response => response.json())
        .then(data => {
            if(data.status !== "success") {
                throw data.message;
                document.getElementById("submit-cancel").style.display = "none";
            }
            else {
                location.reload();
                throw data.message;
            }
        })

}
           
/*----ExportDownload--*/
function exportVendor(url) {
    if (url) {
        fetch(url)
        .then(res => {
            if (!res.ok) {
                throw new Error("Cant access Site");
            }
            return res.json();
        })
        .then(jsonRes => {
            var exortedVendorFile = new Blob([JSON.stringify(jsonRes, null, 2)], {type: "application/json" });
            var link = document.createElement("a");
            link.href = URL.createObjectURL(exortedVendorFile);
            link.download = "exported_vendor.json";
            link.click()
        })
        .catch(error => {
            console.error('Fetch error:', error);
        });
    }
}
