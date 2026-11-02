with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    c = f.read()

dup = """                self._cache[clean_q] = res_obj
                return res_obj
                    text=result,
                    provider_type=self.provider_type,
                    model_name=self.model_name,
                    is_live_inference=True,
                    is_unavailable=False,
                    inference_status="REAL_LLM_INFERENCE",
                    latency_seconds=latency,
                    tokens_generated=num_tokens,
                    request_id=req_id
                )"""

correct = """                self._cache[clean_q] = res_obj
                return res_obj"""

c = c.replace(dup.replace('\n', '\r\n'), correct.replace('\n', '\r\n'))
c = c.replace(dup, correct)

with open('src/services/ai_provider.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Fixed indentation and duplicate successfully!")

