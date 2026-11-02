import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        model, tokenizer = self._load_model()
        if not model or not tokenizer:


        # Fast-path cache lookup for verified fine-tuned model inferences
        clean_q = re.sub(r"\s+", " ", question).strip()'''

replacement = '''        model, tokenizer = self._load_model()
        if not model or not tokenizer:
            diag = self._init_error or "Model or tokenizer failed to initialize"
            logger.warning(f"Local neural model not available: {diag}. Reporting unavailable state.")
            return LLMGenerationResult(
                text=SINDHI_AI_UNAVAILABLE_MESSAGE,
                provider_type=self.provider_type,
                model_name=self.model_name,
                is_live_inference=False,
                is_unavailable=True,
                inference_status="LLM_INFERENCE_UNAVAILABLE",
                latency_seconds=round(time.time() - start_time, 4),
                request_id=req_id,
                diagnostic_message=diag
            )

        # Fast-path cache lookup for verified fine-tuned model inferences
        clean_q = re.sub(r"\s+", " ", question).strip()'''

assert target in text, "Target block not found!"
text = text.replace(target, replacement)

with open('src/services/ai_provider.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed ai_provider.py syntax!")

