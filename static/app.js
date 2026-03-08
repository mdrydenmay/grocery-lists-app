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

// ============== Helpers ==============

function escHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function formatIngredient(ing) {
    if (ing.qty || ing.unit) {
        let html = '';
        if (ing.qty) {
            const qty = (ing.qty % 1 === 0) ? Math.round(ing.qty) : ing.qty;
            html += `<span class="ing-qty">${qty}</span> `;
        }
        if (ing.unit) html += `<span class="ing-unit">${escHtml(ing.unit)}</span> `;
        html += `<span class="ing-name">${escHtml(ing.name)}</span>`;
        return html;
    }
    return escHtml(ing.raw || ing.name);
}

// ============== Recipe Tabs ==============

const tabCache = {};    // id -> recipe data
const openTabIds = [];  // ordered list of open tab ids
let activeTabId = null;

function openRecipeTab(event, linkEl) {
    // Let Ctrl+click / Meta+click / middle-click open in a new browser tab
    if (event.ctrlKey || event.metaKey || event.button === 1) return;
    event.preventDefault();

    const recipeId = parseInt(linkEl.dataset.recipeId);
    if (tabCache[recipeId]) {
        activateTab(recipeId);
    } else {
        fetch(`/api/recipes/${recipeId}`)
            .then(r => r.json())
            .then(recipe => {
                tabCache[recipeId] = recipe;
                if (!openTabIds.includes(recipeId)) openTabIds.push(recipeId);
                renderTabBar();
                activateTab(recipeId);
            });
    }
}

function activateTab(id) {
    activeTabId = id;
    renderTabBar();
    renderTabContent(tabCache[id]);
    document.getElementById('recipe-tabs-bar').style.display = 'block';
    document.getElementById('recipe-tab-content').style.display = 'block';
    document.getElementById('recipe-tabs-bar').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeTab(id, event) {
    event.stopPropagation();
    const idx = openTabIds.indexOf(id);
    openTabIds.splice(idx, 1);
    delete tabCache[id];
    if (openTabIds.length === 0) {
        activeTabId = null;
        document.getElementById('recipe-tabs-bar').style.display = 'none';
        document.getElementById('recipe-tab-content').style.display = 'none';
    } else {
        activateTab(openTabIds[Math.min(idx, openTabIds.length - 1)]);
    }
}

function renderTabBar() {
    const tabList = document.getElementById('tab-list');
    if (!tabList) return;
    tabList.innerHTML = openTabIds.map(id => {
        const recipe = tabCache[id];
        const isActive = id === activeTabId;
        return `<div class="tab-item${isActive ? ' active' : ''}" onclick="activateTab(${id})">
            <span class="tab-title">${escHtml(recipe.title)}</span>
            <button class="tab-close" onclick="closeTab(${id}, event)" aria-label="Close">&#x2715;</button>
        </div>`;
    }).join('');
}

function renderTabContent(recipe) {
    const container = document.getElementById('recipe-tab-content');
    if (!container) return;
    const ingHtml = recipe.ingredients.map(ing => `<li>${formatIngredient(ing)}</li>`).join('');
    const imgHtml = recipe.image_url
        ? `<img src="${escHtml(recipe.image_url)}" alt="${escHtml(recipe.title)}" class="recipe-detail-image">`
        : '';
    const sourceHtml = recipe.source
        ? `<p class="recipe-source">${recipe.url
            ? `<a href="${escHtml(recipe.url)}" target="_blank" rel="noopener">${escHtml(recipe.source)}</a>`
            : escHtml(recipe.source)}</p>`
        : '';
    const notesHtml = recipe.notes
        ? `<div class="recipe-notes"><h2>Notes</h2><p>${escHtml(recipe.notes)}</p></div>`
        : '';
    const instrHtml = recipe.instructions
        ? `<div class="instructions-text">${escHtml(recipe.instructions)}</div>`
        : '<p class="muted">No instructions saved.</p>';

    container.innerHTML = `
        <div class="recipe-detail">
            <div class="recipe-header">
                <div class="recipe-header-text">
                    <h1>${escHtml(recipe.title)}</h1>
                    ${sourceHtml}
                </div>
                ${imgHtml}
            </div>
            <div class="tab-recipe-actions">
                <form action="/meal-plan/add" method="POST" style="display:inline;">
                    <input type="hidden" name="recipe_id" value="${recipe.id}">
                    <button type="submit" class="btn btn-primary">Add to Meal Plan</button>
                </form>
                <button type="button" class="btn btn-secondary"
                        onclick="openCookingMode(tabCache[${recipe.id}])">Cooking Mode</button>
                <a href="/recipes/${recipe.id}" class="btn btn-secondary">Full Page</a>
            </div>
            <div class="recipe-content">
                <div class="recipe-ingredients">
                    <h2>Ingredients</h2>
                    <ul>${ingHtml}</ul>
                </div>
                <div class="recipe-instructions">
                    <h2>Instructions</h2>
                    ${instrHtml}
                </div>
            </div>
            ${notesHtml}
        </div>
    `;
}

// ============== Cooking Mode ==============

function parseSteps(instructions) {
    if (!instructions) return [];
    // Try numbered patterns: "1. step" or "1) step"
    if (/^\s*\d+[\.\)]\s+/m.test(instructions)) {
        return instructions
            .split(/\n?\s*\d+[\.\)]\s+/)
            .map(s => s.trim())
            .filter(s => s.length > 0);
    }
    // Fall back to paragraph / newline splitting
    return instructions
        .split(/\n\n+|\n/)
        .map(s => s.trim())
        .filter(s => s.length > 0);
}

function openCookingMode(recipe) {
    const modal = document.getElementById('cooking-modal');
    if (!modal) return;

    modal.querySelector('.cooking-title').textContent = recipe.title;

    // Populate ingredients
    modal.querySelector('.cooking-ingredients').innerHTML =
        recipe.ingredients.map(ing => `<li>${formatIngredient(ing)}</li>`).join('');

    // Populate steps
    const steps = parseSteps(recipe.instructions);
    let currentStep = 0;

    function renderStep() {
        modal.querySelector('.cooking-step-text').textContent =
            steps.length ? steps[currentStep] : 'No instructions available.';
        modal.querySelector('.cooking-step-counter').textContent =
            steps.length ? `Step ${currentStep + 1} of ${steps.length}` : '';
        modal.querySelector('.cooking-prev').disabled = currentStep === 0;
        modal.querySelector('.cooking-next').disabled = currentStep >= steps.length - 1;
    }

    modal.querySelector('.cooking-prev').onclick = () => {
        if (currentStep > 0) { currentStep--; renderStep(); }
    };
    modal.querySelector('.cooking-next').onclick = () => {
        if (currentStep < steps.length - 1) { currentStep++; renderStep(); }
    };

    renderStep();
    switchCookingTab('ingredients');

    modal.classList.remove('cooking-modal-hidden');
    document.body.style.overflow = 'hidden';

    // Wake Lock API — keep screen on while cooking
    if ('wakeLock' in navigator) {
        navigator.wakeLock.request('screen')
            .then(lock => { modal._wakeLock = lock; })
            .catch(() => {});
    }
}

function closeCookingMode() {
    const modal = document.getElementById('cooking-modal');
    if (!modal) return;
    modal.classList.add('cooking-modal-hidden');
    document.body.style.overflow = '';
    if (modal._wakeLock) {
        modal._wakeLock.release().catch(() => {});
        modal._wakeLock = null;
    }
}

function switchCookingTab(tab) {
    const modal = document.getElementById('cooking-modal');
    if (!modal) return;
    modal.querySelectorAll('.cooking-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    modal.querySelectorAll('.cooking-tab-content').forEach(panel => {
        panel.classList.toggle('cooking-tab-hidden', panel.dataset.tab !== tab);
    });
}
