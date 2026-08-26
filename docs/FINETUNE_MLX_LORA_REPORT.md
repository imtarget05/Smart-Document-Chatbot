# Fine-tune QLoRA-style 4-bit trên Apple Silicon (MLX LoRA) — qwen3-vi

**Ngày:** 2026-08-26 · **Máy:** Apple M1 Pro 16GB · Toàn bộ pipeline chạy local.

## Pipeline đã chạy (tái hiện được)

```bash
# 1. Cài môi trường
.venv/bin/pip install mlx-lm gguf torch

# 2. Tải model gốc + bản MLX 4-bit (train trên bản 4bit, fuse từ bản bf16)
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-4B-Instruct-2507')"

# 3. Soạn dataset tiếng Việt (35 samples: 31 câu eval + context docs)
python finetune/build_dataset.py   # → finetune/data/{train,valid}.jsonl

# 4. Train LoRA (adapter chỉ 0.182% tham số = 7.34M/4022M)
python -m mlx_lm lora \
  --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
  --train --fine-tune-type lora --data finetune/data \
  --iters 200 --batch-size 2 --num-layers 16 --learning-rate 1e-4 \
  --adapter-path finetune/adapters

# 5. Fuse adapter vào model gốc (bf16 — fuse từ bản 4bit sẽ sinh tensor
#    'embed_tokens.biases' mà llama.cpp không convert được)
python -m mlx_lm fuse --model Qwen/Qwen3-4B-Instruct-2507 \
  --save-path finetune/qwen3-vi-fused --adapter-path finetune/adapters

# 6. Convert GGUF (llama.cpp clone trong finetune/llama.cpp)
python llama.cpp/convert_hf_to_gguf.py finetune/qwen3-vi-fused \
  --outfile finetune/qwen3-vi-f16.gguf --outtype f16

# 7. Import vào Ollama
cd finetune && ollama create qwen3-vi -f Modelfile.qwen3-vi
```

## Kết quả training

| Chỉ số | Giá trị |
|---|---|
| Trainable params | 7.34M / 4022M (**0.182%**) |
| Train loss | 4.71 → **0.04** (iter 1→200) |
| Val loss | 4.71 → 0.41 |
| Thời gian | ~11 phút (200 iter, ~117 tok/s) |
| RAM peak | 8.9 GB |

## Benchmark A/B trên máy (6 câu RAG tiếng Việt)

| | **qwen3-vi** (4B fine-tuned) | qwen3:8b (gốc) |
|---|---|---|
| Đúng đáp án | 5/6 ⚠️ | 6/6 ✅ |
| Latency TB/câu | **2.2s** 🏆 | 42s |
| Tốc độ sinh | ~20 tok/s | ~20 tok/s |

## Phát hiện quan trọng

1. **qwen3-vi nhanh ~19 lần** nhưng bị lỗi artifact: xuất `<tool_call>` token rác ở đầu câu trả lời (do template Qwen3-Instruct khi convert GGUF). Câu "Cách hệ thống chống hallucination" thậm chí echo lại câu hỏi thay vì trả lời.
2. Fix khuyến nghị: thêm `PARAMETER stop "</tool_call>"` vào Modelfile, hoặc post-process strip `<tool_call>`; tốt nhất là re-train với chat template chuẩn Qwen3.
3. Dataset 35 samples là quá nhỏ để fine-tune ổn định — cần ≥500 samples nếu muốn model học phong cách bền vững (hiện chỉ nhớ "sup" domain).

## Kết luận cho project

- **Local fallback khả thi**: qwen3-vi dùng được ngay làm phương án dự phòng nhanh, rẻ, offline.
- Production nên dùng **qwen3:8b gốc** (chất lượng ổn định) và giữ qwen3-vi làm PoC fine-tune cho NAB story ("evidence-driven local adaptation").
