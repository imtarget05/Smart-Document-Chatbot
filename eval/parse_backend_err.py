#!/usr/bin/env python3
"""Extract the last 'Caused by' chain from docker logjason stack_trace."""
import json
import re
import subprocess
import sys

raw = subprocess.run(
    ["docker", "logs", "smart-document-chatbox-backend"],
    capture_output=True, text=True,
).stderr + subprocess.run(
    ["docker", "logs", "smart-document-chatbox-backend"],
    capture_output=True, text=True,
).stdout

# find last stack_trace JSON field
hits = re.findall(r'"stack_trace":"(.*?)","applicationName"', raw, re.S)
if not hits:
    print("no stack_trace found")
    sys.exit(0)
st = hits[-1]
st = st.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
lines = st.splitlines()
# print from last "Caused by" to end
idx = max(i for i, l in enumerate(lines) if "Caused by" in l)
for l in lines[idx:]:
    if l.strip().startswith("at") and ("java." in l or "jdk." in l):
        continue  # skip JDK frames
    print(l[:160])
