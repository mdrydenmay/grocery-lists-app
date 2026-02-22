// Grocery List View Toggle
function showView(view) {
    const categoryView = document.getElementById('category-view');
    const storeView = document.getElementById('store-view');
    const buttons = document.querySelectorAll('.view-toggle .btn');

    if (view === 'store') {
        categoryView.style.display = 'none';
        storeView.style.display = 'grid';
    } else {
        categoryView.style.display = 'grid';
        storeView.style.display = 'none';
    }

    buttons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(view)) {
            btn.classList.add('active');
        }
    });
}

// Copy grocery list to clipboard (for Google Keep)
function copyToClipboard() {
    const textArea = document.getElementById('clipboard-text');
    if (!textArea) return;

    // Get the text and clean it up
    let text = textArea.value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line)
        .join('\n');

    navigator.clipboard.writeText(text).then(() => {
        // Show feedback
        const btn = document.querySelector('button[onclick="copyToClipboard()"]');
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('btn-secondary');
        btn.classList.remove('btn-primary');

        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

// Toggle inline name edit form
function toggleNameEdit(id) {
    var el = document.getElementById('name-edit-' + id);
    if (el) {
        el.style.display = el.style.display === 'none' ? 'block' : 'none';
    }
}

// Save checkbox state to localStorage
document.addEventListener('DOMContentLoaded', function() {
    const checkboxes = document.querySelectorAll('.grocery-checkbox');
    const weekStart = new URLSearchParams(window.location.search).get('week') || 'current';
    const storageKey = `grocery-${weekStart}`;

    // Load saved state
    const savedState = JSON.parse(localStorage.getItem(storageKey) || '{}');

    checkboxes.forEach((checkbox, index) => {
        // Restore state
        if (savedState[index]) {
            checkbox.checked = true;
        }

        // Save on change
        checkbox.addEventListener('change', function() {
            const state = {};
            checkboxes.forEach((cb, i) => {
                if (cb.checked) state[i] = true;
            });
            localStorage.setItem(storageKey, JSON.stringify(state));
        });
    });
});

// Flash message auto-dismiss
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transition = 'opacity 0.5s';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });
});
