# 🚀 Training a Proper AI Model for Sindhi Digital Classroom (SDC) via Google Colab

This guide outlines how to train a domain-specific neural AI model for Sindhi Class 6 General Science using Google Colab's free GPU, and deploy the resulting 4-bit GGUF model to the offline Raspberry Pi 5.

---

## 1. Why Fine-Tune a Model?
- **Previous System**: Used SQLite BM25 + deterministic sentence extraction (rule-based).
- **Fine-Tuned AI System**: Real neural language model (`Qwen2.5-0.5B-Instruct` or `Qwen2.5-1.5B-Instruct`) fine-tuned via **QLoRA (4-bit)** on the Sindh Textbook Board (STBB) General Science corpus.
- **Benefits**:
  - Generates fluent, pedagogical Sindhi explanations.
  - Understands bilingual queries (`cell`, `microscope`, `photosynthesis`, `گهرڙو`, `روشنيءَ جو عمل`).
  - Runs 100% offline on Raspberry Pi 5 CPU at ~15–25 tokens/sec using 4-bit GGUF quantization (~350 MB RAM footprint).

---

## 2. Prepared Datasets in Repository
The training pairs have already been extracted, formatted, and verified in your project:
- **Alpaca Format**: `src/data/training/sdc_science_alpaca_dataset.json` (420 pairs)
- **ChatML Format**: `src/data/training/sdc_science_chatml_dataset.jsonl`

The dataset covers:
- 90 topic chunks across all 12 chapters.
- 201 bilingual scientific glossary terms with definitions in native Sindhi.
- 39 SLO exercises and practical activities.
- Hand-crafted conceptual QA pairs for foundational science topics.

---

## 3. Training on Google Colab (5 Simple Steps)

### Step 1: Open Google Colab & Select GPU
1. Go to [colab.research.google.com](https://colab.research.google.com).
2. Click **File -> Upload notebook** and select:
   `notebooks/SDC_Colab_FineTune_Qwen_Sindhi.ipynb`
3. In Colab, click **Runtime -> Change runtime type** and set **Hardware accelerator** to **T4 GPU**.

### Step 2: Upload Dataset
Run the second cell in the notebook to upload:
`src/data/training/sdc_science_alpaca_dataset.json`

### Step 3: Train Model with QLoRA
The notebook trains `Qwen/Qwen2.5-0.5B-Instruct` using:
- 4-bit BitsAndBytes quantization (NF4).
- Rank 16 LoRA adapter on attention + MLP projection layers.
- 4 epochs with cosine learning rate schedule (2e-4).
- **Training Time on Colab T4**: ~15–20 minutes.

### Step 4: Test Neural Sindhi Generation
The notebook includes an interactive test prompt:
> **سوال:** گهرڙو (Cell) ڇا آهي ۽ جاندارن لاءِ ڇو ضروري آهي؟
The model will output complete, fluent Sindhi pedagogical text grounded in STBB Chapter 1.

### Step 5: Export GGUF Model for Raspberry Pi 5
The final notebook cell:
1. Merges the LoRA weights into the base model.
2. Converts the FP16 checkpoint to GGUF format using `llama.cpp`.
3. Quantizes the weights to `Q4_K_M` (4-bit medium).
4. Automatically downloads: `sdc-qwen2.5-0.5b-sindhi-science-q4_k_m.gguf` (~350 MB).

---

## 4. Deploying to Raspberry Pi 5

1. Copy the downloaded `.gguf` file to the SDC `models/` directory:
   ```bash
   cp sdc-qwen2.5-0.5b-sindhi-science-q4_k_m.gguf models/
   ```
2. The SDC backend automatically detects the model via `src/services/ai_provider.py`:
   - If `models/sdc-qwen2.5-0.5b-sindhi-science-q4_k_m.gguf` is found, the system automatically activates `LocalGGUFAIProvider`.
   - Inference runs locally on the Pi 5's 4-core Cortex-A76 CPU with zero internet connection required.
   - If the file is absent, it seamlessly falls back to the deterministic extractive engine.
