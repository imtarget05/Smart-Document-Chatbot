# Legal Domain Fine-Tuning Guide

## Why Fine-Tune?
- General LLMs (llama3.2, qwen3) may hallucinate legal citations
- Fine-tuned models understand Vietnamese legal terminology
- Better accuracy for statutory interpretation

## Option A: Fine-Tune with Ollama (Simple)

### 1. Prepare Training Data
Create `legal_training.jsonl`:
```json
{"prompt": "Điều 7 Luật Doanh nghiệp 2020 quy định gì?", "completion": "Điều 7 quy định về hình thức doanh nghiệp: (1) Doanh nghiệp tư nhân... (2) Công ty TNHH... (3) Công ty cổ phần..."}
```

### 2. Create Modelfile
```dockerfile
FROM llama3.2

# System prompt for legal domain
SYSTEM """Bạn là trợ lý pháp luật Việt Nam. Trả lời chính xác theo văn bản luật được cung cấp. 
Không bịa định điều luật. Nếu không có thông tin, hãy nói 'Không tìm thấy trong tài liệu'."""

# Training data
TEMPLATE """{{ .System }}

### Câu hỏi:
{{ .Prompt }}

### Trả lời:
{{ .Completion }}"""
```

### 3. Build Custom Model
```bash
ollama create legal-llama -f Modelfile
ollama run legal-llama
```

## Option B: Fine-Tune with Unsloth (Advanced, GPU Required)

### 1. Setup
```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-bnb-4bit",
    max_seq_length = 2048,
    load_in_4bit = True,
)
```

### 2. Prepare Dataset
```python
from datasets import load_dataset

dataset = load_dataset("json", data_files="legal_vi_dataset.jsonl")
```

### 3. Train
```python
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
)

from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset["train"],
    dataset_text_field = "text",
    max_seq_length = 2048,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        output_dir = "outputs",
    ),
)
trainer.train()
```

### 4. Export to Ollama
```python
model.save_pretrained_gguf("model", tokenizer, quantization_method = "q4_k_m")
# Convert to Ollama format
```

## Option C: Use Cloud API (Production)
For production, consider:
- **OpenAI GPT-4**: Best accuracy, higher cost
- **Anthropic Claude**: Good for legal reasoning
- **Azure OpenAI**: Enterprise compliance
- **Google Vertex AI**: Integration with Google Workspace

## Evaluation Metrics
After fine-tuning, measure:
1. **Hallucination Rate**: Target <5%
2. **Citation Accuracy**: Target >90%
3. **Legal Term Accuracy**: Target >95%
4. **Latency**: Target <2s p95

Use `eval/eval.py` to benchmark:
```bash
python eval/eval.py --base-url http://localhost:8080/api \
  --token $JWT --document-id 1 \
  --questions eval/questions.json \
  --output eval/results/finetuned_results.json
```
