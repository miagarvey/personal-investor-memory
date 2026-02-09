// Investor Memory - Context Viewer Frontend

const API_BASE = '';

// === API Client ===

async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    return response.json();
}

async function searchCompanies(query, limit = 10) {
    return fetchAPI(`/companies?q=${encodeURIComponent(query)}&limit=${limit}`);
}

async function searchPeople(query, limit = 10) {
    return fetchAPI(`/people?q=${encodeURIComponent(query)}&limit=${limit}`);
}

async function listCompanies(limit = 20) {
    return fetchAPI(`/companies?limit=${limit}`);
}

async function listPeople(limit = 20) {
    return fetchAPI(`/people?limit=${limit}`);
}

async function analyzeText(text) {
    return fetchAPI('/analyze', {
        method: 'POST',
        body: JSON.stringify({ text }),
    });
}

async function saveToMemory(text, sourceType = 'document') {
    return fetchAPI('/ingest/text', {
        method: 'POST',
        body: JSON.stringify({ text, source_type: sourceType }),
    });
}

async function getCompanyContext(companyId) {
    return fetchAPI(`/company/${companyId}/context`);
}

async function getPersonContext(personId) {
    return fetchAPI(`/person/${personId}/context`);
}

async function semanticSearch(query, limit = 10) {
    return fetchAPI(`/search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

// === UI State ===

let currentEntities = [];
let searchDebounceTimer = null;

// === DOM Elements ===

const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const companyList = document.getElementById('company-list');
const personList = document.getElementById('person-list');
const inputText = document.getElementById('input-text');
const fileInput = document.getElementById('file-input');
const fileName = document.getElementById('file-name');
const analyzeBtn = document.getElementById('analyze-btn');
const saveBtn = document.getElementById('save-btn');
const extractedEntities = document.getElementById('extracted-entities');
const entityChips = document.getElementById('entity-chips');
const contentCards = document.getElementById('content-cards');
const loadingOverlay = document.getElementById('loading-overlay');

// === Utility Functions ===

function showLoading() {
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function debounce(fn, delay) {
    return function (...args) {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}

function truncateText(text, maxLength = 200) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// === Render Functions ===

function renderSearchResults(companies, people) {
    if (companies.length === 0 && people.length === 0) {
        searchResults.classList.add('hidden');
        return;
    }

    let html = '';

    companies.forEach(company => {
        html += `
            <div class="search-result-item" data-type="company" data-id="${company.id}">
                <span class="type-badge company">Company</span>
                <span>${escapeHtml(company.name)}</span>
            </div>
        `;
    });

    people.forEach(person => {
        html += `
            <div class="search-result-item" data-type="person" data-id="${person.id}">
                <span class="type-badge person">Person</span>
                <span>${escapeHtml(person.name)}</span>
                ${person.company_name ? `<span style="color: #999; font-size: 0.8em;">@ ${escapeHtml(person.company_name)}</span>` : ''}
            </div>
        `;
    });

    searchResults.innerHTML = html;
    searchResults.classList.remove('hidden');
}

function renderEntityList(companies, people) {
    companyList.innerHTML = companies.map(c => `
        <div class="entity-item" data-type="company" data-id="${c.id}">
            ${escapeHtml(c.name)}
        </div>
    `).join('');

    personList.innerHTML = people.map(p => `
        <div class="entity-item" data-type="person" data-id="${p.id}">
            ${escapeHtml(p.name)}
        </div>
    `).join('');
}

function renderEntityChips(entities) {
    if (entities.length === 0) {
        extractedEntities.classList.add('hidden');
        return;
    }

    extractedEntities.classList.remove('hidden');

    entityChips.innerHTML = entities.map(e => {
        const typeClass = e.type === 'company' ? 'company' : 'person';
        const linkedClass = e.id ? 'linked' : 'unlinked';
        return `
            <span class="entity-chip ${typeClass} ${linkedClass}"
                  data-type="${e.type}"
                  data-id="${e.id || ''}"
                  data-name="${escapeHtml(e.name)}">
                ${escapeHtml(e.name)}
            </span>
        `;
    }).join('');

    currentEntities = entities;
}

function renderContentCards(results) {
    if (results.length === 0) {
        contentCards.innerHTML = '<p class="placeholder-text">No related content found.</p>';
        return;
    }

    contentCards.innerHTML = results.map(result => {
        const chunk = result.chunk;
        const sourceType = chunk.source_type;

        let entitiesHtml = '';
        if (result.company_name) {
            entitiesHtml += `<span class="mini-chip">${escapeHtml(result.company_name)}</span>`;
        }
        if (result.people_names && result.people_names.length > 0) {
            entitiesHtml += result.people_names.map(name =>
                `<span class="mini-chip">${escapeHtml(name)}</span>`
            ).join('');
        }

        return `
            <div class="content-card">
                <div class="content-card-header">
                    <span class="source-badge ${sourceType}">${sourceType.replace('_', ' ')}</span>
                    <span class="content-card-time">${formatDate(chunk.timestamp)}</span>
                </div>
                <div class="content-card-text">${escapeHtml(truncateText(chunk.text, 300))}</div>
                ${entitiesHtml ? `<div class="content-card-entities">${entitiesHtml}</div>` : ''}
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// === Event Handlers ===

async function handleSearch(query) {
    if (!query.trim()) {
        searchResults.classList.add('hidden');
        return;
    }

    try {
        const [companies, people] = await Promise.all([
            searchCompanies(query, 5),
            searchPeople(query, 5),
        ]);
        renderSearchResults(companies, people);
    } catch (error) {
        console.error('Search failed:', error);
    }
}

async function handleSearchResultClick(type, id) {
    searchResults.classList.add('hidden');
    searchInput.value = '';

    showLoading();
    try {
        let context;
        if (type === 'company') {
            context = await getCompanyContext(id);
        } else {
            context = await getPersonContext(id);
        }

        // Clear extracted entities when viewing a specific entity
        extractedEntities.classList.add('hidden');
        entityChips.innerHTML = '';

        renderContentCards(context.results);

        // Highlight the selected entity in the list
        document.querySelectorAll('.entity-item').forEach(el => {
            el.classList.remove('active');
            if (el.dataset.id === id) {
                el.classList.add('active');
            }
        });
    } catch (error) {
        console.error('Failed to get context:', error);
        contentCards.innerHTML = '<p class="placeholder-text">Failed to load context.</p>';
    } finally {
        hideLoading();
    }
}

async function handleAnalyze() {
    const text = inputText.value.trim();
    if (!text) {
        alert('Please enter some text to analyze.');
        return;
    }

    showLoading();
    try {
        const result = await analyzeText(text);
        renderEntityChips(result.extracted_entities);
        renderContentCards(result.related_content);
    } catch (error) {
        console.error('Analysis failed:', error);
        alert('Failed to analyze text. Please try again.');
    } finally {
        hideLoading();
    }
}

async function handleSave() {
    const text = inputText.value.trim();
    if (!text) {
        alert('Please enter some text to save.');
        return;
    }

    showLoading();
    try {
        await saveToMemory(text);
        alert('Text saved to memory successfully!');
        inputText.value = '';

        // Refresh entity lists
        await loadInitialEntities();
    } catch (error) {
        console.error('Save failed:', error);
        alert('Failed to save text. Please try again.');
    } finally {
        hideLoading();
    }
}

async function handleEntityChipClick(type, id, name) {
    if (!id) {
        // Unlinked entity - do a semantic search
        showLoading();
        try {
            const results = await semanticSearch(name, 10);
            renderContentCards(results);
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            hideLoading();
        }
        return;
    }

    // Linked entity - get full context
    await handleSearchResultClick(type, id);
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    fileName.textContent = file.name;

    const reader = new FileReader();
    reader.onload = (e) => {
        inputText.value = e.target.result;
    };
    reader.onerror = () => {
        alert('Failed to read file.');
    };
    reader.readAsText(file);
}

// === Initialization ===

async function loadInitialEntities() {
    try {
        const [companies, people] = await Promise.all([
            listCompanies(20),
            listPeople(20),
        ]);
        renderEntityList(companies, people);
    } catch (error) {
        console.error('Failed to load entities:', error);
    }
}

function initEventListeners() {
    // Search input with debounce
    searchInput.addEventListener('input', debounce((e) => {
        handleSearch(e.target.value);
    }, 300));

    // Hide search results on blur (with delay for click to register)
    searchInput.addEventListener('blur', () => {
        setTimeout(() => searchResults.classList.add('hidden'), 200);
    });

    // Search result click
    searchResults.addEventListener('click', (e) => {
        const item = e.target.closest('.search-result-item');
        if (item) {
            handleSearchResultClick(item.dataset.type, item.dataset.id);
        }
    });

    // Entity list click
    document.getElementById('entity-list').addEventListener('click', (e) => {
        const item = e.target.closest('.entity-item');
        if (item) {
            handleSearchResultClick(item.dataset.type, item.dataset.id);
        }
    });

    // Entity chip click
    entityChips.addEventListener('click', (e) => {
        const chip = e.target.closest('.entity-chip');
        if (chip) {
            handleEntityChipClick(chip.dataset.type, chip.dataset.id, chip.dataset.name);
        }
    });

    // Analyze button
    analyzeBtn.addEventListener('click', handleAnalyze);

    // Save button
    saveBtn.addEventListener('click', handleSave);

    // File upload
    fileInput.addEventListener('change', handleFileUpload);
}

// Start the app
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadInitialEntities();
});
