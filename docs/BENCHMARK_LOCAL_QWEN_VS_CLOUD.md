# Benchmark: Qwen Local (Ollama) vs Cloud llama-3.3-70b

**Ngày:** 2026-08-26 · **Máy:** Apple M1 Pro, 16GB RAM · **RAG context:** tiếng Việt (4 đoạn)

## Kết quả tổng hợp (5 câu hỏi RAG tiếng Việt)

| Tiêu chí | qwen3:4b | qwen3:8b | Cloud llama-3.3-70b |
|---|---|---|---|
| Đúng đáp án | 5/5 ✅ | 5/5 ✅ | 5/5 ✅ |
| Latency TB / câu | ~3.9s ⚠️ | **0.7–1.4s** 🏆 | ~1.8s |
| Tốc độ sinh | 38 tok/s | 21.5 tok/s | n/a |
| Tuân thủ format | ❌ lẫn "Okay, let's see..." thinking leak | ✅ ngắn gọn đúng ý | ✅ |
| Chi phí | 0đ | 0đ | Free tier nhưng rate-limited |

## Phát hiện quan trọng

1. **qwen3:8b nhanh hơn cả cloud** trên máy bạn (TB ~1s vs 1.8s) — vì cloud đi vòng: backend Render → llm-router → Cloudflare Workers AI.
2. **qwen3:4b có vấn đề "thinking leak"**: dù tắt `think`, model vẫn xuất phần suy luận tiếng Anh vào câu trả lời khi prompt thuần tiếng Việt → không dùng được production nếu không post-process. 8b thì sạch.
3. **Cloud free tier không ổn định**: trong lúc đo, Cloudflare Workers AI trả rỗng liên tục ~2 phút ("Sorry, I could not generate a response") rồi tự hồi phục — đúng loại lỗi transient đã thấy ở eval 17:22 hôm trước.
4. Chất lượng tiếng Việt: 8b trả lời tự nhiên, đúng ngữ pháp; trích dẫn số liệu chính xác từ context.

## Khuyến nghị kiến trúc cho project

- **Local fallback**: thêm `qwen3:8b` làm provider dự phòng trong llm-router khi Cloudflare lỗi/circuit-open (khắc phục luôn điểm yếu reliability vừa phát hiện).
- Không khuyên dùng 4b cho answer generation (thinking leak); có thể giữ cho task phụ như query reformulation.

## Cách tái hiện

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:8b", "think": false, "stream": false,
  "prompt": "<context>\n\nCâu hỏi: ...",
  "options": {"temperature": 0.3}
}'
```

Dữ liệu thô: `/tmp/bench_cloud.json`, `/tmp/bench_local_summary.json`
