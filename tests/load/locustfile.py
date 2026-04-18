"""
Quality Infrastructure — Load Testing with Locust
Simulates realistic user traffic patterns against the API.
"""

import random
import json
import time
from locust import HttpUser, task, between, events
from typing import Optional

# Test data (from knowledge base)
TEST_QUESTIONS = [
    "What is the current state of the swarm?",
    "How does hyperdimensional computing work?",
    "Translate 'hello' to French",
    "Explain HDC vector algebra",
    "What are the benefits of CPU-less AI?",
    "Analyze semantic bootstrapping",
    "How does cognitive compression work?",
]

TEST_MESSAGES = [
    [{"role": "user", "content": "Hello, swarm!"}],
    [{"role": "user", "content": "Tell me about HDC"}, {"role": "assistant", "content": "Sure, here's..."}],
]


class ChatUser(HttpUser):
    """
    Simulates a user making chat completions requests.
    Waits 1-3 seconds between requests.
    """
    wait_time = between(1, 3)
    
    @task(3)
    def chat_completion(self):
        payload = {
            "model": "hardwareless-core",
            "messages": [
                {"role": "user", "content": random.choice(TEST_QUESTIONS)}
            ]
        }
        with self.client.post("/v1/chat/completions", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
    
    @task(2)
    def simple_chat(self):
        question = random.choice(TEST_QUESTIONS)
        with self.client.post("/chat", json={"question": question}, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
    
    @task(1)
    def translate(self):
        payload = {
            "text": "Hello world",
            "source_lang": "en",
            "target_lang": random.choice(["es", "fr", "de", "zh", "ja"])
        }
        with self.client.post("/translate", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class BatchUser(HttpUser):
    """
    Simulates bulk/batch API usage.
    """
    wait_time = between(5, 10)
    
    @task
    def batch_translate(self):
        payload = {
            "operations": [
                {"id": f"t{i}", "text": f"Test phrase {i}", "target_lang": random.choice(["es", "fr"])}
                for i in range(10)
            ],
            "continue_on_error": True,
        }
        with self.client.post("/v1/batch/translate", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("error_count", 0) < 5:
                    resp.success()
                else:
                    resp.failure("Too many batch errors")
            else:
                resp.failure(f"HTTP {resp.status_code}")
    
    @task
    def batch_chat(self):
        payload = {
            "operations": [
                {"id": f"q{i}", "question": random.choice(TEST_QUESTIONS)}
                for i in range(5)
            ]
        }
        with self.client.post("/v1/batch/chat", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


# Metrics event hooks
@events.request.add_listener
def log_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Custom logging for request metrics."""
    if exception:
        # Could send to custom metrics backend
        pass


# Run: locust -f tests/load/locustfile.py --host=http://localhost:8000
# Then open http://localhost:8089 to control simulation
