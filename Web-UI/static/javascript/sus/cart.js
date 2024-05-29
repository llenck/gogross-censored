window.addEventListener("pageshow", event => {
    const entries = performance.getEntriesByType("navigation");
    try {
        if (entries[entries.length - 1].type === "back_forward") {
            window.location.reload();
        }
    } catch(e) {
        console.log(e);
    }
});
