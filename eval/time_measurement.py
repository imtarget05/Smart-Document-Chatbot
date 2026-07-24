"""Real time measurement: Dashboard vs Manual Process

Measures actual time for 5 tasks × 2 runs each.
User clicks Enter when starting/stopping each task.

Usage:
    python eval/time_measurement.py

    Follow prompts:
    - Enter when you START a task
    - Enter when you STOP a task

    Tasks measured:
    1. Upload 3 PDFs → Dashboard shows answer (vs manual search: open each PDF → find answer)
    2. Ask 5 questions → Dashboard answers (vs manual: search each doc → copy answer)
    3. Generate summary report → Dashboard (vs manual: read + write summary)
    4. Compare 2 contract terms → Dashboard (vs manual: open 2 PDFs side-by-side)
    5. Find specific clause → Dashboard (vs manual: search through each PDF)
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

TASKS = [
    {
        "id": 1,
        "name": "Upload 3 PDFs + get answer",
        "description": "Upload 3 contract PDFs and ask a question about payment terms",
        "manual_steps": [
            "1. Open first PDF, scroll to payment section",
            "2. Open second PDF, scroll to payment section",
            "3. Open third PDF, scroll to payment section",
            "4. Compare and write answer manually",
        ],
        "dashboard_steps": [
            "1. Drag & drop 3 PDFs into dashboard",
            "2. Ask 'What are the payment terms in these contracts?'",
            "3. Copy dashboard answer",
        ],
    },
    {
        "id": 2,
        "name": "Answer 5 document questions",
        "description": "Answer 5 specific questions about document content",
        "manual_steps": [
            "1. Open PDF, search for keyword",
            "2. Read and extract answer",
            "3. Repeat for each question",
        ],
        "dashboard_steps": [
            "1. Type each question in chat",
            "2. Copy answers from dashboard",
        ],
    },
    {
        "id": 3,
        "name": "Generate summary report",
        "description": "Generate a summary report of all uploaded documents",
        "manual_steps": [
            "1. Read each document",
            "2. Write summary notes",
            "3. Compile into report format",
        ],
        "dashboard_steps": [
            "1. Click 'Generate Report' button",
            "2. Review generated report",
            "3. Export/copy report",
        ],
    },
    {
        "id": 4,
        "name": "Compare 2 contract terms",
        "description": "Compare specific terms between 2 contracts",
        "manual_steps": [
            "1. Open both PDFs side by side",
            "2. Find relevant section in each",
            "3. Compare and note differences",
        ],
        "dashboard_steps": [
            "1. Ask 'Compare payment terms in Contract A vs Contract B'",
            "2. Review comparison result",
        ],
    },
    {
        "id": 5,
        "name": "Find specific clause",
        "description": "Find a specific legal clause across all documents",
        "manual_steps": [
            "1. Open each PDF",
            "2. Search/scroll for the clause",
            "3. Note which documents have it",
        ],
        "dashboard_steps": [
            "1. Ask 'Find termination clauses in all documents'",
            "2. Review results",
        ],
    },
]


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def measure_single_task(task, run_number):
    """Measure time for one task with user input."""
    print(f"\n{'=' * 60}")
    print(f"Task {task['id']}: {task['name']}")
    print(f"Run {run_number} of 2")
    print(f"{'=' * 60}")

    print(f"\nDescription: {task['description']}")
    print("\n--- MANUAL PROCESS ---")
    for step in task["manual_steps"]:
        print(f"  {step}")

    print("\n--- DASHBOARD PROCESS ---")
    for step in task["dashboard_steps"]:
        print(f"  {step}")

    # Measure manual process
    print("\n🔵 MANUAL: Press ENTER when you START the manual process...")
    input()
    start_manual = time.time()
    print(f"   Started at: {get_timestamp()}")
    print("   Doing the manual process now...")

    print("\n🔵 MANUAL: Press ENTER when you FINISH the manual process...")
    input()
    end_manual = time.time()
    manual_time = end_manual - start_manual
    print(f"   Finished at: {get_timestamp()}")
    print(f"   ⏱  Manual time: {manual_time:.1f} seconds")

    # Measure dashboard process
    print("\n🟢 DASHBOARD: Press ENTER when you START the dashboard process...")
    input()
    start_dashboard = time.time()
    print(f"   Started at: {get_timestamp()}")
    print("   Using the dashboard now...")

    print("\n🟢 DASHBOARD: Press ENTER when you FINISH the dashboard process...")
    input()
    end_dashboard = time.time()
    dashboard_time = end_dashboard - start_dashboard
    print(f"   Finished at: {get_timestamp()}")
    print(f"   ⏱  Dashboard time: {dashboard_time:.1f} seconds")

    time_saved = manual_time - dashboard_time
    speedup = manual_time / dashboard_time if dashboard_time > 0 else 0

    print(f"\n📊 Results for Task {task['id']}:")
    print(f"   Manual:      {manual_time:.1f}s")
    print(f"   Dashboard:   {dashboard_time:.1f}s")
    print(f"   Time saved:  {time_saved:.1f}s")
    print(f"   Speedup:     {speedup:.1f}x faster")

    return {
        "task_id": task["id"],
        "task_name": task["name"],
        "run": run_number,
        "manual_seconds": round(manual_time, 1),
        "dashboard_seconds": round(dashboard_time, 1),
        "time_saved_seconds": round(time_saved, 1),
        "speedup_factor": round(speedup, 1),
        "timestamp": get_timestamp(),
    }


def run_measurement():
    """Run all measurements."""
    print("=" * 60)
    print("REAL TIME MEASUREMENT: Dashboard vs Manual Process")
    print("=" * 60)
    print(f"Date: {get_timestamp()}")
    print(f"Tasks: {len(TASKS)}")
    print("Runs per task: 2")
    print(f"Total measurements: {len(TASKS) * 2}")
    print("\nInstructions:")
    print("- Read each task description")
    print("- Press ENTER when you START each process")
    print("- Press ENTER when you FINISH each process")
    print("- Be honest! Real numbers, not estimated")
    print("\nReady? Press ENTER to start...")
    input()

    all_results = []

    for task in TASKS:
        for run in [1, 2]:
            result = measure_single_task(task, run)
            all_results.append(result)

    # Calculate summary
    task_ids = list(range(1, len(TASKS) + 1))
    summary_by_task = []

    for task_id in task_ids:
        task_results = [r for r in all_results if r["task_id"] == task_id]
        avg_manual = sum(r["manual_seconds"] for r in task_results) / len(task_results)
        avg_dashboard = sum(r["dashboard_seconds"] for r in task_results) / len(
            task_results
        )
        avg_saved = sum(r["time_saved_seconds"] for r in task_results) / len(
            task_results
        )
        avg_speedup = sum(r["speedup_factor"] for r in task_results) / len(task_results)

        summary_by_task.append(
            {
                "task_id": task_id,
                "task_name": TASKS[task_id - 1]["name"],
                "avg_manual_seconds": round(avg_manual, 1),
                "avg_dashboard_seconds": round(avg_dashboard, 1),
                "avg_time_saved_seconds": round(avg_saved, 1),
                "avg_speedup_factor": round(avg_speedup, 1),
            }
        )

    total_manual = sum(s["avg_manual_seconds"] for s in summary_by_task)
    total_dashboard = sum(s["avg_dashboard_seconds"] for s in summary_by_task)
    total_saved = total_manual - total_dashboard
    overall_speedup = total_manual / total_dashboard if total_dashboard > 0 else 0

    final_summary = {
        "measurement_date": get_timestamp(),
        "total_tasks": len(TASKS),
        "runs_per_task": 2,
        "total_measurements": len(all_results),
        "results_by_task": summary_by_task,
        "overall_summary": {
            "total_manual_seconds": round(total_manual, 1),
            "total_dashboard_seconds": round(total_dashboard, 1),
            "total_time_saved_seconds": round(total_saved, 1),
            "overall_speedup_factor": round(overall_speedup, 1),
            "percentage_faster": round((1 - total_dashboard / total_manual) * 100, 1)
            if total_manual > 0
            else 0,
        },
    }

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"time_measurement_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(final_summary, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'=' * 60}")
    print("FINAL RESULTS")
    print(f"{'=' * 60}")

    for item in summary_by_task:
        print(f"\nTask {item['task_id']}: {item['task_name']}")
        print(
            f"  Manual: {item['avg_manual_seconds']:.1f}s | Dashboard: {item['avg_dashboard_seconds']:.1f}s | Saved: {item['avg_time_saved_seconds']:.1f}s | Speedup: {item['avg_speedup_factor']:.1f}x"
        )

    print(f"\n{'=' * 60}")
    print("OVERALL SUMMARY")
    print(f"{'=' * 60}")
    print(
        f"Total manual time:     {total_manual:.1f} seconds ({total_manual / 60:.1f} minutes)"
    )
    print(
        f"Total dashboard time:  {total_dashboard:.1f} seconds ({total_dashboard / 60:.1f} minutes)"
    )
    print(
        f"Total time saved:      {total_saved:.1f} seconds ({total_saved / 60:.1f} minutes)"
    )
    print(f"Overall speedup:       {overall_speedup:.1f}x faster")
    print(f"Percentage faster:     {(1 - total_dashboard / total_manual) * 100:.1f}%")
    print(f"\nResults saved to: {results_file}")
    print("\n⚠️  These are YOUR REAL measured numbers. Use them in your CV!")

    return final_summary


if __name__ == "__main__":
    try:
        run_measurement()
    except KeyboardInterrupt:
        print("\n\nMeasurement cancelled.")
        sys.exit(1)
