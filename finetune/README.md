# LoRA Fine-tuning Pipeline

Fine-tune a base language model with LoRA (Low-Rank Adaptation) on Vietnamese legal Q&A data.

## Architecture

```
finetune/
├── lora_trainer.py          # Main training pipeline
├── data/
│   ├── prepare_data.py      # Data preparation script
│   ├── train.jsonl          # Training set (generated)
│   └── valid.jsonl          # Validation set (generated)
└── adapters/                # Saved adapter weights
```

## Data Format

Training data uses JSONL format with one JSON object per line:

```json
{"instruction": "Bạn là trợ lý AI...", "input": "Câu hỏi...", "output": "Câu trả lời..."}
```

Or with chat messages:

```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

## How to Prepare Data

```bash
# From repo root
python finetune/data/prepare_data.py
```

This converts existing eval questions and generates synthetic Vietnamese legal Q&A pairs.

## How to Run Training

### Basic training

```bash
python finetune/lora_trainer.py \
  --base-model meta-llama/Llama-3.2-1B \
  --train-path finetune/data/train.jsonl \
  --valid-path finetune/data/valid.jsonl \
  --output-dir finetune/adapters/lora \
  --epochs 3 \
  --batch-size 2
```

### 8-bit quantization (saves memory)

```bash
python finetune/lora_trainer.py \
  --base-model meta-llama/Llama-3.2-1B \
  --8bit \
  --epochs 3
```

### Evaluate only

```bash
python finetune/lora_trainer.py \
  --eval-only \
  --output-dir finetune/adapters/lora
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LORA_BASE_MODEL` | `meta-llama/Llama-3.2-1B` | Base model name |
| `LORA_R` | `8` | LoRA rank |
| `LORA_ALPHA` | `32` | LoRA alpha |
| `LORA_DROPOUT` | `0.05` | LoRA dropout |
| `LORA_MAX_LENGTH` | `1024` | Max sequence length |
| `LORA_8BIT` | `false` | Use 8-bit quantization |
| `LORA_EVAL_STEPS` | `50` | Evaluation interval |

## How to Evaluate the Fine-tuned Model

```python
from finetune.lora_trainer import LoRATrainer

model, tokenizer = LoRATrainer.load_adapter(
    base_model="meta-llama/Llama-3.2-1B",
    adapter_path="finetune/adapters/lora",
)

# Generate response
inputs = tokenizer("Câu hỏi pháp lý...", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=256)
print(tokenizer.decode(outputs[0]))
```

## Hardware Requirements

| Model Size | GPU VRAM (FP16) | GPU VRAM (8-bit) | Training Time* |
|------------|-----------------|------------------|----------------|
| 1B params  | ~6 GB           | ~3 GB            | ~30 min        |
| 3B params  | ~14 GB          | ~7 GB            | ~1.5 hours     |
| 8B params  | ~30 GB          | ~16 GB           | ~4 hours       |

*Approximate, 1000 samples, 3 epochs, batch size 2.

### Minimum requirements

- **GPU**: NVIDIA with CUDA support, ≥4 GB VRAM (8-bit mode)
- **RAM**: ≥16 GB system memory
- **Disk**: ≥10 GB free (model + adapters + data)

### Recommended

- **GPU**: NVIDIA RTX 3090/4090 (24 GB) or A100
- **RAM**: ≥32 GB
- **Use 8-bit quantization** for consumer GPUs

## Dependencies

```bash
pip install peft transformers torch accelerate
```

Optional for 8-bit training:
```bash
pip install bitsandbytes
```

## Integration with Smart Document Chatbot

After training, the adapter can be served via:

1. **Ollama**: Convert to GGUF format and serve locally
2. **llm-router**: Upload adapter and configure in Cloudflare Workers AI
3. **Direct inference**: Use `LoRATrainer.load_adapter()` in the agent service
