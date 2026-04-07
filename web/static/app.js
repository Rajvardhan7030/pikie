// web/static/app.js

// Tab switching logic
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).style.display = 'block';
    document.querySelector(`[onclick="showTab('${tabId}')"]`).classList.add('active');
}

// Common file handling
let selectedFile = null;

function handleFileSelect(event, previewId, btnId) {
    const file = event.target.files[0];
    if (!file) return;
    
    selectedFile = file;
    const preview = document.getElementById(previewId);
    if (preview) {
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            preview.style.display = 'none';
        }
    }
    
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = false;
}

// Extraction logic
async function extractExif() {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    const res = await fetch('/extract', { method: 'POST', body: formData });
    const data = await res.json();
    displayResults(data, 'extractResults');
}

function displayResults(data, containerId) {
    const container = document.getElementById(containerId);
    let html = '<div class="success"><h3>EXIF Data Extracted!</h3><table style="width:100%">';
    for (const [k, v] of Object.entries(data)) {
        if (typeof v === 'object') continue;
        html += `<tr><td><b>${k}</b></td><td>${v}</td></tr>`;
    }
    html += '</table></div>';
    container.innerHTML = html;
}

// Tagging logic
let customTags = [];

function addTagField() {
    const container = document.getElementById('tagFields');
    const div = document.createElement('div');
    div.className = 'tag-field';
    div.innerHTML = `
        <input type="text" placeholder="Key" class="tag-key">
        <select class="tag-type">
            <option value="text">Text</option>
            <option value="number">Number</option>
        </select>
        <input type="text" placeholder="Value" class="tag-value">
        <button onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(div);
}

async function saveTags() {
    if (!selectedFile) return;
    const tags = {};
    document.querySelectorAll('.tag-field').forEach(field => {
        const key = field.querySelector('.tag-key').value;
        const type = field.querySelector('.tag-type').value;
        let value = field.querySelector('.tag-value').value;
        if (key) {
            if (type === 'number') value = parseFloat(value);
            tags[key] = value;
        }
    });
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('tags_json', JSON.stringify(tags));
    
    const res = await fetch('/tag', { method: 'POST', body: formData });
    const blob = await res.blob();
    downloadBlob(blob, `tagged_${selectedFile.name}`);
}

// Encryption logic
async function encryptFile() {
    const password = document.getElementById('encPassword').value;
    if (!selectedFile || !password) return;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('password', password);
    
    const res = await fetch('/encrypt', { method: 'POST', body: formData });
    if (!res.ok) {
        const err = await res.json();
        alert(err.detail);
        return;
    }
    const blob = await res.blob();
    downloadBlob(blob, selectedFile.name.split('.')[0] + '.pikie');
}

async function decryptFile() {
    const password = document.getElementById('decPassword').value;
    if (!selectedFile || !password) return;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('password', password);
    
    const res = await fetch('/decrypt', { method: 'POST', body: formData });
    if (!res.ok) {
        alert("Decryption failed. Wrong password?");
        return;
    }
    const blob = await res.blob();
    downloadBlob(blob, 'restored_image.jpg');
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
}

// Initial setup
window.onload = () => {
    showTab('extractTab');
};
