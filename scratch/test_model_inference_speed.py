# -*- coding: utf-8 -*-
import time
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir = "models/sdc-sindhillm-1b-science"
print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())

t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
print(f"Tokenizer loaded in {time.time()-t0:.2f}s")

# Test torch.bfloat16 vs torch.float32 on CPU
dtype = torch.bfloat16 if hasattr(torch, "bfloat16") else torch.float32
t1 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    torch_dtype=dtype,
    low_cpu_mem_usage=True,
    trust_remote_code=True
)
model.eval()
print(f"Model loaded in {time.time()-t1:.2f}s, dtype={dtype}")

threads = min(4, os.cpu_count() or 2)
torch.set_num_threads(threads)
print(f"Using {threads} CPU threads")

prompt = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nتوهان سنڌ ٽيڪسٽ بڪ بورڊ (STBB) جا سنڌي استاد آهيو۔<|eot_id|>\n<|start_header_id|>user<|end_header_id|>\nسيٽ ڇا آهي؟<|eot_id|>\n<|start_header_id|>assistant<|end_header_id|>\n"
inputs = tokenizer([prompt], return_tensors="pt")

t2 = time.time()
with torch.no_grad():
    outputs = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=20,
        do_sample=False,
        repetition_penalty=1.1,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=[tokenizer.eos_token_id, 128009]
    )
gen_tokens = outputs[0][inputs.input_ids.shape[1]:]
gen_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
duration = time.time() - t2
print(f"Generated {len(gen_tokens)} tokens in {duration:.2f}s ({len(gen_tokens)/duration:.2f} tokens/s)")
print("Generated text:")
print(gen_text)

