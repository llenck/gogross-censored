document.addEventListener("DOMContentLoaded", () => {
    const shop_id = new URLSearchParams(window.location.search).get("shop");
    const iban = document.getElementById("iban");

    const productForm  = document.querySelector("#vendor-iban-change");
    const cancelButton = document.querySelector("#cancel-button");

    productForm.addEventListener("submit", submitProduct);
    cancelButton.addEventListener("click", cancelAdding);

    function submitProduct(ev) {
        ev.preventDefault();

        const productInfo = {
            iban: iban.value
        };

        sendProductInfo(productInfo)
            .then(() => {
                console.log("Success: Iban changed successfully");
                //alert("Iban changed successfully!"); Wird schon ausgegeben
                window.location.href = "/administration";
            })
            .catch(error => {
                console.error("Error:", error);
                alert("Es ist ein Fehler aufgetreten: " + error);
            });
    }

    function sendProductInfo(productInfo) {
        console.log("Sending new iban:", productInfo);

        return fetch("/administration/change_iban?shop=" + shop_id, {
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
            });
    }

    function cancelAdding(ev) {
        ev.preventDefault();
        console.log("Adding cancelled");
        window.location.href = "/administration";
    }
});