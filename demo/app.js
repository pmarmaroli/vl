const CHARS_PER_TOKEN = 2.58;

function estimateTokens(text) {
    return Math.ceil(text.length / CHARS_PER_TOKEN);
}

async function convert() {
    const pythonInput = document.getElementById('pythonInput').value.trim();
    
    if (!pythonInput) {
        showError('Please enter some Python code');
        return;
    }

    const convertBtn = document.getElementById('convertBtn');
    convertBtn.disabled = true;
    convertBtn.textContent = 'Converting...';
    
    hideMessages();

    try {
        const response = await fetch('/api/convert', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ python_code: pythonInput })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Conversion failed');
        }

        // Display results
        document.getElementById('vlOutput').value = data.vl_code;
        document.getElementById('pythonOutput').value = data.roundtrip_python;

        // Update stats
        const originalTokens = data.original_tokens;
        const vlTokens = data.vl_tokens;
        const saved = originalTokens - vlTokens;
        const savedPercent = ((saved / originalTokens) * 100).toFixed(1);

        document.getElementById('originalTokens').textContent = originalTokens.toLocaleString();
        document.getElementById('vlTokens').textContent = vlTokens.toLocaleString();
        document.getElementById('savedTokens').textContent = saved.toLocaleString();
        document.getElementById('savedPercent').textContent = `(${savedPercent}%)`;
        document.getElementById('statsBar').style.display = 'flex';

        showSuccess('✅ Conversion successful! Generated code executes correctly.');

    } catch (error) {
        showError(`Conversion failed: ${error.message}`);
        document.getElementById('vlOutput').value = '';
        document.getElementById('pythonOutput').value = '';
        document.getElementById('statsBar').style.display = 'none';
    } finally {
        convertBtn.disabled = false;
        convertBtn.textContent = 'Convert Python → VL → Python';
    }
}

function loadExample() {
    const example = `import requests
from datetime import datetime

def fetch_active_users(api_url: str, min_age: int = 18):
    """
    Fetch active users from API and filter by age.
    Returns list of user contact info.
    """
    response = requests.get(api_url)
    response.raise_for_status()
    users = response.json()
    
    active_adults = [
        user for user in users
        if user['age'] >= min_age
        and user['is_active']
    ]
    
    return [
        {
            'name': u['name'],
            'email': u['email']
        }
        for u in active_adults
    ]

# Example: Production API with ~50% token savings
result = fetch_active_users('https://api.example.com/users', min_age=21)
print(f"Found {len(result)} active users")`;

    document.getElementById('pythonInput').value = example;
    document.getElementById('vlOutput').value = '';
    document.getElementById('pythonOutput').value = '';
    document.getElementById('statsBar').style.display = 'none';
    hideMessages();
}

function clearAll() {
    document.getElementById('pythonInput').value = '';
    document.getElementById('vlOutput').value = '';
    document.getElementById('pythonOutput').value = '';
    document.getElementById('statsBar').style.display = 'none';
    hideMessages();
}

function copyVL() {
    const vlOutput = document.getElementById('vlOutput');
    vlOutput.select();
    document.execCommand('copy');
    showSuccess('VL code copied to clipboard!');
}

function copyRoundtrip() {
    const pythonOutput = document.getElementById('pythonOutput');
    pythonOutput.select();
    document.execCommand('copy');
    showSuccess('Python code copied to clipboard!');
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('successMessage').style.display = 'none';
}

function showSuccess(message) {
    const successDiv = document.getElementById('successMessage');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
    document.getElementById('errorMessage').style.display = 'none';
}

function hideMessages() {
    document.getElementById('errorMessage').style.display = 'none';
    document.getElementById('successMessage').style.display = 'none';
}

// Load example on page load
window.addEventListener('DOMContentLoaded', () => {
    loadExample();
});
