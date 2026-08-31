#!/usr/bin/env python3
"""
Load Testing Script for Smart Document Chatbot
Simulates concurrent users to test system performance.

Usage:
    python scripts/load_test.py --users 100 --duration 60
    python scripts/load_test.py --users 50 --duration 30 --ramp-up 10
"""

import argparse
import asyncio
import aiohttp
import time
import statistics
import json
from datetime import datetime
from typing import Optional

BASE_URL = "http://localhost:8080/api"

class LoadTest:
    def __init__(self, num_users: int, duration: int, ramp_up: int = 0):
        self.num_users = num_users
        self.duration = duration
        self.ramp_up = ramp_up
        self.results = []
        self.errors = []
        self.token = None
        self.csrf = None
        self.doc_id = None

    async def setup(self):
        """Login and upload test document."""
        async with aiohttp.ClientSession() as session:
            # Get CSRF
            async with session.get(f"{BASE_URL}/csrf") as resp:
                data = await resp.json()
                self.csrf = data["token"]
            
            # Login
            async with session.post(f"{BASE_URL}/auth/login", 
                    json={"username": "testuser", "password": "TestPass123!"},
                    headers={"X-XSRF-TOKEN": self.csrf}) as resp:
                data = await resp.json()
                self.token = data["token"]
            
            # Upload document
            doc_content = "LUẬT DOANH NGHIỆP 2020. Điều 7: Hình thức doanh nghiệp. Điều 10: Thủ tục thành lập."
            data = aiohttp.FormData()
            data.add_field("file", doc_content.encode(), filename="load_test.txt", content_type="text/plain")
            
            async with session.post(f"{BASE_URL}/documents/upload",
                    data=data,
                    headers={"Authorization": f"Bearer {self.token}", "X-XSRF-TOKEN": self.csrf}) as resp:
                result = await resp.json()
                self.doc_id = result.get("documentId")
            
            print(f"Setup complete: token=...{self.token[-10:]}, doc_id={self.doc_id}")

    async def user_session(self, user_id: int):
        """Simulate a single user session."""
        await asyncio.sleep((self.ramp_up / self.num_users) * user_id)  # Ramp up
        
        session_start = time.time()
        session_results = []
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "X-XSRF-TOKEN": self.csrf,
                "Content-Type": "application/json"
            }
            
            questions = [
                "Điều 7 quy định gì?",
                "Điều 10 quy định gì?",
                "Công ty cổ phần là gì?",
                "Quyền của cổ đông?",
                "Nghĩa vụ doanh nghiệp?",
            ]
            
            end_time = session_start + self.duration
            q_idx = 0
            
            while time.time() < end_time:
                q = questions[q_idx % len(questions)]
                q_idx += 1
                
                start = time.time()
                try:
                    async with session.post(f"{BASE_URL}/chat/ask",
                            json={
                                "sessionId": f"load-{user_id}",
                                "documentId": self.doc_id,
                                "message": q
                            },
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=120)) as resp:
                        latency = (time.time() - start) * 1000
                        
                        if resp.status == 200:
                            data = await resp.json()
                            session_results.append({
                                "user_id": user_id,
                                "status": 200,
                                "latency_ms": latency,
                                "confidence": data.get("confidence", "unknown"),
                                "rag_strategy": data.get("ragStrategy", "unknown")
                            })
                        elif resp.status == 429:
                            session_results.append({
                                "user_id": user_id,
                                "status": 429,
                                "latency_ms": latency,
                                "confidence": None,
                                "rag_strategy": "rate_limited"
                            })
                        else:
                            self.errors.append({
                                "user_id": user_id,
                                "status": resp.status,
                                "error": await resp.text()
                            })
                except Exception as e:
                    self.errors.append({
                        "user_id": user_id,
                        "status": 0,
                        "error": str(e)
                    })
                
                # Small delay between requests (simulate user thinking)
                await asyncio.sleep(0.5)
        
        self.results.extend(session_results)

    async def run(self):
        """Run the load test."""
        print(f"\n🚀 Load Test Starting")
        print(f"   Users: {self.num_users}")
        print(f"   Duration: {self.duration}s")
        print(f"   Ramp-up: {self.ramp_up}s")
        print(f"   Target: {BASE_URL}")
        print()
        
        await self.setup()
        
        start_time = time.time()
        
        # Launch all users
        tasks = [self.user_session(i) for i in range(self.num_users)]
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Report
        self.report(total_time)

    def report(self, total_time: float):
        """Generate test report."""
        if not self.results:
            print("❌ No results collected")
            return
        
        latencies = [r["latency_ms"] for r in self.results if r["status"] == 200]
        successes = len([r for r in self.results if r["status"] == 200])
        rate_limited = len([r for r in self.results if r["status"] == 429])
        total_requests = len(self.results)
        
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Total Requests: {total_requests}")
        print(f"Successful (200): {successes}")
        print(f"Rate Limited (429): {rate_limited}")
        print(f"Errors: {len(self.errors)}")
        print(f"Total Time: {total_time:.1f}s")
        print()
        
        if latencies:
            print(f"Latency (successful requests):")
            print(f"  Avg: {statistics.mean(latencies):.0f}ms")
            print(f"  Min: {min(latencies):.0f}ms")
            print(f"  Max: {max(latencies):.0f}ms")
            print(f"  P50: {statistics.median(latencies):.0f}ms")
            print(f"  P95: {sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms")
            print(f"  P99: {sorted(latencies)[int(len(latencies)*0.99)]:.0f}ms")
            print()
        
        if total_time > 0:
            print(f"Throughput: {total_requests/total_time:.2f} req/s")
            print(f"Success Rate: {successes/total_requests*100:.1f}%")
        
        # Save results
        results_file = f"load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump({
                "config": {
                    "users": self.num_users,
                    "duration": self.duration,
                    "ramp_up": self.ramp_up
                },
                "summary": {
                    "total_requests": total_requests,
                    "successes": successes,
                    "rate_limited": rate_limited,
                    "errors": len(self.errors),
                    "total_time": total_time,
                    "throughput": total_requests/total_time if total_time > 0 else 0,
                    "success_rate": successes/total_requests if total_requests > 0 else 0,
                    "latency_avg": statistics.mean(latencies) if latencies else 0,
                    "latency_p95": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0
                },
                "results": self.results,
                "errors": self.errors[:100]  # Limit stored errors
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Test Smart Document Chatbot")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--ramp-up", type=int, default=0, help="Ramp-up time in seconds")
    args = parser.parse_args()
    
    test = LoadTest(args.users, args.duration, args.ramp_up)
    asyncio.run(test.run())
