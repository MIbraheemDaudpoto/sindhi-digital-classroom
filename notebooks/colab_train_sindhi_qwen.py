"""Google Colab Fine-Tuning Pipeline for SDC Sindhi Science Model.
Fine-tunes Qwen2.5 (0.5B / 1.5B) on STBB Class 6 General Science dataset using QLoRA.
Exports 4-bit GGUF model optimized for Raspberry Pi 5 CPU offline deployment.

Run this script on Google Colab with GPU (T4 / V100 / A100) enabled.
"""

import os
import sys
import json
import torch

print(f"=== SDC SINDHI SCIENCE AI MODEL TRAINING PIPELINE ===")
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
else:
    print("WARNING: No GPU detected! Colab T4 GPU is recommended.")

# 1. Configuration
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"  # Ultra-fast on Pi 5 (350MB Q4_K_M, ~25 tok/sec on Pi 5 CPU)
# MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct" # Alternative higher capacity model (~900MB Q4_K_M)
OUTPUT_DIR = "sdc-qwen2.5-0.5b-sindhi-science"
DATASET_PATH = "sdc_science_alpaca_dataset.json"

MAX_SEQ_LENGTH = 512
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4
LEARNING_RATE = 2e-4
NUM_EPOCHS = 4

print(f"\nTarget Base Model: {MODEL_ID}")
print(f"Output Directory: {OUTPUT_DIR}")
print(f"Epochs: {NUM_EPOCHS} | Batch Size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")

# 2. Check Dataset
if not os.path.exists(DATASET_PATH):
    print(f"Error: Dataset {DATASET_PATH} not found!")
    print("Please upload sdc_science_alpaca_dataset.json to Colab working directory.")
    sys.exit(1)

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)
print(f"Loaded {len(raw_data)} training pairs from {DATASET_PATH}")

# 3. Format into ChatML
from datasets import Dataset

SYSTEM_PROMPT = (
    "توهان سنڌ ٽيڪسٽ بڪ بورڊ (STBB) جا هڪ ماهر ۽ مهربان سنڌي استاد آهيو، جيڪي ڪلاس 6 جي شاگردن کي سائنس پڙهائيندا آهن۔ "
    "توهان صرف تصديق ٿيل نصابي مواد مان مڪمل، سليس ۽ باحوالا جواب ڏيندا آهيو۔"
)

formatted_samples = []
for item in raw_data:
    inst = item.get("instruction", "")
    inp = item.get("input", "")
    out = item.get("output", "")
    
    user_content = inst
    if inp:
        user_content = f"حوالو يا مواد:\n{inp}\n\nسوال:\n{inst}"
        
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": out}
    ]
    formatted_samples.append({"messages": messages})

hf_dataset = Dataset.from_list(formatted_samples)
print("ChatML dataset formatted successfully.")

# 4. Load Tokenizer & Model with 4-bit Quantization
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print(f"Loading {MODEL_ID} in 4-bit...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

model = prepare_model_for_kbit_training(model)

peft_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 5. Training with TRL SFTTrainer
from trl import SFTTrainer, SFTConfig

training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
    learning_rate=LEARNING_RATE,
    fp16=True,
    logging_steps=10,
    optim="paged_adamw_8bit",
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    save_strategy="epoch",
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field=None
)

def formatting_prompts_func(example):
    return tokenizer.apply_chat_template(example["messages"], tokenize=False)

trainer = SFTTrainer(
    model=model,
    train_dataset=hf_dataset,
    args=training_args,
    formatting_func=formatting_prompts_func
)

print("\nStarting LoRA Fine-Tuning on GPU...")
trainer.train()
print("\nTraining complete! Saving LoRA adapter...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"LoRA adapter successfully saved to {OUTPUT_DIR}")
