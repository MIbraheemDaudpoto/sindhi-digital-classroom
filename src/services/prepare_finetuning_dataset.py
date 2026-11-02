"""SDC Dataset Preparation Script for Fine-Tuning a Neural Sindhi LLM.
Compiles curriculum chunks, glossaries, and QA pairs into standard Hugging Face
instruction-tuning formats (Alpaca JSON & ChatML JSONL) for fine-tuning on Google Colab (T4 / A100 GPU).
Target Base Models:
1. Qwen/Qwen2.5-0.5B-Instruct / Qwen/Qwen2.5-1.5B-Instruct (Best for Raspberry Pi 5 CPU via GGUF)
2. shaikhsalman/Sindhi-Qwen2.5-7B (High parameter open-weight Sindhi model)
Authored under agency-ai-engineer.
"""

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List

from src.services.sdc_rag_db import get_db_connection


def build_instruction_dataset(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()

    alpaca_data: List[Dict[str, str]] = []
    chatml_data: List[Dict[str, Any]] = []

    # System prompt strictly grounding the model
    system_prompt = (
        "توهان سنڌ ٽيڪسٽ بڪ بورڊ (STBB) جا هڪ ماهر ۽ مهربان سنڌي استاد آهيو، جيڪي ڪلاس 6 عام سائنس جا سوال سمجهائيندا آهن۔ "
        "هميشه تصديق ٿيل نصابي مواد مان جواب ڏيو ۽ باقاعده صفحو ٻڌايو۔"
    )

    # 1. Ingest from 90 Chunks (Summaries + Chapter Topics)
    chunks = conn.execute("SELECT * FROM sdc_chunks ORDER BY chapter_id, chunk_id").fetchall()
    for ch in chunks:
        ch_num = ch["chapter_id"]
        title_sd = ch["topic_title_sd"]
        title_en = ch["topic_title_en"]
        summary = ch["summary_sd"]
        citation = ch["citation_formatted"]

        # Synthetic QA prompt 1: Direct Topic Explanation in Sindhi
        inst_1 = f"باب {ch_num} ({title_en}) مان '{title_sd}' بابت سمجهاڻي ڏيو۔"
        output_1 = f"{summary}\n\n(حوالو: {citation})"

        alpaca_data.append({
            "instruction": inst_1,
            "input": f"باب: {ch_num} | موضوع: {title_sd} ({title_en})",
            "output": output_1
        })

        chatml_data.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": inst_1},
                {"role": "assistant", "content": output_1}
            ]
        })

        # Synthetic QA prompt 2: English Query to Sindhi Explanation
        inst_2 = f"Explain '{title_en}' from Class 6 General Science in Sindhi."
        output_2 = f"ڪلاس 6 سائنس جي باب {ch_num} مطابق {title_sd} ({title_en}) جو خلاصو هيٺين ريت آهي:\n\n{summary}\n\n(حوالو: {citation})"

        alpaca_data.append({
            "instruction": inst_2,
            "input": f"Class 6 Science STBB - Chapter {ch_num}",
            "output": output_2
        })

        chatml_data.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": inst_2},
                {"role": "assistant", "content": output_2}
            ]
        })

    # 2. Ingest from 201 Glossary Terms
    glossary = conn.execute("SELECT * FROM sdc_glossary ORDER BY id").fetchall()
    for g in glossary:
        term_sd = g["term_sd"]
        term_en = g["term_en"]
        definition = g["definition_sd"]
        citation = g["citation_formatted"]

        inst_g = f"سائنسي اصطلاح '{term_sd}' ({term_en}) جي وصف يا مطلب ڇا آهي؟"
        output_g = f"{term_sd} ({term_en}): {definition}\n(حوالو: {citation})"

        alpaca_data.append({
            "instruction": inst_g,
            "input": f"سائنسي اصطلاح: {term_sd} / {term_en}",
            "output": output_g
        })

        chatml_data.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": inst_g},
                {"role": "assistant", "content": output_g}
            ]
        })

    # 3. Ingest from 39 Exercises
    exercises = conn.execute("SELECT * FROM sdc_exercises ORDER BY chapter_id, id").fetchall()
    for ex in exercises:
        ch_num = ex["chapter_id"]
        item_type = ex["item_type"]
        topic_en = ex["topic_en"]
        citation = ex["citation_formatted"]
        vid_title = ex["sos_video_title"]

        inst_ex = f"ڪلاس 6 سائنس جي باب {ch_num} جي مشق '{topic_en}' جو حوالو ۽ حل ڇا آهي؟"
        output_ex = f"هي موضوع باب {ch_num} جي {item_type} آهي۔ حوالو: {citation}۔"
        if vid_title:
            output_ex += f" وڊيو ليڪچر: {vid_title}۔"

        alpaca_data.append({
            "instruction": inst_ex,
            "input": f"مشق: {topic_en} | باب {ch_num}",
            "output": output_ex
        })

        chatml_data.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": inst_ex},
                {"role": "assistant", "content": output_ex}
            ]
        })

    conn.close()

    # Save to disk
    alpaca_file = output_dir / "sdc_science_alpaca_dataset.json"
    chatml_file = output_dir / "sdc_science_chatml_dataset.jsonl"

    with open(alpaca_file, "w", encoding="utf-8") as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=2)

    with open(chatml_file, "w", encoding="utf-8") as f:
        for entry in chatml_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Generated {len(alpaca_data)} training pairs!")
    print(f"Saved Alpaca dataset to: {alpaca_file}")
    print(f"Saved ChatML dataset to: {chatml_file}")
    return len(alpaca_data)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "data" / "training"
    build_instruction_dataset(out)
