#!/usr/bin/env python3
"""Interactive CLI query tool to test the fine-tuned Sindhi Science AI model."""

import sys
import os

# Set root
sys.path.insert(0, os.path.abspath("."))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.services.sdc_rag_service import sdc_rag_service
from src.services.ai_provider import get_ai_system_status

def main():
    print("=" * 65)
    print(" SDC PILOT: FINE-TUNED SINDHI SCIENCE AI MODEL CLI TEST")
    print("=" * 65)
    status = get_ai_system_status()
    print(f"Active Provider: {status['active_provider_type']}")
    print(f"Model Name:      {status['active_model_name']}")
    print(f"Live Neural:     {status['is_live_inference']}")
    print("=" * 65)

    test_queries = [
        ("گهرڙو (Cell) ڇا آهي؟", "Chapter 1: Cell Structure"),
        ("What is Cell?", "Bilingual Concept"),
        ("خوردبين ڇا لاءِ استعمال ٿيندي آهي؟", "Chapter 1: Microscope"),
        ("روشنيءَ جو عمل (Photosynthesis) ڇا آهي؟", "Chapter 3: Photosynthesis"),
        ("آواز ڪيئن پيدا ٿئي ٿو؟", "Chapter 11: Sound")
    ]

    print("\nRunning quick test queries through the fine-tuned model:\n")
    for q, desc in test_queries:
        print(f"\n[QUERY]: {q} ({desc})")
        res = sdc_rag_service.generate_grounded_answer(q)
        print(f"Status: {res['status']} | Latency: {res['latency_ms']} ms | Provider: {res.get('ai_provider_used')}")
        print(f"Citations: {res['citations']}")
        print(f"Answer:\n{res['answer_sd'][:250]}...")
        print("-" * 50)

    print("\nAll sample queries executed successfully with active AI provider!")

if __name__ == "__main__":
    main()
