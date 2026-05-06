import asyncio

from sqlalchemy import select

from db.base import AsyncSessionLocal
from db.models import Topic

DEFAULT_TOPICS = [
    {"name": "Array", "slug": "array"},
    {"name": "String", "slug": "string"},
    {"name": "Hash Table", "slug": "hash-table"},
    {"name": "Linked List", "slug": "linked-list"},
    {"name": "Stack", "slug": "stack"},
    {"name": "Queue", "slug": "queue"},
    {"name": "Tree", "slug": "tree"},
    {"name": "Binary Tree", "slug": "binary-tree"},
    {"name": "Binary Search Tree", "slug": "binary-search-tree"},
    {"name": "Heap", "slug": "heap"},
    {"name": "Graph", "slug": "graph"},
    {"name": "Trie", "slug": "trie"},
    {"name": "Two Pointers", "slug": "two-pointers"},
    {"name": "Sliding Window", "slug": "sliding-window"},
    {"name": "Binary Search", "slug": "binary-search"},
    {"name": "Depth-First Search", "slug": "depth-first-search"},
    {"name": "Breadth-First Search", "slug": "breadth-first-search"},
    {"name": "Backtracking", "slug": "backtracking"},
    {"name": "Dynamic Programming", "slug": "dynamic-programming"},
    {"name": "Memoization", "slug": "memoization"},
    {"name": "Greedy", "slug": "greedy"},
    {"name": "Prefix Sum", "slug": "prefix-sum"},
    {"name": "Union-Find", "slug": "union-find"},
    {"name": "Topological Sort", "slug": "topological-sort"},
    {"name": "Shortest Path", "slug": "shortest-path"},
    {"name": "Bit Manipulation", "slug": "bit-manipulation"},
    {"name": "Divide and Conquer", "slug": "divide-and-conquer"},
    {"name": "Arrays & Hashing", "slug": "arrays-hashing"},
    {"name": "Graphs", "slug": "graphs"},
]


async def seed_topics() -> None:
    async with AsyncSessionLocal() as session:
        for topic_data in DEFAULT_TOPICS:
            result = await session.execute(select(Topic).where(Topic.slug == topic_data["slug"]))
            topic = result.scalar_one_or_none()
            if not topic:
                topic = Topic(name=topic_data["name"], slug=topic_data["slug"])
                session.add(topic)
                print(f"Added topic: {topic_data['name']}")
            else:
                print(f"Topic already exists: {topic_data['name']}")
        await session.commit()
        print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_topics())
