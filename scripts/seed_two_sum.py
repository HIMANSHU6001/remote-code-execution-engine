import asyncio
import uuid
import json
from sqlalchemy import select, text
from db.base import AsyncSessionLocal
from db.models import Problem, TestCase, ProblemLanguageConfig
from shared.enums import SupportedLanguage

async def seed_two_sum():
    async with AsyncSessionLocal() as session:
        # 1. Find Two Sum Problem
        res = await session.execute(select(Problem).where(Problem.title == "Two Sum"))
        problem = res.unique().scalar_one_or_none()
        if not problem:
            print("Two Sum problem not found. Please run seed_problems_v2.py first.")
            return

        # 2. Update Drivers for JSON Input (Python & Node)
        # Python Driver
        py_driver = """import sys
import json

def main():
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
        nums = data['nums']
        target = data['target']
        sol = Solution()
        res = sol.twoSum(nums, target)
        print('\\n---RCE_EXEC_{job_id}---')
        print(json.dumps(res))
    except Exception as e:
        print('\\n---RCE_EXEC_{job_id}---')
        print(json.dumps({'error': str(e)}))

if __name__ == '__main__':
    main()
"""
        # Node.js Driver
        node_driver = """const fs = require('fs');

function main() {
    try {
        const rawInput = fs.readFileSync(0, 'utf-8');
        const data = JSON.parse(rawInput);
        const { nums, target } = data;
        const sol = new Solution();
        const res = sol.twoSum(nums, target);
        console.log('\\n---RCE_EXEC_{job_id}---');
        console.log(JSON.stringify(res));
    } catch (e) {
        console.log('\\n---RCE_EXEC_{job_id}---');
        console.log(JSON.stringify({error: e.toString()}));
    }
}
main();
"""

        # Update configs in DB
        await session.execute(
            text("UPDATE problem_language_configs SET driver_code = :code WHERE problem_id = :pid AND language = 'python'"),
            {"code": py_driver, "pid": problem.id}
        )
        await session.execute(
            text("UPDATE problem_language_configs SET driver_code = :code WHERE problem_id = :pid AND language = 'nodejs'"),
            {"code": node_driver, "pid": problem.id}
        )

        # 3. Clear existing test cases for Two Sum
        await session.execute(text("DELETE FROM test_cases WHERE problem_id = :pid"), {"pid": problem.id})
        
        # 4. Define Test Cases
        test_cases = [
            # Samples (3)
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "output": [0, 1], "is_sample": True},
            {"input": {"nums": [3, 2, 4], "target": 6}, "output": [1, 2], "is_sample": True},
            {"input": {"nums": [3, 3], "target": 6}, "output": [0, 1], "is_sample": True},
            
            # Hidden (12)
            {"input": {"nums": [1, 2, 3], "target": 5}, "output": [1, 2], "is_sample": False},
            {"input": {"nums": [10, 20, 30, 40], "target": 50}, "output": [0, 3], "is_sample": False},
            {"input": {"nums": [-1, -2, -3, -4, -5], "target": -8}, "output": [2, 4], "is_sample": False},
            {"input": {"nums": [0, 4, 3, 0], "target": 0}, "output": [0, 3], "is_sample": False},
            {"input": {"nums": [-3, 4, 3, 90], "target": 0}, "output": [0, 2], "is_sample": False},
            {"input": {"nums": [5, 25, 75, 10], "target": 100}, "output": [1, 2], "is_sample": False},
            {"input": {"nums": [1, 5, 8, 3], "target": 11}, "output": [2, 3], "is_sample": False},
            {"input": {"nums": [100, 200, 300, 400], "target": 700}, "output": [2, 3], "is_sample": False},
            {"input": {"nums": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "target": 19}, "output": [8, 9], "is_sample": False},
            {"input": {"nums": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "target": 3}, "output": [0, 1], "is_sample": False},
            {"input": {"nums": [2, 5, 5, 11], "target": 10}, "output": [1, 2], "is_sample": False},
            {"input": {"nums": [3, 2, 3], "target": 6}, "output": [0, 2], "is_sample": False},
        ]

        for i, tc in enumerate(test_cases, 1):
            new_tc = TestCase(
                id=uuid.uuid4(),
                problem_id=problem.id,
                input_data=json.dumps(tc["input"]),
                expected_output=json.dumps(tc["output"]),
                is_sample=tc["is_sample"],
                ordering=i
            )
            session.add(new_tc)

        await session.commit()
        print(f"Seeded 15 test cases for {problem.title}")

if __name__ == "__main__":
    asyncio.run(seed_two_sum())
