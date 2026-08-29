# Smart Document Chatbot — Agent Context

RAG chatbot over documents. Stack: Python backend (FastAPI) + TypeScript/React frontend, plus airflow/docker/eval/finetune modules.

## ABSOLUTE PATH (MUST cd here before any command)
Repo root: /Users/mainguyenbinhtan/Downloads/Smart-Document-Chatbot
ALWAYS prefix terminal commands with: `cd /Users/mainguyenbinhtan/Downloads/Smart-Document-Chatbot && ...`
The channel session has cwd=None — an unqualified `git`/`npm`/`mvn` fails with "not a git repository". NEVER run commands without the absolute cd.

## Commands (use full absolute paths)
- Audit backend: `cd /Users/mainguyenbinhtan/Downloads/Smart-Document-Chatbot/backend && export JAVA_HOME=/opt/homebrew/opt/openjdk@17 && export PATH=$JAVA_HOME/bin:$PATH && mvn -q test 2>&1 | tail -15`
  (JDK 26 default breaks Mockito inline → 108 errors; MUST use JDK17)
- Audit frontend: `cd /Users/mainguyenbinhtan/Downloads/Smart-Document-Chatbot/frontend && npm test -- --run 2>&1 | tail -15`
- Git status: `cd /Users/mainguyenbinhtan/Downloads/Smart-Document-Chatbot && git status --short | head -20`
- Last commit: `cd /Users/mainguyenbinhtan/Downloads/Smart-Document-Chatbot && git log -1 --oneline`

## Current state (2026-08-29)
- Active project being driven via Telegram channel -1003941012831 (Smart document chatbot).
- User asks the agent to "xử lý tiếp toàn bộ task" / "check dự án hoàn thành tới đâu" — agent should actually run build+test and report a real status table, not just chat.

## Conventions
- Report must cover git status + last commit + build + test per suite (backend/frontend) + WIP detection + summary table with pass/fail.
- Use real output from commands; never fabricate test results.

## Delivery
Project progress reports go to Telegram channel -1003941012831 (Smart document chatbot).
