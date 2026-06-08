# agents.py
import requests
import json
import time
from config import *

class LLMClient:
    """Handles communication with LLM APIs (Gemini and OpenAI)"""
    @staticmethod
    def call_gemini(prompt, api_key=GEMINI_API_KEY, model=PRIMARY_MODEL):
        if not api_key:
            return None, "API key not set"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        max_retries = 3
        backoff = 5
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=120)
                
                # Check for rate-limiting (HTTP 429)
                if response.status_code == 429:
                    delay = backoff
                    try:
                        response_json = response.json()
                        for detail in response_json.get("error", {}).get("details", []):
                            if "RetryInfo" in detail.get("@type", ""):
                                delay = float(detail.get("retryDelay", "5s").rstrip("s")) + 2
                                break
                    except Exception:
                        pass
                    
                    time.sleep(delay)
                    backoff *= 2
                    continue
                
                response_json = response.json()
                if response.status_code == 200:
                    text = response_json['candidates'][0]['content']['parts'][0]['text']
                    return text, None
                else:
                    error_msg = response_json.get("error", {}).get("message", "Unknown error")
                    return None, f"Status {response.status_code}: {error_msg}"
            except Exception as e:
                if attempt == max_retries - 1:
                    return None, str(e)
                time.sleep(backoff)
                backoff *= 2
        return None, "Max retries exceeded"

    @staticmethod
    def call_openai(prompt, api_key=OPENAI_API_KEY, model=SECONDARY_MODEL):
        if not api_key:
            return None, "API key not set"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response_json = response.json()
            text = response_json['choices'][0]['message']['content']
            return text, None
        except Exception as e:
            return None, str(e)


# ─────────────────────────────────────────────────────────
# COMBINED PROMPT — Uses a SINGLE API call for everything
# ─────────────────────────────────────────────────────────
COMBINED_PROMPT = """You are an AI-powered Algorithm Generation and Explanation Agent.
You are a specialist system that helps computer science students understand algorithms deeply.

Given the following user request, you must produce a COMPLETE, DETAILED, and PROFESSIONAL response.

**Algorithm Name:** {algorithm}
**Target Language:** {language}
**User Query:** {query}

You MUST respond with ALL of the following sections. Be thorough and detailed — this is for a university-level student:

---

## 1. Intent Classification
State which of these intents apply: GENERATE, EXPLAIN, ANALYZE, COMPARE.

## 2. Complete Implementation
Write a FULL, WORKING, well-commented implementation of the {algorithm} algorithm in {language}.
- Include all necessary imports
- Include proper docstrings
- Include a usage example with sample input/output at the bottom in an `if __name__ == "__main__"` block
- The code must be production-quality, not a stub

## 3. Step-by-Step Explanation
Provide a detailed Chain-of-Thought explanation:
1. **Core Concept**: What does this algorithm do and why is it important? (3-4 sentences)
2. **How It Works**: Explain the algorithm logic step-by-step with numbered steps (at least 6 detailed steps)
3. **Key Data Structures**: What data structures are used and why?
4. **Dry Run Example**: Walk through a concrete example with actual values showing each iteration

## 4. Complexity Analysis
1. **Time Complexity**: Best, Average, and Worst case with mathematical justification
2. **Space Complexity**: Auxiliary and total space usage
3. **When to Use**: Practical scenarios where this algorithm excels
4. **Limitations**: When NOT to use this algorithm

---
Respond in clean Markdown format. Be comprehensive — aim for at least 500 words of explanation."""


class CoordinatorAgent:
    """Orchestrates queries using a single combined LLM call for efficiency"""
    def __init__(self):
        pass

    def process_query(self, query, algorithm, language="Python", provider="gemini"):
        prompt = COMBINED_PROMPT.format(
            algorithm=algorithm,
            language=language,
            query=query
        )

        if provider == "gemini":
            result, error = LLMClient.call_gemini(prompt)
        else:
            result, error = LLMClient.call_openai(prompt)

        if result:
            # Successfully got a real response from the LLM
            return self._format_success(result, algorithm)
        else:
            # API failed — return a helpful error message instead of fake stubs
            return self._format_error(error, algorithm, query, language)

    def _format_success(self, llm_response, algorithm):
        """Format a successful LLM response"""
        md = f"# AI Agent Output: {algorithm}\n\n"
        md += llm_response
        return md

    def _format_error(self, error_msg, algorithm, query, language):
        """When the API fails, return a clear error with instructions instead of fake stubs"""
        md = f"# AI Agent Output: {algorithm}\n\n"
        md += f"> **⚠️ API Error:** {error_msg}\n\n"
        md += "### Troubleshooting\n"
        md += "The Gemini API request failed. This is usually caused by:\n\n"
        md += "1. **Rate Limit Exceeded** — Free-tier API keys have a limit of ~20 requests/day. "
        md += "Wait a few minutes and try again, or upgrade to a paid plan.\n"
        md += "2. **Invalid API Key** — Check that your key in `keys.json` is correct.\n"
        md += "3. **Network Issue** — Check your internet connection.\n\n"
        md += f"**Your query:** *{query}*\n\n"
        md += f"**Algorithm:** {algorithm} | **Language:** {language}\n"
        return md


# ─────────────────────────────────────────────────────────
# Legacy agent classes kept for compatibility with evaluator.py
# ─────────────────────────────────────────────────────────
class ClassifierAgent:
    def classify(self, query, provider="gemini"):
        categories = []
        q_lower = query.lower()
        if any(w in q_lower for w in ["write", "generate", "code", "implement", "give me"]):
            categories.append("GENERATE")
        if any(w in q_lower for w in ["explain", "how", "why", "logic", "walkthrough", "detail"]):
            categories.append("EXPLAIN")
        if any(w in q_lower for w in ["complexity", "big o", "time complexity", "space", "analyze"]):
            categories.append("ANALYZE")
        if any(w in q_lower for w in ["compare", "vs", "versus", "difference"]):
            categories.append("COMPARE")
        if not categories:
            categories = ["GENERATE", "EXPLAIN"]
        return categories

class CodeGeneratorAgent:
    def generate(self, query, algorithm, language="Python", constraints="None", provider="gemini"):
        prompt = GENERATOR_PROMPT.format(query=query, algorithm=algorithm, language=language, constraints=constraints)
        result, error = LLMClient.call_gemini(prompt) if provider == "gemini" else LLMClient.call_openai(prompt)
        if result:
            return result
        return f"```python\n# API Error: {error}\n# Please retry after rate limit resets.\npass\n```"

class ExplainerAgent:
    def explain(self, algorithm, context, provider="gemini"):
        prompt = EXPLAINER_PROMPT.format(algorithm=algorithm, context=context)
        result, error = LLMClient.call_gemini(prompt) if provider == "gemini" else LLMClient.call_openai(prompt)
        if result:
            return result
        return f"API Error: {error}. Please retry."

class ComplexityAnalyzerAgent:
    def analyze(self, algorithm, code, provider="gemini"):
        prompt = ANALYZER_PROMPT.format(algorithm=algorithm, code=code)
        result, error = LLMClient.call_gemini(prompt) if provider == "gemini" else LLMClient.call_openai(prompt)
        if result:
            return result
        return f"API Error: {error}. Please retry."
