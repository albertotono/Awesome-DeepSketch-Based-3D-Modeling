import os
import time
import requests
import datetime
import json
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
KEYWORDS = '"sketch to 3D" deep learning generation'
# We search these specific "Honeypots" for high-quality papers
DOMAINS = [
    "arxiv.org",
    "dl.acm.org",
    "ieeexplore.ieee.org",
    "onlinelibrary.wiley.com",
    "twitter.com", # For social signals
    "github.com"   # For code releases
]

# --- LOCAL LLM CONFIG (Ollama) ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2" # Lightweight model that runs fast in CI

def search_web_free():
    """Uses DuckDuckGo to scan the internet without an API key."""
    print("🌍 Starting Free Web Scout (DuckDuckGo)...")
    results = []
    
    with DDGS() as ddgs:
        for domain in DOMAINS:
            query = f"site:{domain} {KEYWORDS} after:{datetime.date.today().year}-01-01"
            print(f"   Searching: {query}")
            try:
                # Get top 5 results per domain to keep it fast
                hits = list(ddgs.text(query, max_results=5))
                for h in hits:
                    h['source_domain'] = domain
                    results.append(h)
                time.sleep(1) # Be polite
            except Exception as e:
                print(f"   ⚠️ Error searching {domain}: {e}")
                
    print(f"   Found {len(results)} raw candidates.")
    return results

def ask_local_llm(title, snippet):
    """
    Sends text to the local Ollama instance running in the GitHub Action.
    No API Key required.
    """
    prompt = f"""
    Task: Check if this paper is relevant for a "Deep Sketch-Based 3D Modeling" list.
    
    Candidate:
    Title: {title}
    Snippet: {snippet}
    
    Rules:
    1. MUST be Sketch -> 3D Shape.
    2. MUST use Deep Learning.
    3. Output STRICTLY in this format: | YEAR | [Title](URL) | Venue |
    4. If irrelevant, output STRICTLY: NO_MATCH
    """
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1}
    }
    
    try:
        resp = requests.post(OLLAMA_URL, json=payload)
        resp_json = resp.json()
        return resp_json.get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"   ⚠️ Ollama Error: {e}")
        return "NO_MATCH"

def main():
    # 1. Search
    candidates = search_web_free()
    
    valid_rows = []
    seen_urls = set()
    
    print(f"🧠 Analyzing {len(candidates)} items with Local LLM...")
    
    for item in candidates:
        if item['href'] in seen_urls: continue
        seen_urls.add(item['href'])
        
        # 2. Filter with Local LLM
        decision = ask_local_llm(item['title'], item['body'])
        
        if "NO_MATCH" not in decision and "|" in decision:
            # Clean up the output
            row = decision.replace("URL", item['href']) # Fallback if LLM missed it
            # Ensure the link is actually in there
            if "(" not in row: 
                row = f"| {datetime.date.today().year} | [{item['title']}]({item['href']}) | {item['source_domain']} |"
            
            print(f"   ✅ KEEP: {item['title']}")
            valid_rows.append(row)

    # 3. Save
    if valid_rows:
        with open("new_papers_free.md", "w", encoding="utf-8") as f:
            f.write("### 🦞 Fresh Catch (No-Key Agent)\n\n")
            f.write("| Year | Paper | Venue | Code / Project |\n")
            f.write("|---|---|---|---|\n")
            f.write("\n".join(valid_rows))
        print(f"🎉 Saved {len(valid_rows)} new papers.")
    else:
        print("No new papers found.")

if __name__ == "__main__":
    main()
