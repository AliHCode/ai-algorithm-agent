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
            return "[Simulation Mode: Gemini API Key not set. Prompt received.]"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        max_retries = 3
        backoff = 5
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)
                
                # Check for rate-limiting (HTTP 429) or non-200 status
                if response.status_code == 429:
                    delay = backoff
                    try:
                        response_json = response.json()
                        for detail in response_json.get("error", {}).get("details", []):
                            if "RetryInfo" in detail.get("@type", ""):
                                # Extract seconds from e.g. "40s"
                                delay = float(detail.get("retryDelay", "5s").rstrip("s")) + 1
                                break
                    except Exception:
                        pass
                    
                    time.sleep(delay)
                    backoff *= 2
                    continue
                
                response_json = response.json()
                if response.status_code == 200:
                    return response_json['candidates'][0]['content']['parts'][0]['text']
                else:
                    error_msg = response_json.get("error", {}).get("message", "Unknown error")
                    return f"Gemini API Error: Status {response.status_code} - {error_msg}"
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"Gemini API Error: {str(e)}"
                time.sleep(backoff)
                backoff *= 2
        return "Gemini API Error: Max retries exceeded."

    @staticmethod
    def call_openai(prompt, api_key=OPENAI_API_KEY, model=SECONDARY_MODEL):
        if not api_key:
            return "[Simulation Mode: OpenAI API Key not set. Prompt received.]"
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
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response_json = response.json()
            return response_json['choices'][0]['message']['content']
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"

class ClassifierAgent:
    def classify(self, query, provider="gemini"):
        prompt = CLASSIFIER_PROMPT.format(query=query)
        if provider == "gemini":
            response = LLMClient.call_gemini(prompt)
        else:
            response = LLMClient.call_openai(prompt)
        
        # If response is simulation mode or error, default to a standard classification
        if "[Simulation" in response or "Error:" in response:
            categories = []
            q_lower = query.lower()
            if any(w in q_lower for w in ["write", "generate", "code", "implement", "give me"]):
                categories.append("GENERATE")
            if any(w in q_lower for w in ["explain", "how", "why", "logic", "walkthrough"]):
                categories.append("EXPLAIN")
            if any(w in q_lower for w in ["complexity", "big o", "time complexity", "space"]):
                categories.append("ANALYZE")
            if any(w in q_lower for w in ["compare", "vs", "versus", "difference"]):
                categories.append("COMPARE")
            if not categories:
                categories = ["GENERATE", "EXPLAIN"]
            return categories
            
        # Parse classification categories
        categories = [cat.strip().upper() for cat in response.split(",") if cat.strip()]
        return categories

class CodeGeneratorAgent:
    def generate(self, query, algorithm, language="Python", constraints="None", provider="gemini"):
        prompt = GENERATOR_PROMPT.format(query=query, algorithm=algorithm, language=language, constraints=constraints)
        if provider == "gemini":
            response = LLMClient.call_gemini(prompt)
        else:
            response = LLMClient.call_openai(prompt)
            
        if "[Simulation" in response or "Error:" in response:
            return f"```python\n# Simulated Code for {algorithm} in {language}\ndef {algorithm.lower().replace(' ', '_')}(*args, **kwargs):\n    # TODO: Implement {algorithm}\n    pass\n```"
        return response

class ExplainerAgent:
    def explain(self, algorithm, context, provider="gemini"):
        prompt = EXPLAINER_PROMPT.format(algorithm=algorithm, context=context)
        if provider == "gemini":
            response = LLMClient.call_gemini(prompt)
        else:
            response = LLMClient.call_openai(prompt)
            
        if "[Simulation" in response or "Error:" in response:
            return f"1. **Core Concept**: This is a simulated conceptual explanation of {algorithm}.\n2. **Step-by-Step Logic**: The system traverses inputs iteratively.\n3. **Dry Run**: Simulated walkthrough complete."
        return response

class ComplexityAnalyzerAgent:
    def analyze(self, algorithm, code, provider="gemini"):
        prompt = ANALYZER_PROMPT.format(algorithm=algorithm, code=code)
        if provider == "gemini":
            response = LLMClient.call_gemini(prompt)
        else:
            response = LLMClient.call_openai(prompt)
            
        if "[Simulation" in response or "Error:" in response:
            return f"1. **Time Complexity**: $O(n \\log n)$ average for {algorithm}.\n2. **Space Complexity**: $O(1)$ auxiliary storage.\n3. **Bottlenecks**: I/O and nesting loops."
        return response

class CoordinatorAgent:
    """Orchestrates queries, routes to specialist agents, and compiles output"""
    def __init__(self):
        self.classifier = ClassifierAgent()
        self.generator = CodeGeneratorAgent()
        self.explainer = ExplainerAgent()
        self.analyzer = ComplexityAnalyzerAgent()

    def process_query(self, query, algorithm, language="Python", provider="gemini"):
        # Step 1: Classify intent
        intents = self.classifier.classify(query, provider)
        
        output = {"query": query, "intents": intents, "code": "", "explanation": "", "complexity": ""}
        
        # Step 2: Route tasks
        if "GENERATE" in intents or not intents:
            output["code"] = self.generator.generate(query, algorithm, language=language, provider=provider)
            context = output["code"]
        else:
            context = f"Algorithm: {algorithm}. Code not requested."

        if "EXPLAIN" in intents:
            output["explanation"] = self.explainer.explain(algorithm, context, provider=provider)

        if "ANALYZE" in intents:
            code_context = output["code"] if output["code"] else f"Algorithm context for: {algorithm}"
            output["complexity"] = self.analyzer.analyze(algorithm, code_context, provider=provider)

        return self.format_markdown(output, algorithm)

    def format_markdown(self, results, algorithm):
        md = f"# AI Agent Output: {algorithm}\n\n"
        md += f"**Detected Intents:** {', '.join(results['intents'])}\n\n"
        
        if results["code"]:
            md += f"## 💻 Implementation\n{results['code']}\n\n"
        if results["explanation"]:
            md += f"## 📖 Logic & Walkthrough\n{results['explanation']}\n\n"
        if results["complexity"]:
            md += f"## 📊 Complexity Analysis\n{results['complexity']}\n\n"
            
        return md
