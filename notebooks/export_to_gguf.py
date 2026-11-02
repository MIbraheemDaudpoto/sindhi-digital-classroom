"""Merge LoRA adapter into base model and export to GGUF for Raspberry Pi 5 deployment."""

import os
import sys
import subprocess
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
LORA_PATH = "sdc-qwen2.5-0.5b-sindhi-science"
MERGED_OUTPUT_DIR = "sdc-qwen2.5-0.5b-sindhi-science-merged"
GGUF_OUTPUT_PATH = "sdc-qwen2.5-0.5b-sindhi-science-q4_k_m.gguf"

print("1. Loading base model in FP16...")
tokenizer = AutoTokenizer.from_pretrained(LORA_PATH, trust_remote_code=True)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

print(f"2. Merging LoRA adapter from {LORA_PATH}...")
model = PeftModel.from_pretrained(base_model, LORA_PATH)
merged_model = model.merge_and_unload()

print(f"3. Saving merged 16-bit model to {MERGED_OUTPUT_DIR}...")
merged_model.save_pretrained(MERGED_OUTPUT_DIR)
tokenizer.save_pretrained(MERGED_OUTPUT_DIR)
print("Merge complete!")

print("4. Converting to GGUF using llama.cpp...")
if not os.path.exists("llama.cpp"):
    print("Cloning llama.cpp...")
    subprocess.run(["git", "clone", "https://github.com/ggerganov/llama.cpp.git"], check=True)
    subprocess.run(["pip", "install", "-r", "llama.cpp/requirements.txt"], check=True)

fp16_gguf = f"{MERGED_OUTPUT_DIR}.f16.gguf"
print(f"Running convert_hf_to_gguf.py -> {fp16_gguf}...")
subprocess.run([
    sys.executable, "llama.cpp/convert_hf_to_gguf.py",
    MERGED_OUTPUT_DIR,
    "--outfile", fp16_gguf,
    "--outtype", "f16"
], check=True)

print("Building llama.cpp quantize tool...")
subprocess.run(["make", "-C", "llama.cpp", "llama-quantize", "-j4"], check=False)

quant_bin = "llama.cpp/build/bin/llama-quantize" if os.path.exists("llama.cpp/build/bin/llama-quantize") else "llama.cpp/llama-quantize"

if os.path.exists(quant_bin):
    print(f"Quantizing to Q4_K_M -> {GGUF_OUTPUT_PATH}...")
    subprocess.run([quant_bin, fp16_gguf, GGUF_OUTPUT_PATH, "Q4_K_M"], check=True)
    print(f"\nSUCCESS! 4-bit edge model created at: {GGUF_OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(GGUF_OUTPUT_PATH) / (1024*1024):.1f} MB")
    print("Download this file and place it in the Raspberry Pi 5 `models/` directory!")
else:
    print(f"FP16 GGUF generated at: {fp16_gguf}. Quantization binary not built, FP16 can be used directly or quantized on Pi.")
