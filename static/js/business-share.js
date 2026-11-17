const shareButton = document.getElementById("mgr-share");
shareButton?.addEventListener("click", async () => {
    const url = new URL(shareButton.dataset.public, location.origin).href;
    const status = document.getElementById("mgr-copy-status");
    try {
        if (navigator.share) {
            await navigator.share({url, title: document.title});
        } else {
            await navigator.clipboard.writeText(url);
            status.textContent = "Enlace copiado.";
        }
    } catch (error) {
        if (error.name !== "AbortError") status.textContent = url;
    }
});
