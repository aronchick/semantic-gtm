"""AI Analysis Pipeline for GTM Semantic Crawler"""
import json
import re
from typing import Optional
import time

from config.settings import (
    ANTHROPIC_API_KEY, OPENAI_API_KEY,
    ANALYSIS_MODEL, ANALYSIS_PROVIDER, EXPANSO_CONTEXT, PROBLEM_CATEGORIES
)
from db import get_unanalyzed_posts, insert_analysis

# Lazy imports for API clients
_anthropic_client = None
_openai_client = None

def get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client

def get_openai():
    global _openai_client
    if _openai_client is None:
        import openai
        _openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client

ANALYSIS_PROMPT = f"""You are an expert at identifying sales opportunities for Expanso/Bacalhau.

{EXPANSO_CONTEXT}

Problem Categories:
{json.dumps(PROBLEM_CATEGORIES, indent=2)}

Analyze the following post/comment and determine if the author is experiencing a problem that Expanso/Bacalhau could solve.

POST TITLE: {{title}}
POST BODY: {{body}}
SOURCE: {{source}}
URL: {{url}}

Respond in JSON format:
{{
  "fit_score": <0-10, how well does this problem match Bacalhau's capabilities?>,
  "urgency_score": <0-10, how urgently does this person seem to need a solution?>,
  "use_case": "<category from the list above, e.g. 'ml_inference', 'data_pipelines', etc. Use 'other' if none fit>",
  "problem_summary": "<1-2 sentence summary of the problem they're experiencing>",
  "reasoning": "<brief explanation of your scoring>"
}}

Scoring guidance:
- 0-3: Not relevant (general tech discussion, different problem domain)
- 4-6: Potentially relevant (mentions related concepts but unclear fit)
- 7-8: Good fit (clear problem that Bacalhau could solve)
- 9-10: Excellent fit (explicitly looking for Bacalhau-like solution)

For urgency:
- 0-3: Just exploring/learning
- 4-6: Has a real need but not pressing
- 7-8: Active project, needs solution soon
- 9-10: Production pain point, urgent need

Respond ONLY with the JSON object, no other text."""

def analyze_post_anthropic(title: str, body: str, source: str, url: str) -> Optional[dict]:
    """Analyze a post using Anthropic Claude"""
    client = get_anthropic()
    
    prompt = ANALYSIS_PROMPT.format(
        title=title or "(no title)",
        body=body[:3000] if body else "(no body)",  # Limit body length
        source=source,
        url=url,
    )
    
    try:
        message = client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            print(f"Could not parse JSON from response: {response_text[:200]}")
            return None
            
    except Exception as e:
        print(f"Anthropic API error: {e}")
        return None

def analyze_post_openai(title: str, body: str, source: str, url: str) -> Optional[dict]:
    """Analyze a post using OpenAI"""
    client = get_openai()
    
    prompt = ANALYSIS_PROMPT.format(
        title=title or "(no title)",
        body=body[:3000] if body else "(no body)",
        source=source,
        url=url,
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def analyze_post(title: str, body: str, source: str, url: str) -> Optional[dict]:
    """Analyze a post using configured provider"""
    if ANALYSIS_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
        return analyze_post_anthropic(title, body, source, url)
    elif OPENAI_API_KEY:
        return analyze_post_openai(title, body, source, url)
    else:
        raise RuntimeError("No API key configured for analysis")

def run_analysis(batch_size: int = 100, delay: float = 0.5) -> dict:
    """Run analysis on unanalyzed posts"""
    posts = get_unanalyzed_posts(limit=batch_size)
    
    stats = {"analyzed": 0, "skipped": 0, "errors": 0, "high_fit": 0}
    
    for post in posts:
        # Skip posts with very little content
        content = (post.get("title") or "") + " " + (post.get("body") or "")
        if len(content.strip()) < 50:
            stats["skipped"] += 1
            continue
        
        result = analyze_post(
            title=post.get("title"),
            body=post.get("body"),
            source=post.get("source"),
            url=post.get("url"),
        )
        
        if result:
            try:
                insert_analysis(
                    post_id=post["id"],
                    fit_score=result.get("fit_score", 0),
                    urgency_score=result.get("urgency_score", 0),
                    use_case=result.get("use_case", "other"),
                    reasoning=result.get("reasoning", ""),
                    problem_summary=result.get("problem_summary", ""),
                    model_used=ANALYSIS_MODEL,
                )
                stats["analyzed"] += 1
                
                if result.get("fit_score", 0) >= 7:
                    stats["high_fit"] += 1
                    
            except Exception as e:
                print(f"Error inserting analysis: {e}")
                stats["errors"] += 1
        else:
            stats["errors"] += 1
        
        time.sleep(delay)  # Rate limiting
    
    return stats

if __name__ == "__main__":
    from db import init_db
    init_db()
    stats = run_analysis(batch_size=10)
    print(f"Analysis complete: {stats}")
