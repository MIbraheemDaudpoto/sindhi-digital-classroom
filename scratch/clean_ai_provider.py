import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace lines 351 to 397 with just standard HuggingFace method
dup_block = text[text.find('    def generate_draft_quiz_questions(self, lesson_title: str, context_text: str, count: int = 3) -> List[dict]:\n        """Generate curriculum-grounded draft quiz questions via OpenAI/Ollama endpoint."""'):text.find('class OpenAICompatibleProvider(BaseAIProvider):')]

clean_hf_draft = '''    def generate_draft_quiz_questions(self, lesson_title: str, context_text: str, count: int = 3) -> List[dict]:
        return LocalRuleBasedAIProvider().generate_draft_quiz_questions(lesson_title, context_text, count)


'''

text = text.replace(dup_block, clean_hf_draft)

# Now fix the generate_draft_quiz_questions in OpenAICompatibleProvider
openai_draft_bad_start = text.find('    def generate_draft_quiz_questions(self, lesson_title: str, context_text: str, count: int = 3) -> List[dict]:', text.find('class OpenAICompatibleProvider'))
openai_draft_end = text.find('class LocalTransformersAIProvider(BaseAIProvider):')

good_openai_draft = '''    def generate_draft_quiz_questions(self, lesson_title: str, context_text: str, count: int = 3) -> List[dict]:
        """Generate curriculum-grounded draft quiz questions via OpenAI/Ollama endpoint."""
        prompt = (
            f"Generate {count} multiple choice questions in Sindhi based on the following curriculum lesson '{lesson_title}'.\\n"
            f"Curriculum text:\\n{context_text[:2000]}\\n\\n"
            f"Return ONLY a valid JSON array with format:\\n"
            f'[{{"question_text_sindhi": "...", "options_sindhi": ["...", "...", "...", "..."], "correct_option_index": 0, "explanation_sindhi": "...", "difficulty": "MEDIUM"}}]'
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
                    start_idx = content.find("[")
                    end_idx = content.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        parsed = json.loads(content[start_idx:end_idx+1])
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed[:count]
        except Exception as e:
            logger.warning(f"Failed to generate draft quiz via LLM, falling back to rule-based: {e}")

        return LocalRuleBasedAIProvider().generate_draft_quiz_questions(lesson_title, context_text, count)


'''

text = text[:openai_draft_bad_start] + good_openai_draft + text[openai_draft_end:]

with open('src/services/ai_provider.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully cleaned up src/services/ai_provider.py!")

