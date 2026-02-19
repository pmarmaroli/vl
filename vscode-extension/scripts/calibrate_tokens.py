"""
LLM Token Calibration Script

Sends sample code to Claude or Gemini to measure actual token counts.
Builds a model: tokens = f(characters, language)

Run once to calibrate, then use the model in the extension.

Usage:
    python calibrate_tokens.py           # Default: Claude
    python calibrate_tokens.py claude    # Claude sonnet
    python calibrate_tokens.py gemini    # Gemini 3 pro
"""

import os
import sys
import json
from pathlib import Path

# Determine which model to use
MODEL_PROVIDER = sys.argv[1].lower() if len(sys.argv) > 1 else "claude"

# Load API keys from environment or .env file
def load_api_key(key_name: str) -> str:
    api_key = os.environ.get(key_name)
    if not api_key:
        env_paths = [
            Path(__file__).parent.parent / '.env',
            Path(__file__).parent.parent.parent / '.env',
        ]
        for env_path in env_paths:
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith(f'{key_name}='):
                        api_key = line.split('=', 1)[1].strip()
                        break
            if api_key:
                break
    return api_key

# Initialize the appropriate client
if MODEL_PROVIDER == "gemini":
    import google.generativeai as genai
    
    GEMINI_API_KEY = load_api_key('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment or .env file")
    
    genai.configure(api_key=GEMINI_API_KEY)
    MODEL_NAME = "gemini-3-pro-preview"
    client = genai.GenerativeModel(MODEL_NAME)
else:
    import anthropic
    
    ANTHROPIC_API_KEY = load_api_key('ANTHROPIC_API_KEY')
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found in environment or .env file")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    MODEL_NAME = "claude-sonnet-4-20250514"

# Sample code for calibration
SAMPLES = {
    "python": [
        # Small
        '''def add(a, b):
    return a + b''',
        
        # Medium
        '''import requests
from typing import List, Dict

def fetch_users(api_url: str) -> List[Dict]:
    """Fetch users from API and return as list of dicts."""
    response = requests.get(api_url)
    response.raise_for_status()
    return response.json()

def filter_adults(users: List[Dict], min_age: int = 18) -> List[Dict]:
    """Filter users by minimum age."""
    return [u for u in users if u.get('age', 0) >= min_age]

def get_names(users: List[Dict]) -> List[str]:
    """Extract names from user dicts."""
    return [u['name'] for u in users if 'name' in u]''',
        
        # Large
        '''import os
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """Represents a user in the system."""
    id: int
    name: str
    email: str
    age: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'age': self.age,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            email=data['email'],
            age=data['age'],
            is_active=data.get('is_active', True),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        )

class UserService:
    """Service for managing users."""
    
    def __init__(self, api_base_url: str, cache_dir: Optional[Path] = None):
        self.api_base_url = api_base_url.rstrip('/')
        self.cache_dir = cache_dir or Path('.cache')
        self.cache_dir.mkdir(exist_ok=True)
        self._users_cache: Dict[int, User] = {}
    
    def fetch_users(self, page: int = 1, limit: int = 100) -> List[User]:
        """Fetch users from API with pagination."""
        logger.info(f"Fetching users page={page} limit={limit}")
        
        try:
            response = requests.get(
                f"{self.api_base_url}/users",
                params={'page': page, 'limit': limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            users = [User.from_dict(u) for u in data.get('users', [])]
            
            # Update cache
            for user in users:
                self._users_cache[user.id] = user
            
            return users
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch users: {e}")
            raise
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID, checking cache first."""
        if user_id in self._users_cache:
            return self._users_cache[user_id]
        
        try:
            response = requests.get(f"{self.api_base_url}/users/{user_id}")
            response.raise_for_status()
            user = User.from_dict(response.json())
            self._users_cache[user_id] = user
            return user
        except requests.RequestException:
            return None
    
    def filter_active_adults(self, users: List[User], min_age: int = 18) -> List[User]:
        """Filter for active adult users."""
        return [u for u in users if u.is_active and u.age >= min_age]
    
    def save_to_cache(self, filename: str = 'users.json') -> None:
        """Save cached users to file."""
        cache_file = self.cache_dir / filename
        data = [u.to_dict() for u in self._users_cache.values()]
        cache_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved {len(data)} users to {cache_file}")
    
    def load_from_cache(self, filename: str = 'users.json') -> List[User]:
        """Load users from cache file."""
        cache_file = self.cache_dir / filename
        if not cache_file.exists():
            return []
        
        data = json.loads(cache_file.read_text())
        users = [User.from_dict(u) for u in data]
        
        for user in users:
            self._users_cache[user.id] = user
        
        return users''',
    ],
    
    "javascript": [
        # Small
        '''function add(a, b) {
    return a + b;
}''',
        
        # Medium
        '''const axios = require('axios');

async function fetchUsers(apiUrl) {
    const response = await axios.get(apiUrl);
    return response.data;
}

function filterAdults(users, minAge = 18) {
    return users.filter(u => u.age >= minAge);
}

function getNames(users) {
    return users.map(u => u.name);
}

module.exports = { fetchUsers, filterAdults, getNames };''',
        
        # Large
        '''const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');

class User {
    constructor(id, name, email, age, isActive = true, createdAt = null) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.age = age;
        this.isActive = isActive;
        this.createdAt = createdAt;
    }
    
    toJSON() {
        return {
            id: this.id,
            name: this.name,
            email: this.email,
            age: this.age,
            isActive: this.isActive,
            createdAt: this.createdAt?.toISOString() || null
        };
    }
    
    static fromJSON(data) {
        return new User(
            data.id,
            data.name,
            data.email,
            data.age,
            data.isActive ?? true,
            data.createdAt ? new Date(data.createdAt) : null
        );
    }
}

class UserService {
    constructor(apiBaseUrl, cacheDir = '.cache') {
        this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '');
        this.cacheDir = cacheDir;
        this.usersCache = new Map();
    }
    
    async init() {
        await fs.mkdir(this.cacheDir, { recursive: true });
    }
    
    async fetchUsers(page = 1, limit = 100) {
        console.log(`Fetching users page=${page} limit=${limit}`);
        
        try {
            const response = await axios.get(`${this.apiBaseUrl}/users`, {
                params: { page, limit },
                timeout: 30000
            });
            
            const users = response.data.users.map(u => User.fromJSON(u));
            
            for (const user of users) {
                this.usersCache.set(user.id, user);
            }
            
            return users;
        } catch (error) {
            console.error(`Failed to fetch users: ${error.message}`);
            throw error;
        }
    }
    
    async getUser(userId) {
        if (this.usersCache.has(userId)) {
            return this.usersCache.get(userId);
        }
        
        try {
            const response = await axios.get(`${this.apiBaseUrl}/users/${userId}`);
            const user = User.fromJSON(response.data);
            this.usersCache.set(userId, user);
            return user;
        } catch {
            return null;
        }
    }
    
    filterActiveAdults(users, minAge = 18) {
        return users.filter(u => u.isActive && u.age >= minAge);
    }
    
    async saveToCache(filename = 'users.json') {
        const cacheFile = path.join(this.cacheDir, filename);
        const data = Array.from(this.usersCache.values()).map(u => u.toJSON());
        await fs.writeFile(cacheFile, JSON.stringify(data, null, 2));
        console.log(`Saved ${data.length} users to ${cacheFile}`);
    }
    
    async loadFromCache(filename = 'users.json') {
        const cacheFile = path.join(this.cacheDir, filename);
        
        try {
            const data = JSON.parse(await fs.readFile(cacheFile, 'utf8'));
            const users = data.map(u => User.fromJSON(u));
            
            for (const user of users) {
                this.usersCache.set(user.id, user);
            }
            
            return users;
        } catch {
            return [];
        }
    }
}

module.exports = { User, UserService };''',
    ],
    
    "typescript": [
        # Small
        '''function add(a: number, b: number): number {
    return a + b;
}''',
        
        # Medium
        '''import axios from 'axios';

interface User {
    id: number;
    name: string;
    email: string;
    age: number;
}

async function fetchUsers(apiUrl: string): Promise<User[]> {
    const response = await axios.get<User[]>(apiUrl);
    return response.data;
}

function filterAdults(users: User[], minAge: number = 18): User[] {
    return users.filter(u => u.age >= minAge);
}

function getNames(users: User[]): string[] {
    return users.map(u => u.name);
}

export { fetchUsers, filterAdults, getNames, User };''',
    ],
}


def count_tokens_claude(code: str, language: str) -> dict:
    """Send code to Claude and get actual token count."""
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"Count to 3.\n\nCode context:\n```{language}\n{code}\n```"
        }]
    )
    return {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


def count_tokens_gemini(code: str, language: str) -> dict:
    """Send code to Gemini and get actual token count."""
    prompt = f"Count to 3.\n\nCode context:\n```{language}\n{code}\n```"
    
    # Use count_tokens API for accurate measurement
    token_count = client.count_tokens(prompt)
    
    # Also make a real call to verify
    response = client.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=10)
    )
    
    return {
        "input_tokens": token_count.total_tokens,
        "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
    }


def count_tokens(code: str, language: str) -> dict:
    """Route to appropriate token counter based on provider."""
    if MODEL_PROVIDER == "gemini":
        return count_tokens_gemini(code, language)
    else:
        return count_tokens_claude(code, language)


def run_calibration():
    """Run calibration and build model."""
    
    print("=" * 60)
    print(f"{MODEL_PROVIDER.upper()} Token Calibration ({MODEL_NAME})")
    print("=" * 60)
    
    results = []
    
    # Measure baseline (just the prompt without code)
    if MODEL_PROVIDER == "gemini":
        baseline_count = client.count_tokens("Count to 3.")
        baseline_tokens = baseline_count.total_tokens
    else:
        baseline = client.messages.create(
            model=MODEL_NAME,
            max_tokens=10,
            messages=[{"role": "user", "content": "Count to 3."}]
        )
        baseline_tokens = baseline.usage.input_tokens
    
    print(f"\nBaseline (prompt only): {baseline_tokens} tokens")
    
    for language, samples in SAMPLES.items():
        print(f"\n--- {language.upper()} ---")
        
        for i, code in enumerate(samples):
            size = ["small", "medium", "large"][i] if i < 3 else f"sample_{i}"
            chars = len(code)
            lines = code.count('\n') + 1
            
            usage = count_tokens(code, language)
            code_tokens = usage["input_tokens"] - baseline_tokens
            
            ratio = chars / code_tokens if code_tokens > 0 else 0
            
            result = {
                "language": language,
                "size": size,
                "characters": chars,
                "lines": lines,
                "total_tokens": usage["input_tokens"],
                "code_tokens": code_tokens,
                "chars_per_token": round(ratio, 2),
            }
            results.append(result)
            
            print(f"  {size:8} | {chars:5} chars | {lines:3} lines | {code_tokens:4} tokens | {ratio:.2f} chars/token")
    
    # Calculate averages per language
    print("\n" + "=" * 60)
    print("SUMMARY BY LANGUAGE")
    print("=" * 60)
    
    model = {}
    for language in SAMPLES.keys():
        lang_results = [r for r in results if r["language"] == language]
        avg_ratio = sum(r["chars_per_token"] for r in lang_results) / len(lang_results)
        model[language] = round(avg_ratio, 2)
        print(f"{language:12} | avg {avg_ratio:.2f} chars/token")
    
    # Overall average
    overall_avg = sum(r["chars_per_token"] for r in results) / len(results)
    model["default"] = round(overall_avg, 2)
    print(f"{'OVERALL':12} | avg {overall_avg:.2f} chars/token")
    
    # Save results
    output = {
        "calibration_date": datetime.now().isoformat(),
        "model_provider": MODEL_PROVIDER,
        "model_name": MODEL_NAME,
        "baseline_tokens": baseline_tokens,
        "model": model,
        "raw_results": results,
    }
    
    output_path = Path(__file__).parent / f"token_calibration_{MODEL_PROVIDER}.json"
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n✅ Calibration saved to {output_path}")
    
    # Generate TypeScript code for extension
    print("\n" + "=" * 60)
    print("TYPESCRIPT CODE FOR EXTENSION")
    print("=" * 60)
    print(f'''
// Token estimation model (calibrated {datetime.now().strftime('%Y-%m-%d')})
const CHARS_PER_TOKEN: Record<string, number> = {{
    python: {model.get('python', 3.5)},
    javascript: {model.get('javascript', 3.5)},
    typescript: {model.get('typescript', 3.5)},
    default: {model.get('default', 3.5)},
}};

function estimateTokens(code: string, language: string): number {{
    const ratio = CHARS_PER_TOKEN[language] || CHARS_PER_TOKEN.default;
    return Math.ceil(code.length / ratio);
}}
''')
    
    return output


if __name__ == "__main__":
    from datetime import datetime
    run_calibration()
