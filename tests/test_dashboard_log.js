const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const dashboardPath = path.join(__dirname, '..', 'templates', 'dashboard.html');
const source = fs.readFileSync(dashboardPath, 'utf8');
const start = source.indexOf('        function addLog(message, type = \'info\') {');
const end = source.indexOf('\n        async function setMode', start);
assert.notEqual(start, -1, 'addLog function should exist in the dashboard');
assert.notEqual(end, -1, 'addLog function should end before setMode');
const addLogSource = source.slice(start, end);

function makeElement(tagName) {
    return {
        tagName,
        className: '',
        textContent: '',
        children: [],
        appendChild(child) { this.children.push(child); },
    };
}

function createHarness() {
    const logContainer = {
        children: [],
        scrollTop: 0,
        get scrollHeight() { return this.children.length * 10; },
        appendChild(child) { this.children.push(child); },
    };
    const createdTags = [];
    const document = {
        createElement(tagName) {
            createdTags.push(tagName);
            return makeElement(tagName);
        },
        createTextNode(text) {
            return { nodeType: 3, textContent: String(text) };
        },
    };
    const addLog = new Function('document', 'logContainer', `${addLogSource}; return addLog;`)(document, logContainer);
    return { addLog, logContainer, createdTags };
}

test('renders HTML-looking model output as text instead of creating markup', () => {
    const { addLog, logContainer, createdTags } = createHarness();
    const hostileLookingText = '<img src=x onerror=alert(1)> hydraulic seal failure';
    addLog(hostileLookingText, 'alert');

    const messageLabel = logContainer.children[0].children[2];
    assert.equal(messageLabel.textContent, `[GEMMA INSIGHT] ${hostileLookingText}`);
    assert.deepEqual(createdTags, ['div', 'span', 'span']);
    assert.equal(Object.hasOwn(logContainer.children[0], 'innerHTML'), false);
});

test('uses a visible unavailable label for empty-model fallback messages', () => {
    const { addLog, logContainer } = createHarness();
    addLog('Gemma returned an empty response.', 'warning');
    const messageLabel = logContainer.children[0].children[2];
    assert.equal(messageLabel.textContent, '[AI UNAVAILABLE] Gemma returned an empty response.');
    assert.match(messageLabel.className, /amber/);
});
