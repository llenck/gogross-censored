document.addEventListener("DOMContentLoaded", () => {
    const shop_id = new URLSearchParams(window.location.search).get("shop");
    const iban = document.getElementById("iban");

    const productForm  = document.querySelector("#vendor-iban-change");
    const skontoperiod  = document.querySelector("#skonto-period");
    const cancelButton = document.querySelector("#cancel-button");

    productForm.addEventListener("submit", submitProduct);
    skontoperiod.addEventListener("submit", submitProduct);
    cancelButton.addEventListener("click", cancelAdding);

    function submitProduct(ev) {
        ev.preventDefault();

        let discount_str = document.querySelector("#discount + .form-control").value;
        if (!discount_str.includes(".") && !discount_str.includes(",")) {
            discount_str += ".0";
        }

        let discount = discount_str.replace(".", "").replace(",", "").replace("%", "") - 0;
        
        const productInfo = {
            discount: discount,
            skonto_period: skonto_period.value
        };

        console.log(productInfo)
        sendProductInfo(productInfo)
            .then(() => {
                console.log("Success: Iban changed successfully");
                //alert("Discount changed successfully!"); Wird schon ausgegeben
                window.location.href = "/administration";
            })
            .catch(error => {
                console.error("Error:", error);
                alert("Es ist ein Fehler aufgetreten: " + error);
            });
    }

    function sendProductInfo(productInfo) {
        console.log("Sending new Discount:", productInfo);

        return fetch("/administration/change_discount?shop=" + shop_id, {
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