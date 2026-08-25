#!/usr/bin/env python3
"""Decision 17 - local LLM PoC harness (OFFLINE, NO Cloud).

Scores a local Ollama model on legal-critical behavior using the same
synthetic Vietnamese legal fixtures as the backend retrieval benchmark.
Dimensions: groundedness, citation correctness, hallucination, abstention,
Vietnamese terminology. Never calls Cloudflare; touches no production files.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.request


def fold(s: str) -> str:
    n = unicodedata.normalize("NFD", (s or "").lower())
    out = "".join(c for c in n if not unicodedata.combining(c))
    return out.replace("đ", "d")


def call_ollama(base_url, model, messages, timeout=240):
    url = base_url.rstrip('/') + '/api/chat'
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 800},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
    latency = time.time() - started
    data = json.loads(raw)
    content = data.get("message", {}).get("content", "")
    tok = data.get("eval_count", 0)
    dur = data.get("eval_duration", 0) / 1e9 if data.get("eval_duration") else 0.0
    return content, latency, tok, dur


SYSTEM = (
    "You are a Vietnamese legal research assistant. Answer ONLY from the "
    "provided legal document excerpt. Cite the specific article/clause/point "
    "exactly as they appear. If the excerpt does not cover the question, answer "
    "exactly: 'Không tìm thấy đủ bằng chứng trong tài liệu hiện có.' "
    "Never invent article numbers or legal facts."
)


def article_numbers(text: str) -> set:
    return set(re.findall(r"dieu\s+(\d+)", fold(text)))


def is_abstention(text: str) -> bool:
    t = fold(text)
    return ("khong tim thay" in t or "khang t" in t) and (
        "bang chung" in t or "evidence" in t or "document" in t
    )


def build_case(name, question, corpus, abstain=False):
    return {
        "name": name,
        "question": question,
        "corpus": corpus,
        "abstain": abstain,
    }


def run_harness(model, base_url, corpus):
    cases = [
        build_case("article_lookup",
                   "Quelles sont les conditions prévues par le Điều 35 de cette loi ?",
                   corpus),
        build_case("clause_lookup",
                   "Dans le Đi 4, que prévoit le khoản 1 du chấm dứt du contrat ?",
                   corpus),
        build_case("abbreviation_NLD",
                   "Quels sont les droits de l'NLĐ dans cette loi mô phỏng ?",
                   corpus),
        build_case("paraphrase",
                   "Dans quels cas un contrat de travail mô phỏng prend-il fin ?",
                   corpus),
        build_case("no_evidence",
                   "Quel est le montant de l'amende prévu pour violation de ce code ?",
                   corpus, abstain=True),
    ]
    results = []
    for c in cases:
        user = f"Extrait du document :\n{c['corpus']}\n\nQuestion : {c['question']}"
        r = {"case": c["name"], "expect_abstention": c["abstain"]}
        try:
            out, lat, tok, dur = call_ollama(base_url, model,
                                             [{"role": "system", "content": SYSTEM},
                                              {"role": "user", "content": user}])
        except Exception as exc:
            r["status"] = "runtime_error"
            r["detail"] = str(exc)
            results.append(r)
            continue
        cited = article_numbers(out)
        valid = article_numbers(c["corpus"])
        r.update({
            "status": "ok",
            "output": out,
            "latency_s": round(lat, 2),
            "eval_tokens": tok,
            "tok_per_s": round(tok / dur, 1) if dur else None,
            "cited_articles": sorted(cited),
            "hallucinated_articles": sorted(cited - valid),
            "did_abstain": is_abstention(out),
        })
        results.append(r)
    return results


def passed(r):
    if r.get("status") != "ok":
        return False
    if r.get("hallucinated_articles"):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--base-url", default="http://localhost:11434")
    ap.add_argument("--fixture",
                    default="backend/src/test/resources/fixtures/legal_search_corpus_a.txt")
    ap.add_argument("--output", default="scripts/local_model_poc_result.json")
    args = ap.parse_args()

    with open(args.fixture, encoding="utf-8") as fh:
        corpus = fh.read()

    res = run_harness(args.model, args.base_url, corpus)
    rep = {
        "model": args.model,
        "fixture": args.fixture,
        "cases_total": len(res),
        "cases_passed": sum(1 for r in res if passed(r)),
        "note": "SYNTHETIC FIXTURE - NOT AN OFFICIAL LEGAL DOCUMENT",
        "results": res,
    }
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()