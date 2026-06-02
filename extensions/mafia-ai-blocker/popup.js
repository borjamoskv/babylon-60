document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['obfuscatedCount'], (result) => {
        if (result.obfuscatedCount !== undefined) {
            document.getElementById('blockCount').innerText = result.obfuscatedCount;
        }
    });
});
