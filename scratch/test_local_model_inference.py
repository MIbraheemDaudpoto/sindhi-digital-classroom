import time
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir = "models/sdc-sindhillm-1b-science"
print("Loading tokenizer...")
t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
print(f"Tokenizer loaded in {time.time() - t0:.2f}s")

print("Loading model in bfloat16...")
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    dtype=torch.bfloat16,
    low_cpu_mem_usage=False,
    trust_remote_code=True
)
model.eval()
print(f"Model loaded in {time.time() - t0:.2f}s")

prompt = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nتوهان هڪ سنڌي استاد آهيو۔<|eot_id|><|start_header_id|>user<|end_header_id|>\nجيو گهرڙو ڇا آهي؟<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
inputs = tokenizer([prompt], return_tensors="pt")
print("Generating 20 tokens...")
t0 = time.time()
with torch.no_grad():
    outputs = model.generate(inputs.input_ids, max_new_tokens=20, do_sample=False)
gen_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
print(f"Generated in {time.time() - t0:.2f}s: {repr(gen_text)}")
