import asyncio
import aiohttp
import uuid
from datetime import datetime
import random
import time
import argparse
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample URLs for testing
SAMPLE_URLS = [
    "https://example.com/page-1",
    "https://example.com/page-2",
    "https://example.com/page-3",
    "https://example.com/products",
    "https://example.com/about",
    "https://example.com/contact",
    "https://example.com/blog",
    "https://example.com/pricing",
    "https://example.com/features",
    "https://example.com/docs"
]

async def generate_event() -> Dict:
    """Generate a random page view event."""
    return {
        "event_id": str(uuid.uuid4()),
        "user_id": f"user_{random.randint(1, 10000)}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "page_view",
        "payload": {
            "page_url": random.choice(SAMPLE_URLS)
        }
    }

async def send_event(session: aiohttp.ClientSession, url: str, event: Dict) -> bool:
    """Send a single event to the API."""
    try:
        async with session.post(url, json=event) as response:
            if response.status == 201:
                return True
            else:
                logger.error(f"Failed to send event {event['event_id']}: {response.status}")
                return False
    except Exception as e:
        logger.error(f"Error sending event {event['event_id']}: {str(e)}")
        return False

async def send_batch(session: aiohttp.ClientSession, url: str, batch_size: int) -> tuple[int, int]:
    """Send a batch of events concurrently."""
    events = [await generate_event() for _ in range(batch_size)]
    tasks = [send_event(session, url, event) for event in events]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = sum(1 for r in results if r is True)
    failures = batch_size - successes
    
    return successes, failures

async def run_load_test(
    api_url: str,
    total_requests: int,
    batch_size: int,
    requests_per_second: int
) -> None:
    """
    Run the load test with specified parameters.
    
    Args:
        api_url: The events API endpoint URL
        total_requests: Total number of requests to send
        batch_size: Number of concurrent requests per batch
        requests_per_second: Target requests per second
    """
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=None)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        start_time = time.time()
        total_successes = 0
        total_failures = 0
        batches_sent = 0
        
        logger.info(f"Starting load test - Target: {requests_per_second} req/s, Total: {total_requests}")
        
        while total_successes + total_failures < total_requests:
            batch_start = time.time()
            
            # Calculate actual batch size (don't exceed remaining requests)
            remaining = total_requests - (total_successes + total_failures)
            current_batch_size = min(batch_size, remaining)
            
            # Send batch
            successes, failures = await send_batch(session, api_url, current_batch_size)
            total_successes += successes
            total_failures += failures
            batches_sent += 1
            
            # Calculate sleep time to maintain target rate
            batch_duration = time.time() - batch_start
            target_duration = current_batch_size / requests_per_second
            sleep_time = max(0, target_duration - batch_duration)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            
            # Log progress
            elapsed = time.time() - start_time
            current_rate = (total_successes + total_failures) / elapsed
            logger.info(
                f"Progress: {total_successes + total_failures}/{total_requests} "
                f"({(total_successes + total_failures) * 100 / total_requests:.1f}%) - "
                f"Rate: {current_rate:.1f} req/s"
            )

    # Final statistics
    total_time = time.time() - start_time
    final_rate = (total_successes + total_failures) / total_time
    
    logger.info("\nLoad Test Results:")
    logger.info(f"Total Requests Sent: {total_successes + total_failures}")
    logger.info(f"Successful Requests: {total_successes}")
    logger.info(f"Failed Requests: {total_failures}")
    logger.info(f"Total Time: {total_time:.2f} seconds")
    logger.info(f"Average Rate: {final_rate:.1f} requests/second")
    logger.info(f"Success Rate: {(total_successes * 100) / (total_successes + total_failures):.1f}%")

def main():
    parser = argparse.ArgumentParser(description="Load test for events API")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/events",
        help="Events API endpoint URL"
    )
    parser.add_argument(
        "--total",
        type=int,
        default=10000,
        help="Total number of requests to send"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of concurrent requests per batch"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=500,
        help="Target requests per second"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_load_test(
            api_url=args.url,
            total_requests=args.total,
            batch_size=args.batch_size,
            requests_per_second=args.rate
        ))
    except KeyboardInterrupt:
        logger.info("\nLoad test interrupted by user")
    except Exception as e:
        logger.error(f"Load test failed: {str(e)}")

if __name__ == "__main__":
    main() 