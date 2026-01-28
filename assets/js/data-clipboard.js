async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        alert(`Text copied to clipboard: ${text}`);
    } catch (err) {
        alert(`Failed to copy text: ${err}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-clipboard]').forEach((el) => {
        el.addEventListener('click', (e) => {
            e.preventDefault();

            copyToClipboard(el.getAttribute('data-clipboard'));
        })
    })
})