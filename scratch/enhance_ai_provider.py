import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update OpenAICompatibleProvider init and timeout
old_init = '''class OpenAICompatibleProvider(BaseAIProvider):
    """Tier 3 Remote OpenAI-Compatible Adapter: Supports vLLM, Ollama, Groq, OpenRouter, or self-hosted servers."""
    provider_type: str = "OPENAI_COMPATIBLE_LLM"

    def __init__(self, endpoint_url: str, model_name: str, api_key: Optional[str] = None):
        self.endpoint_url = endpoint_url.rstrip("/") if endpoint_url else "http://localhost:11434/v1"
        self.model_name = model_name or "sdc-sindhillm-1b-science"
        self.api_key = api_key or ""'''

new_init = '''class OpenAICompatibleProvider(BaseAIProvider):
    """Tier 3 Remote OpenAI-Compatible Adapter: Supports vLLM, Ollama, Groq, OpenRouter, or self-hosted servers."""
    provider_type: str = "OPENAI_COMPATIBLE_LLM"

    def __init__(self, endpoint_url: str, model_name: str, api_key: Optional[str] = None):
        clean_url = (endpoint_url or "http://127.0.0.1:11434/v1").rstrip("/")
        if not clean_url.endswith("/v1") and ("11434" in clean_url or "api" not in clean_url):
            clean_url = f"{clean_url}/v1"
        self.endpoint_url = clean_url
        self.model_name = model_name or getattr(settings, "ollama_default_model", "llama3.2:1b")
        self.api_key = api_key or ""'''

assert old_init in text, "old_init not found"
text = text.replace(old_init, new_init)

old_timeout = '''        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:'''

new_timeout = '''        timeout_sec = max(getattr(settings, "ai_inference_timeout_seconds", 30.0), 30.0)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:'''

assert old_timeout in text, "old_timeout not found"
text = text.replace(old_timeout, new_timeout)

# 2. Update generate_draft_quiz_questions in OpenAICompatibleProvider
old_draft = '''    def generate_draft_quiz_questions(self, lesson_title: str, context_text: str, count: int = 3) -> List[dict]:
        return LocalRuleBasedAIProvider().generate_draft_quiz_questions(lesson_title, context_text, count)'''

new_draft = '''    def generate_draft_quiz_questions(self, lesson_title: str, context_text: str, count: int = 3) -> List[dict]:
        """Generate curriculum-grounded draft quiz questions via OpenAI/Ollama endpoint."""
        prompt = (
            f"Generate {count} multiple choice questions in Sindhi based on the following curriculum lesson '{lesson_title}'.\n"
            f"Curriculum text:\n{context_text[:2000]}\n\n"
            f"Return ONLY valid JSON array with format:\n"
            f'[{{"question_text_sindhi": "...", "options_sindhi": ["...", "...", "...", "..."], "correct_option_index": 0, "explanation_sindhi": "...", "difficulty": "MEDIUM"}}]\n'
        )
        url = f"{self.endpoint_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are an expert Sindhi curriculum teacher creating valid JSON quiz questions."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.3
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                if 200 <= resp.status < 300:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    content = res_data["choices"][0]["message"]["content"].strip()
                    # Extract JSON array
                    start_idx = content.find("[")
                    end_idx = content.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        parsed = json.loads(content[start_idx:end_idx+1])
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed[:count]
        except Exception as e:
            logger.warning(f"Failed to generate draft quiz via LLM, falling back to rule-based: {e}")

        return LocalRuleBasedAIProvider().generate_draft_quiz_questions(lesson_title, context_text, count)'''

assert old_draft in text, "old_draft not found"
text = text.replace(old_draft, new_draft)

# 3. Update get_ai_provider() and get_ai_system_status()
old_get_provider = '''def get_ai_provider() -> BaseAIProvider:
    """Retrieve active AI inference provider based on configuration."""
    global transformers_provider, gguf_provider, openai_provider

    # 1. Neural model explicitly requested via ai_provider in ("neural", "local_transformers", "local_neural")
    if settings.ai_provider in ("neural", "local_transformers", "local_neural"):
        if transformers_provider is None:
            transformers_provider = LocalTransformersAIProvider(model_dir=settings.local_model_dir)
        return transformers_provider

    # 2. GGUF model requested via ai_provider == "gguf"
    if settings.ai_provider == "gguf":
        if gguf_provider is None:
            gguf_provider = LocalGGUFAIProvider(model_path=settings.gguf_model_path)
        return gguf_provider

    # 3. HuggingFace Cloud requested via ai_provider == "huggingface"
    if settings.ai_provider == "huggingface":
        return HuggingFaceInferenceProvider(
            api_token=settings.hf_api_token,
            model_name=settings.ai_model_name,
            endpoint_url=settings.ai_endpoint_url
        )

    # 4. OpenAI-compatible endpoint (vLLM / Ollama / Groq / OpenAI)
    if settings.ai_provider in ("openai", "custom_openai", "vllm"):
        if openai_provider is None:
            openai_provider = OpenAICompatibleProvider(
                endpoint_url=settings.ai_endpoint_url,
                model_name=settings.ai_model_name,
                api_key=settings.ai_api_key
            )
        return openai_provider

    # 5. Default: Local Deterministic Synthesizer (explicitly non-LLM)
    return local_provider'''

new_get_provider = '''def get_ai_provider() -> BaseAIProvider:
    """Retrieve active AI inference provider based on configuration."""
    global transformers_provider, gguf_provider, openai_provider

    # 1. Auto mode: Dynamically probes running Ollama, local safetensors, or fallback
    if settings.ai_provider == "auto":
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    tags = json.loads(resp.read().decode())
                    models = [m.get("name") for m in tags.get("models", [])]
                    target_model = settings.ai_model_name if settings.ai_model_name in models else (models[0] if models else getattr(settings, "ollama_default_model", "llama3.2:1b"))
                    if openai_provider is None or openai_provider.model_name != target_model:
                        openai_provider = OpenAICompatibleProvider(
                            endpoint_url=getattr(settings, "ollama_endpoint_url", "http://127.0.0.1:11434/v1"),
                            model_name=target_model,
                            api_key=settings.ai_api_key
                        )
                    return openai_provider
        except Exception:
            pass

        safetensors_path = os.path.join(settings.local_model_dir, "model.safetensors")
        if os.path.exists(safetensors_path):
            if transformers_provider is None:
                transformers_provider = LocalTransformersAIProvider(model_dir=settings.local_model_dir)
            return transformers_provider
        return local_provider

    # 2. Neural model explicitly requested via ai_provider in ("neural", "local_transformers", "local_neural")
    if settings.ai_provider in ("neural", "local_transformers", "local_neural"):
        if transformers_provider is None:
            transformers_provider = LocalTransformersAIProvider(model_dir=settings.local_model_dir)
        return transformers_provider

    # 3. Ollama or OpenAI-compatible endpoint (vLLM / Ollama / Groq / OpenAI)
    if settings.ai_provider in ("ollama", "openai", "custom_openai", "vllm"):
        if openai_provider is None:
            endpoint = settings.ai_endpoint_url or getattr(settings, "ollama_endpoint_url", "http://127.0.0.1:11434/v1")
            model = settings.ai_model_name if settings.ai_model_name != "sdc-sindhillm-1b-science" else getattr(settings, "ollama_default_model", "llama3.2:1b")
            openai_provider = OpenAICompatibleProvider(
                endpoint_url=endpoint,
                model_name=model,
                api_key=settings.ai_api_key
            )
        return openai_provider

    # 4. GGUF model requested via ai_provider == "gguf"
    if settings.ai_provider == "gguf":
        if gguf_provider is None:
            gguf_provider = LocalGGUFAIProvider(model_path=settings.gguf_model_path)
        return gguf_provider

    # 5. HuggingFace Cloud requested via ai_provider == "huggingface"
    if settings.ai_provider == "huggingface":
        return HuggingFaceInferenceProvider(
            api_token=settings.hf_api_token,
            model_name=settings.ai_model_name,
            endpoint_url=settings.ai_endpoint_url
        )

    # 6. Default: Local Deterministic Synthesizer (explicitly non-LLM)
    return local_provider'''

assert old_get_provider in text, "old_get_provider not found"
text = text.replace(old_get_provider, new_get_provider)

with open('src/services/ai_provider.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully updated src/services/ai_provider.py!")

