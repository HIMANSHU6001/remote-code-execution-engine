import asyncio
import json
import time

from sqlalchemy import select

from auth.security import hash_password
from db.base import AsyncSessionLocal
from db.models import Problem, ProblemLanguageConfig, TestCase, Topic, User
from shared.enums import Difficulty, SupportedLanguage


async def seed_database():
    async with AsyncSessionLocal() as db:
        print("Starting database seed...")

        # ==========================================
        # 1. CREATE SYSTEM ADMIN USER
        # ==========================================
        result = await db.execute(select(User).filter_by(email="admin@system.local"))
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                email="admin@system.local",
                name="Himanshu Kaushik",
                role="admin",
                is_verified=True,
                password_hash=hash_password("admin123"),
            )
            db.add(admin_user)
            await db.flush()
            print("Created Admin User.")

        # ==========================================
        # 2. SEED TOPICS
        # ==========================================
        topics_data = [
            {"id": 1,  "name": "Array",                "slug": "array"},
            {"id": 2,  "name": "Hash Table",           "slug": "hash-table"},
            {"id": 3,  "name": "Linked List",          "slug": "linked-list"},
            {"id": 4,  "name": "Math",                 "slug": "math"},
            {"id": 5,  "name": "Dynamic Programming",  "slug": "dynamic-programming"},
            {"id": 6,  "name": "String",               "slug": "string"},
            {"id": 7,  "name": "Two Pointers",         "slug": "two-pointers"},
            {"id": 8,  "name": "Sliding Window",       "slug": "sliding-window"},
            {"id": 9,  "name": "Stack",                "slug": "stack"},
            {"id": 10, "name": "Binary Search",        "slug": "binary-search"},
            {"id": 11, "name": "Tree",                 "slug": "tree"},
            {"id": 12, "name": "Graph",                "slug": "graph"},
            {"id": 13, "name": "Sorting",              "slug": "sorting"},
            {"id": 14, "name": "Greedy",               "slug": "greedy"},
            {"id": 15, "name": "Backtracking",         "slug": "backtracking"},
        ]

        topic_map = {}
        for td in topics_data:
            topic = await db.get(Topic, td["id"])
            if not topic:
                topic = Topic(id=td["id"], name=td["name"], slug=td["slug"])
                db.add(topic)
            topic_map[td["name"]] = topic
        await db.flush()
        print("Topics seeded.")

        # ==========================================
        # 3. SEED PROBLEMS
        # ==========================================
        problems_data = [
            # ── EASY ──────────────────────────────────────────────────────
            {
                "title": "Two Sum",
                "description": (
                    "Given an array of integers `nums` and an integer `target`, return the "
                    "**indices** of the two numbers such that they add up to `target`.\n\n"
                    "You may assume that each input would have **exactly one solution**, and "
                    "you may not use the same element twice. You can return the answer in any order.\n\n"
                    "**Example 1:**\n```\nInput:  nums = [2,7,11,15], target = 9\nOutput: [0,1]\n"
                    "Explanation: nums[0] + nums[1] = 2 + 7 = 9\n```\n\n"
                    "**Example 2:**\n```\nInput:  nums = [3,2,4], target = 6\nOutput: [1,2]\n```\n\n"
                    "**Constraints:**\n"
                    "- `2 <= nums.length <= 10⁴`\n"
                    "- `-10⁹ <= nums[i] <= 10⁹`\n"
                    "- `-10⁹ <= target <= 10⁹`\n"
                    "- Only one valid answer exists.\n\n"
                    "**Follow-up:** Can you come up with an algorithm that is less than O(n²) time complexity?"
                ),
                "difficulty": Difficulty.EASY,
                "base_time_limit_ms": 1000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Hash Table"],
                "hints": [
                    "A brute force way would be to search for all possible pairs, but that's O(n²).",
                    "Can we use a hash map to store indices of seen numbers and find the complement in O(1)?"
                ],
            },
            {
                "title": "Reverse Linked List",
                "description": (
                    "Given the `head` of a singly linked list, reverse the list, and return "
                    "the *reversed list*.\n\n"
                    "**Example 1:**\n```\nInput:  head = [1,2,3,4,5]\nOutput: [5,4,3,2,1]\n```\n\n"
                    "**Example 2:**\n```\nInput:  head = [1,2]\nOutput: [2,1]\n```\n\n"
                    "**Example 3:**\n```\nInput:  head = []\nOutput: []\n```\n\n"
                    "**Constraints:**\n"
                    "- The number of nodes in the list is in the range `[0, 5000]`.\n"
                    "- `-5000 <= Node.val <= 5000`\n\n"
                    "**Follow-up:** A linked list can be reversed either iteratively or recursively. "
                    "Could you implement both?"
                ),
                "difficulty": Difficulty.EASY,
                "base_time_limit_ms": 1000,
                "base_memory_limit_mb": 256,
                "topics": ["Linked List"],
                "hints": [
                    "Iteratively: Keep track of prev, curr, and next nodes as you traverse.",
                    "Recursively: Reverse the rest of the list first, then fix the head."
                ],
            },
            {
                "title": "Valid Parentheses",
                "description": (
                    "Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, "
                    "`'['` and `']'`, determine if the input string is **valid**.\n\n"
                    "An input string is valid if:\n"
                    "1. Open brackets must be closed by the same type of brackets.\n"
                    "2. Open brackets must be closed in the correct order.\n"
                    "3. Every close bracket has a corresponding open bracket of the same type.\n\n"
                    "**Example 1:**\n```\nInput:  s = \"()\"\nOutput: true\n```\n\n"
                    "**Example 2:**\n```\nInput:  s = \"()[]{}\"\nOutput: true\n```\n\n"
                    "**Example 3:**\n```\nInput:  s = \"(]\"\nOutput: false\n```\n\n"
                    "**Constraints:**\n"
                    "- `1 <= s.length <= 10⁴`\n"
                    "- `s` consists of parentheses only `'()[]{}'`."
                ),
                "difficulty": Difficulty.EASY,
                "base_time_limit_ms": 1000,
                "base_memory_limit_mb": 256,
                "topics": ["String", "Stack"],
                "hints": [
                    "A stack is perfect here: push open brackets, pop and match when you see a closing one.",
                    "Ensure the stack is empty at the end for a valid string."
                ],
            },
            {
                "title": "Binary Search",
                "description": (
                    "Given an array of integers `nums` which is sorted in ascending order, and an "
                    "integer `target`, write a function to search `target` in `nums`. If `target` "
                    "exists, return its index. Otherwise, return `-1`.\n\n"
                    "You must write an algorithm with **O(log n)** runtime complexity.\n\n"
                    "**Example 1:**\n```\nInput:  nums = [-1,0,3,5,9,12], target = 9\nOutput: 4\n"
                    "Explanation: 9 exists in nums and its index is 4\n```\n\n"
                    "**Example 2:**\n```\nInput:  nums = [-1,0,3,5,9,12], target = 2\nOutput: -1\n"
                    "Explanation: 2 does not exist in nums so return -1\n```\n\n"
                    "**Constraints:**\n"
                    "- `1 <= nums.length <= 10⁴`\n"
                    "- `-10⁴ < nums[i], target < 10⁴`\n"
                    "- All the integers in `nums` are **unique**.\n"
                    "- `nums` is sorted in ascending order."
                ),
                "difficulty": Difficulty.EASY,
                "base_time_limit_ms": 1000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Binary Search"],
                "hints": [
                    "Maintain low and high pointers. Check the middle element in each step.",
                    "If target < middle, high = mid - 1; otherwise, low = mid + 1."
                ],
            },
            # ── MEDIUM ────────────────────────────────────────────────────
            {
                "title": "Maximum Subarray",
                "description": (
                    "Given an integer array `nums`, find the **subarray** with the largest sum, "
                    "and return *its sum*.\n\n"
                    "**Example 1:**\n```\nInput:  nums = [-2,1,-3,4,-1,2,1,-5,4]\nOutput: 6\n"
                    "Explanation: The subarray [4,-1,2,1] has the largest sum 6.\n```\n\n"
                    "**Example 2:**\n```\nInput:  nums = [1]\nOutput: 1\n```\n\n"
                    "**Example 3:**\n```\nInput:  nums = [5,4,-1,7,8]\nOutput: 23\n```\n\n"
                    "**Constraints:**\n"
                    "- `1 <= nums.length <= 10⁵`\n"
                    "- `-10⁴ <= nums[i] <= 10⁴`\n\n"
                    "**Follow-up:** If you have figured out the O(n) solution, try coding another "
                    "solution using the **divide and conquer** approach, which is more subtle."
                ),
                "difficulty": Difficulty.MEDIUM,
                "base_time_limit_ms": 2000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Dynamic Programming"],
                "hints": [
                    "Kadane's Algorithm: Keep track of the current subarray sum and the global max sum.",
                    "At each index, current_sum = max(nums[i], current_sum + nums[i])."
                ],
            },
            {
                "title": "Longest Substring Without Repeating Characters",
                "description": (
                    "Given a string `s`, find the length of the **longest substring** without "
                    "duplicate characters.\n\n"
                    "**Example 1:**\n```\nInput:  s = \"abcabcbb\"\nOutput: 3\n"
                    "Explanation: The answer is \"abc\", with the length of 3.\n```\n\n"
                    "**Example 2:**\n```\nInput:  s = \"bbbbb\"\nOutput: 1\n"
                    "Explanation: The answer is \"b\", with the length of 1.\n```\n\n"
                    "**Example 3:**\n```\nInput:  s = \"pwwkew\"\nOutput: 3\n"
                    "Explanation: The answer is \"wke\", with the length of 3.\n"
                    "Notice that the answer must be a substring, \"pwke\" is a subsequence and not a substring.\n```\n\n"
                    "**Constraints:**\n"
                    "- `0 <= s.length <= 5 * 10⁴`\n"
                    "- `s` consists of English letters, digits, symbols and spaces."
                ),
                "difficulty": Difficulty.MEDIUM,
                "base_time_limit_ms": 2000,
                "base_memory_limit_mb": 256,
                "topics": ["String", "Hash Table", "Sliding Window"],
                "hints": [
                    "Sliding Window: Use two pointers (i, j) to define the current substring.",
                    "Move j forward, and if a duplicate is found, move i forward until the duplicate is gone."
                ],
            },
            {
                "title": "3Sum",
                "description": (
                    "Given an integer array `nums`, return all the triplets "
                    "`[nums[i], nums[j], nums[k]]` such that `i != j`, `i != k`, `j != k`, "
                    "and `nums[i] + nums[j] + nums[k] == 0`.\n\n"
                    "Notice that the solution set must not contain duplicate triplets.\n\n"
                    "**Example 1:**\n```\nInput:  nums = [-1,0,1,2,-1,-4]\n"
                    "Output: [[-1,-1,2],[-1,0,1]]\n"
                    "Explanation:\nnums[0] + nums[1] + nums[2] = (-1) + 0 + 1 = 0.\n"
                    "nums[1] + nums[2] + nums[4] = 0 + 1 + (-1) = 0.\n"
                    "nums[0] + nums[3] + nums[4] = (-1) + 2 + (-1) = 0.\n"
                    "The distinct triplets are [-1,0,1] and [-1,-1,2].\n```\n\n"
                    "**Example 2:**\n```\nInput:  nums = [0,1,1]\nOutput: []\n```\n\n"
                    "**Example 3:**\n```\nInput:  nums = [0,0,0]\nOutput: [[0,0,0]]\n```\n\n"
                    "**Constraints:**\n"
                    "- `3 <= nums.length <= 3000`\n"
                    "- `-10⁵ <= nums[i] <= 10⁵`"
                ),
                "difficulty": Difficulty.MEDIUM,
                "base_time_limit_ms": 2000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Two Pointers", "Sorting"],
                "hints": [
                    "Sort the array first to easily skip duplicates.",
                    "Fix one number and use two pointers to find the other two that sum to zero."
                ],
            },
            {
                "title": "Coin Change",
                "description": (
                    "You are given an integer array `coins` representing coins of different "
                    "denominations and an integer `amount` representing a total amount of money.\n\n"
                    "Return the **fewest number of coins** that you need to make up that amount. "
                    "If that amount of money cannot be made up by any combination of the coins, "
                    "return `-1`.\n\n"
                    "You may assume that you have an infinite number of each kind of coin.\n\n"
                    "**Example 1:**\n```\nInput:  coins = [1,5,11], amount = 15\nOutput: 3\n"
                    "Explanation: 15 = 5 + 5 + 5\n```\n\n"
                    "**Example 2:**\n```\nInput:  coins = [2], amount = 3\nOutput: -1\n```\n\n"
                    "**Example 3:**\n```\nInput:  coins = [1], amount = 0\nOutput: 0\n```\n\n"
                    "**Constraints:**\n"
                    "- `1 <= coins.length <= 12`\n"
                    "- `1 <= coins[i] <= 2^31 - 1`\n"
                    "- `0 <= amount <= 10⁴`"
                ),
                "difficulty": Difficulty.MEDIUM,
                "base_time_limit_ms": 2000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Dynamic Programming"],
                "hints": [
                    "Let dp[i] be the minimum number of coins needed to make amount i.",
                    "For each coin c, dp[i] = min(dp[i], dp[i - c] + 1)."
                ],
            },
            # ── HARD ──────────────────────────────────────────────────────
            {
                "title": "Trapping Rain Water",
                "description": (
                    "Given `n` non-negative integers representing an elevation map where the width "
                    "of each bar is `1`, compute how much water it can trap after raining.\n\n"
                    "**Example 1:**\n```\nInput:  height = [0,1,0,2,1,0,1,3,2,1,2,1]\nOutput: 6\n"
                    "Explanation: The elevation map (depicted above) is represented by the array "
                    "[0,1,0,2,1,0,1,3,2,1,2,1]. In this case, 6 units of rain water are being trapped.\n```\n\n"
                    "**Example 2:**\n```\nInput:  height = [4,2,0,3,2,5]\nOutput: 9\n```\n\n"
                    "**Constraints:**\n"
                    "- `n == height.length`\n"
                    "- `1 <= n <= 2 * 10⁴`\n"
                    "- `0 <= height[i] <= 10⁵`"
                ),
                "difficulty": Difficulty.HARD,
                "base_time_limit_ms": 3000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Two Pointers", "Dynamic Programming"],
                "hints": [
                    "The water trapped at index i is min(max_left, max_right) - height[i].",
                    "Precompute prefix_max and suffix_max arrays for O(n) performance."
                ],
            },
            {
                "title": "Median of Two Sorted Arrays",
                "description": (
                    "Given two sorted arrays `nums1` and `nums2` of size `m` and `n` respectively, "
                    "return **the median** of the two sorted arrays.\n\n"
                    "The overall run time complexity should be **O(log(m + n))**.\n\n"
                    "**Example 1:**\n```\nInput:  nums1 = [1,3], nums2 = [2]\nOutput: 2.00000\n"
                    "Explanation: merged array = [1,2,3] and median is 2.\n```\n\n"
                    "**Example 2:**\n```\nInput:  nums1 = [1,2], nums2 = [3,4]\nOutput: 2.50000\n"
                    "Explanation: merged array = [1,2,3,4] and median is (2 + 3) / 2 = 2.5.\n```\n\n"
                    "**Constraints:**\n"
                    "- `nums1.length == m`\n"
                    "- `nums2.length == n`\n"
                    "- `0 <= m <= 1000`\n"
                    "- `0 <= n <= 1000`\n"
                    "- `1 <= m + n <= 2000`\n"
                    "- `-10⁶ <= nums1[i], nums2[i] <= 10⁶`"
                ),
                "difficulty": Difficulty.HARD,
                "base_time_limit_ms": 3000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Binary Search"],
                "hints": [
                    "Binary search on the partition point of the smaller array.",
                    "Ensure max(left_half) <= min(right_half) across both arrays."
                ],
            },
        ]

        problem_map = {}
        for pd in problems_data:
            result = await db.execute(select(Problem).filter_by(title=pd["title"]))
            prob = result.unique().scalar_one_or_none()
            if not prob:
                prob = Problem(
                    title=pd["title"],
                    description=pd["description"],
                    difficulty=pd["difficulty"],
                    base_time_limit_ms=pd["base_time_limit_ms"],
                    base_memory_limit_mb=pd["base_memory_limit_mb"],
                    hints=pd.get("hints", []),
                    created_by=admin_user.id,
                )
                prob.topics = [topic_map[t] for t in pd["topics"]]
                db.add(prob)
                await db.flush()
            problem_map[pd["title"]] = prob
        print("Problems seeded.")

        # ==========================================
        # 4. SEED TEST CASES
        # ==========================================
        test_cases_data = {
            "Two Sum": [
                ({"nums": [2, 7, 11, 15], "target": 9},  [0, 1], True),
                ({"nums": [3, 2, 4],      "target": 6},  [1, 2], True),
                ({"nums": [3, 3],          "target": 6},  [0, 1], True),
                ({"nums": [0, 4, 3, 0],   "target": 0},  [0, 3], False),
                ({"nums": [-1,-2,-3,-4,-5],"target":-8},  [2, 4], False),
                ({"nums": [100,200,300,400],"target":700}, [2, 3], False),
                ({"nums": [1,5,8,3],       "target":11},  [2, 3], False),
                ({"nums": [-3,4,3,90],     "target": 0},  [0, 2], False),
            ],
            "Reverse Linked List": [
                ([1,2,3,4,5],              [5,4,3,2,1],         True),
                ([1,2],                    [2,1],               True),
                ([],                       [],                  True),
                ([7,8,9],                  [9,8,7],             False),
                ([1],                      [1],                 False),
                ([10,20,30,40,50,60],      [60,50,40,30,20,10], False),
                ([2,4,6,8,10,12,14,16],   [16,14,12,10,8,6,4,2],False),
                ([0,0,0],                  [0,0,0],             False),
            ],
            "Maximum Subarray": [
                ({"nums": [-2,1,-3,4,-1,2,1,-5,4]}, 6,  True),
                ({"nums": [1]},                       1,  True),
                ({"nums": [5,4,-1,7,8]},             23,  True),
                ({"nums": [-1]},                     -1, False),
                ({"nums": [-2,-1]},                  -1, False),
                ({"nums": [8,-19,5,-4,20]},          21, False),
                ({"nums": [2,-1,2,3,4,-5]},          10, False),
                ({"nums": [-2,3,1,3]},                7, False),
            ],
            "Valid Parentheses": [
                ({"s": "()"},      True,  True),
                ({"s": "()[]{}"},  True,  True),
                ({"s": "(]"},      False, True),
                ({"s": "([)]"},    False, False),
                ({"s": "{[]}"},    True,  False),
                ({"s": ""},        True,  False),
                ({"s": "(((("},    False, False),
                ({"s": "([{}])"},  True,  False),
            ],
            "Binary Search": [
                ({"nums": [-1,0,3,5,9,12], "target": 9},   4,  True),
                ({"nums": [-1,0,3,5,9,12], "target": 2},  -1,  True),
                ({"nums": [5],             "target": 5},    0,  True),
                ({"nums": [5],             "target": 3},   -1, False),
                ({"nums": [-10,-3,0,1,5],  "target":-3},   1, False),
                ({"nums": [1,2,3,4,5],     "target": 1},   0, False),
                ({"nums": [1,2,3,4,5],     "target": 5},   4, False),
                ({"nums": [2,5,8,12,16,23,38,56,72,91], "target":23}, 5, False),
            ],
            "Longest Substring Without Repeating Characters": [
                ({"s": "abcabcbb"}, 3, True),
                ({"s": "bbbbb"},    1, True),
                ({"s": "pwwkew"},   3, True),
                ({"s": ""},         0, False),
                ({"s": "au"},       2, False),
                ({"s": "dvdf"},     3, False),
                ({"s": "anviaj"},   5, False),
                ({"s": "tmmzuxt"},  5, False),
            ],
            "3Sum": [
                ({"nums": [-1, 0, 1, 2, -1, -4]}, [[-1, -1, 2], [-1, 0, 1]], True),
                ({"nums": [0, 1, 1]}, [], True),
                ({"nums": [0, 0, 0]}, [[0, 0, 0]], True),
                ({"nums": [-2, 0, 0, 2, 2]}, [[-2, 0, 2]], False),
                (
                    {"nums": [-4, -2, -2, -2, 0, 1, 2, 2, 2, 3, 3, 4, 4, 6, 6]},
                    [[-4, -2, 6], [-4, 0, 4], [-4, 1, 3], [-4, 2, 2], [-2, -2, 4], [-2, 0, 2]],
                    False,
                ),
                ({"nums": [-2, 0, 1, 1, 2]}, [[-2, 0, 2], [-2, 1, 1]], False),
                ({"nums": [-1, -1, 0, 1]}, [[-1, 0, 1]], False),
            ],
            "Coin Change": [
                ({"coins": [1,5,11],  "amount": 15}, 3,  True),
                ({"coins": [2],       "amount": 3},  -1, True),
                ({"coins": [1],       "amount": 0},  0,  True),
                ({"coins": [1],       "amount": 1},  1,  False),
                ({"coins": [1],       "amount": 2},  2,  False),
                ({"coins": [1,2,5],   "amount": 11}, 3,  False),
                ({"coins": [186,419,83,408], "amount": 6249}, 20, False),
                ({"coins": [2,5,10,1],"amount": 27}, 4,  False),
            ],
            "Trapping Rain Water": [
                ({"height": [0,1,0,2,1,0,1,3,2,1,2,1]}, 6,  True),
                ({"height": [4,2,0,3,2,5]},              9,  True),
                ({"height": [1,0,1]},                    1,  True),
                ({"height": [3,0,2,0,4]},                7,  False),
                ({"height": [0,1,0,2,1,0,1,3,2,1,2,1]}, 6,  False),
                ({"height": [1,2,3,4,5]},                0,  False),
                ({"height": [5,4,3,2,1]},                0,  False),
                ({"height": [2,0,2]},                    2,  False),
            ],
            "Median of Two Sorted Arrays": [
                ({"nums1": [1,3],  "nums2": [2]},     2.0,   True),
                ({"nums1": [1,2],  "nums2": [3,4]},   2.5,   True),
                ({"nums1": [],     "nums2": [1]},      1.0,   True),
                ({"nums1": [2],    "nums2": []},       2.0,   False),
                ({"nums1": [1,3],  "nums2": [2,4]},   2.5,   False),
                ({"nums1": [0,0],  "nums2": [0,0]},   0.0,   False),
                ({"nums1": [],     "nums2": [2,3]},   2.5,   False),
                ({"nums1": [1,2,3],"nums2": [4,5,6]}, 3.5,   False),
            ],
        }

        for p_title, cases in test_cases_data.items():
            prob = problem_map[p_title]
            await db.execute(TestCase.__table__.delete().where(TestCase.problem_id == prob.id))
            for i, (in_data, out_data, is_samp) in enumerate(cases):
                db.add(
                    TestCase(
                        problem_id=prob.id,
                        input_data=json.dumps(in_data),
                        expected_output=json.dumps(out_data),
                        is_sample=is_samp,
                        ordering=i + 1,
                    )
                )
        await db.flush()
        print("Test Cases seeded.")

        # ==========================================
        # 5. SEED LANGUAGE DRIVERS (v3 Isolated Format)
        # ==========================================
        print("Seeding Language Drivers (v3 format)...")

        # ── DRIVER TEMPLATES ──────────────────────────────────────────────

        PYTHON_DRIVER = r"""import json, time, sys, io

_user_stdout = io.StringIO()
_orig_stdout = sys.stdout
sys.stdout = _user_stdout

{user_code}

def run_test():
    try:
        with open("/sandbox/testcases.json", "r") as f:
            testcases = json.load(f)
    except Exception:
        testcases = []

    results = []
    start_total = time.perf_counter()
    
    sol = Solution()
    for i, tc in enumerate(testcases):
        _user_stdout.seek(0)
        _user_stdout.truncate(0)
        actual = None
        try:
            {call_logic}
        except Exception as e:
            actual = f"Runtime Error: {str(e)}"
            
        results.append({
            "test_case_index": i,
            "actual_output": json.dumps(actual),
            "expected_output": tc["expected_output"],
            "stdout": _user_stdout.getvalue()
        })

    end_total = time.perf_counter()
    sys.stdout = _orig_stdout
    with open("/sandbox/run_results.json", "w") as f:
        json.dump({
            "execution_time_ms": int((end_total - start_total) * 1000),
            "test_case_results": results
        }, f)

if __name__ == "__main__":
    run_test()
"""

        NODEJS_DRIVER = r"""const fs = require('fs');
{user_code}

function runTest() {
    let testcases = [];
    try {
        testcases = JSON.parse(fs.readFileSync('/sandbox/testcases.json', 'utf8'));
    } catch (e) { testcases = []; }

    const results = [];
    const start = Date.now();
    const sol = new Solution();

    testcases.forEach((tc, i) => {
        let stdout = "";
        const oldLog = console.log;
        console.log = (...args) => { 
            stdout += args.map(a => typeof a === 'object' ? JSON.stringify(a) : a).join(" ") + "\n"; 
        };

        let actual;
        try {
            {call_logic}
        } catch (e) {
            actual = "Runtime Error: " + e.message;
        }

        console.log = oldLog;
        results.push({
            test_case_index: i,
            actual_output: JSON.stringify(actual),
            expected_output: tc.expected_output,
            stdout: stdout
        });
    });

    const end = Date.now();
    fs.writeFileSync('/sandbox/run_results.json', JSON.stringify({
        execution_time_ms: end - start,
        test_case_results: results
    }));
}
runTest();
"""

        CPP_DRIVER = r"""#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <chrono>
#include <sstream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

{user_code}

int main() {
    std::ifstream f("/sandbox/testcases.json");
    if (!f.is_open()) return 1;
    json testcases = json::parse(f);

    auto start = std::chrono::high_resolution_clock::now();
    Solution sol;
    json results = json::array();

    for (int i = 0; i < testcases.size(); ++i) {
        auto& tc = testcases[i];
        
        std::stringstream ss;
        auto old_buf = std::cout.rdbuf(ss.rdbuf());
        
        json actual;
        try {
            {call_logic}
        } catch (const std::exception& e) {
            actual = std::string("Runtime Error: ") + e.what();
        } catch (...) {
            actual = "Runtime Error: Unknown exception";
        }

        std::cout.rdbuf(old_buf);

        results.push_back({
            {"test_case_index", i},
            {"actual_output", actual.is_string() ? actual.get<std::string>() : actual.dump()},
            {"expected_output", tc["expected_output"].is_string() ? tc["expected_output"].get<std::string>() : tc["expected_output"].dump()},
            {"stdout", ss.str()}
        });
    }

    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    json final_output;
    final_output["execution_time_ms"] = duration;
    final_output["test_case_results"] = results;

    std::ofstream out("/sandbox/run_results.json");
    out << final_output.dump();
    return 0;
}
"""

        JAVA_DRIVER = r"""import java.io.*;
import java.util.*;
import org.json.simple.*;
import org.json.simple.parser.*;

{user_code}

public class Main {
    public static void main(String[] args) throws Exception {
        JSONParser parser = new JSONParser();
        JSONArray testcases = new JSONArray();
        try {
            testcases = (JSONArray) parser.parse(new FileReader("/sandbox/testcases.json"));
        } catch (Exception e) {}

        long start = System.currentTimeMillis();
        Solution sol = new Solution();
        JSONArray results = new JSONArray();

        for (int i = 0; i < testcases.size(); i++) {
            JSONObject tc = (JSONObject) testcases.get(i);
            
            PrintStream oldOut = System.out;
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            System.setOut(new PrintStream(baos));

            Object actual = null;
            try {
                {call_logic}
            } catch (Exception e) {
                actual = "Runtime Error: " + e.getMessage();
            }

            System.setOut(oldOut);
            JSONObject res = new JSONObject();
            res.put("test_case_index", i);
            
            // Format actual output
            String actualStr;
            if (actual instanceof String && ((String)actual).startsWith("Runtime Error")) {
                actualStr = (String)actual;
            } else {
                actualStr = JSONValue.toJSONString(actual);
            }
            
            res.put("actual_output", actualStr);
            res.put("expected_output", JSONValue.toJSONString(tc.get("expected_output")));
            res.put("stdout", baos.toString());
            results.add(res);
        }

        long end = System.currentTimeMillis();
        JSONObject output = new JSONObject();
        output.put("execution_time_ms", (int)(end - start));
        output.put("test_case_results", results);

        FileWriter fw = new FileWriter("/sandbox/run_results.json");
        fw.write(output.toJSONString());
        fw.flush();
        fw.close();
    }
}
"""

        # ── PROBLEM CONFIGS ───────────────────────────────────────────────

        configs = [
            {
                "title": "Two Sum",
                "py": "actual = sol.twoSum(tc['input']['nums'], tc['input']['target'])",
                "js": "actual = sol.twoSum(tc.input.nums, tc.input.target);",
                "cpp": "actual = sol.twoSum(tc[\"input\"][\"nums\"].get<std::vector<int>>(), tc[\"input\"][\"target\"].get<int>());",
                "java": "actual = sol.twoSum((List<Long>)tc.get(\"input.nums\"), (int)tc.get(\"input.target\"));",
                "py_boiler": "class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        pass\n",
                "js_boiler": "class Solution {\n    twoSum(nums, target) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    std::vector<int> twoSum(std::vector<int>& nums, int target) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        \n    }\n}\n",
            },
            {
                "title": "Reverse Linked List",
                "py_extra": """
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def build_list(arr):
    if not arr: return None
    head = ListNode(arr[0])
    curr = head
    for val in arr[1:]:
        curr.next = ListNode(val)
        curr = curr.next
    return head

def flatten_list(head):
    res = []
    while head:
        res.append(head.val)
        head = head.next
    return res
""",
                "js_extra": """
class ListNode { constructor(v=0,n=null){this.val=v;this.next=n;} }
function buildList(a){ if(!a||!a.length)return null;let h=new ListNode(a[0]),c=h;for(let i=1;i<a.length;i++){c.next=new ListNode(a[i]);c=c.next;}return h; }
function flattenList(h){ let r=[];while(h){r.push(h.val);h=h.next;}return r; }
""",
                "cpp_extra": """
struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};

ListNode* buildList(std::vector<int> a) {
    if (a.empty()) return nullptr;
    ListNode* h = new ListNode(a[0]), *c = h;
    for (size_t i = 1; i < a.size(); i++) {
        c->next = new ListNode(a[i]);
        c = c->next;
    }
    return h;
}

std::vector<int> flattenList(ListNode* h) {
    std::vector<int> r;
    while (h) { r.push_back(h->val); h = h->next; }
    return r;
}
""",
                "java_extra": """
class ListNode {
    int val; ListNode next;
    ListNode() {}
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}
""",
                "py": "actual = flatten_list(sol.reverseList(build_list(tc['input'])))",
                "js": "actual = flattenList(sol.reverseList(buildList(tc.input)));",
                "cpp": "actual = flattenList(sol.reverseList(buildList(tc[\"input\"].get<std::vector<int>>())));",
                "java": "actual = \"[Reverse Linked List java logic simplified]\";",
                "py_boiler": "class Solution:\n    def reverseList(self, head):\n        pass\n",
                "js_boiler": "class Solution {\n    reverseList(head) {\n    }\n}\n",
                "cpp_boiler": "/**\n * Definition for singly-linked list.\n * struct ListNode {\n *     int val;\n *     ListNode *next;\n *     ListNode() : val(0), next(nullptr) {}\n *     ListNode(int x) : val(x), next(nullptr) {}\n *     ListNode(int x, ListNode *next) : val(x), next(next) {}\n * };\n */\nclass Solution {\npublic:\n    ListNode* reverseList(ListNode* head) {\n        \n    }\n};\n",
                "java_boiler": "/**\n * Definition for singly-linked list.\n * public class ListNode {\n *     int val;\n *     ListNode next;\n *     ListNode() {}\n *     ListNode(int val) { this.val = val; }\n *     ListNode(int val, ListNode next) { this.val = val; this.next = next; }\n * }\n */\nclass Solution {\n    public ListNode reverseList(ListNode head) {\n        \n    }\n}\n",
            },
            {
                "title": "Valid Parentheses",
                "py": "actual = sol.isValid(tc['input']['s'])",
                "js": "actual = sol.isValid(tc.input.s);",
                "cpp": "actual = sol.isValid(tc[\"input\"][\"s\"].get<std::string>());",
                "java": "actual = sol.isValid((String)tc.get(\"input.s\"));",
                "py_boiler": "class Solution:\n    def isValid(self, s: str) -> bool:\n        pass\n",
                "js_boiler": "class Solution {\n    isValid(s) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    bool isValid(string s) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public boolean isValid(String s) {\n        \n    }\n}\n",
            },
            {
                "title": "Binary Search",
                "py": "actual = sol.search(tc['input']['nums'], tc['input']['target'])",
                "js": "actual = sol.search(tc.input.nums, tc.input.target);",
                "cpp": "actual = sol.search(tc[\"input\"][\"nums\"].get<std::vector<int>>(), tc[\"input\"][\"target\"].get<int>());",
                "java": "actual = sol.search((List<Long>)tc.get(\"input.nums\"), (int)tc.get(\"input.target\"));",
                "py_boiler": "class Solution:\n    def search(self, nums: list[int], target: int) -> int:\n        pass\n",
                "js_boiler": "class Solution {\n    search(nums, target) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    int search(vector<int>& nums, int target) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public int search(int[] nums, int target) {\n        \n    }\n}\n",
            },
            {
                "title": "Maximum Subarray",
                "py": "actual = sol.maxSubArray(tc['input']['nums'])",
                "js": "actual = sol.maxSubArray(tc.input.nums);",
                "cpp": "actual = sol.maxSubArray(tc[\"input\"][\"nums\"].get<std::vector<int>>());",
                "java": "actual = sol.maxSubArray((List<Long>)tc.get(\"input.nums\"));",
                "py_boiler": "class Solution:\n    def maxSubArray(self, nums: list[int]) -> int:\n        pass\n",
                "js_boiler": "class Solution {\n    maxSubArray(nums) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    int maxSubArray(vector<int>& nums) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public int maxSubArray(int[] nums) {\n        \n    }\n}\n",
            },
            {
                "title": "Longest Substring Without Repeating Characters",
                "py": "actual = sol.lengthOfLongestSubstring(tc['input']['s'])",
                "js": "actual = sol.lengthOfLongestSubstring(tc.input.s);",
                "cpp": "actual = sol.lengthOfLongestSubstring(tc[\"input\"][\"s\"].get<std::string>());",
                "java": "actual = sol.lengthOfLongestSubstring((String)tc.get(\"input.s\"));",
                "py_boiler": "class Solution:\n    def lengthOfLongestSubstring(self, s: str) -> int:\n        pass\n",
                "js_boiler": "class Solution {\n    lengthOfLongestSubstring(s) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    int lengthOfLongestSubstring(string s) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public int lengthOfLongestSubstring(String s) {\n        \n    }\n}\n",
            },
            {
                "title": "3Sum",
                "py": "res = sol.threeSum(tc['input']['nums'])\n            actual = sorted([sorted(t) for t in res])",
                "js": "let res = sol.threeSum(tc.input.nums);\n            actual = res.map(t=>[...t].sort((a,b)=>a-b)).sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);",
                "cpp": "auto res = sol.threeSum(tc[\"input\"][\"nums\"].get<std::vector<int>>());\n            for(auto& t : res) std::sort(t.begin(), t.end());\n            std::sort(res.begin(), res.end());\n            actual = res;",
                "java": "actual = \"[3Sum java logic simplified]\";",
                "py_boiler": "class Solution:\n    def threeSum(self, nums: list[int]) -> list[list[int]]:\n        pass\n",
                "js_boiler": "class Solution {\n    threeSum(nums) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    vector<vector<int>> threeSum(vector<int>& nums) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public List<List<Integer>> threeSum(int[] nums) {\n        \n    }\n}\n",
            },
            {
                "title": "Coin Change",
                "py": "actual = sol.coinChange(tc['input']['coins'], tc['input']['amount'])",
                "js": "actual = sol.coinChange(tc.input.coins, tc.input.amount);",
                "cpp": "actual = sol.coinChange(tc[\"input\"][\"coins\"].get<std::vector<int>>(), tc[\"input\"][\"amount\"].get<int>());",
                "java": "actual = sol.coinChange((List<Long>)tc.get(\"input.coins\"), (int)tc.get(\"input.amount\"));",
                "py_boiler": "class Solution:\n    def coinChange(self, coins: list[int], amount: int) -> int:\n        pass\n",
                "js_boiler": "class Solution {\n    coinChange(coins, amount) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    int coinChange(vector<int>& coins, int amount) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public int coinChange(int[] coins, int amount) {\n        \n    }\n}\n",
            },
            {
                "title": "Trapping Rain Water",
                "py": "actual = sol.trap(tc['input']['height'])",
                "js": "actual = sol.trap(tc.input.height);",
                "cpp": "actual = sol.trap(tc[\"input\"][\"height\"].get<std::vector<int>>());",
                "java": "actual = sol.trap((List<Long>)tc.get(\"input.height\"));",
                "py_boiler": "class Solution:\n    def trap(self, height: list[int]) -> int:\n        pass\n",
                "js_boiler": "class Solution {\n    trap(height) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    int trap(vector<int>& height) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public int trap(int[] height) {\n        \n    }\n}\n",
            },
            {
                "title": "Median of Two Sorted Arrays",
                "py": "res = sol.findMedianSortedArrays(tc['input']['nums1'], tc['input']['nums2'])\n            actual = round(float(res), 5)",
                "js": "let res = sol.findMedianSortedArrays(tc.input.nums1, tc.input.nums2);\n            actual = Math.round(res * 100000) / 100000;",
                "cpp": "double res = sol.findMedianSortedArrays(tc[\"input\"][\"nums1\"].get<std::vector<int>>(), tc[\"input\"][\"nums2\"].get<std::vector<int>>());\n            actual = std::round(res * 100000.0) / 100000.0;",
                "java": "actual = \"[Median java logic simplified]\";",
                "py_boiler": "class Solution:\n    def findMedianSortedArrays(self, nums1: list[int], nums2: list[int]) -> float:\n        pass\n",
                "js_boiler": "class Solution {\n    findMedianSortedArrays(nums1, nums2) {\n    }\n}\n",
                "cpp_boiler": "class Solution {\npublic:\n    double findMedianSortedArrays(vector<int>& nums1, vector<int>& nums2) {\n        \n    }\n};\n",
                "java_boiler": "class Solution {\n    public double findMedianSortedArrays(int[] nums1, int[] nums2) {\n        \n    }\n}\n",
            },
        ]

        drivers = []
        for c in configs:
            prob = problem_map[c["title"]]
            
            # ── Python Driver ──
            py_code = PYTHON_DRIVER.replace("{user_code}", c.get("py_extra", "") + "\n{user_code}")
            py_code = py_code.replace("{call_logic}", c["py"])
            drivers.append(ProblemLanguageConfig(
                problem_id=prob.id,
                language=SupportedLanguage.PYTHON,
                boilerplate=c["py_boiler"],
                driver_code=py_code
            ))

            # ── Node.js Driver ──
            js_code = NODEJS_DRIVER.replace("{user_code}", c.get("js_extra", "") + "\n{user_code}")
            js_code = js_code.replace("{call_logic}", c["js"])
            drivers.append(ProblemLanguageConfig(
                problem_id=prob.id,
                language=SupportedLanguage.NODEJS,
                boilerplate=c["js_boiler"],
                driver_code=js_code
            ))

            # ── C++ Driver ──
            cpp_code = CPP_DRIVER.replace("{user_code}", c.get("cpp_extra", "") + "\n{user_code}")
            cpp_code = cpp_code.replace("{call_logic}", c.get("cpp", ""))
            drivers.append(ProblemLanguageConfig(
                problem_id=prob.id,
                language=SupportedLanguage.CPP,
                boilerplate=c.get("cpp_boiler", ""),
                driver_code=cpp_code
            ))

            # ── Java Driver ──
            java_code = JAVA_DRIVER.replace("{user_code}", c.get("java_extra", "") + "\n{user_code}")
            java_code = java_code.replace("{call_logic}", c.get("java", ""))
            drivers.append(ProblemLanguageConfig(
                problem_id=prob.id,
                language=SupportedLanguage.JAVA,
                boilerplate=c.get("java_boiler", ""),
                driver_code=java_code
            ))

        # Clear existing configs
        for pd in problem_map.values():
            await db.execute(
                ProblemLanguageConfig.__table__.delete().where(
                    ProblemLanguageConfig.problem_id == pd.id
                )
            )

        db.add_all(drivers)
        await db.commit()
        print("Language Drivers seeded successfully.")
        print("Database hydration complete!")
        print(f"\nSummary:")
        print(f"  Topics:   {len(topics_data)}")
        print(f"  Problems: {len(problems_data)} ({sum(1 for p in problems_data if p['difficulty']==Difficulty.EASY)} easy, "
              f"{sum(1 for p in problems_data if p['difficulty']==Difficulty.MEDIUM)} medium, "
              f"{sum(1 for p in problems_data if p['difficulty']==Difficulty.HARD)} hard)")
        print(f"  Drivers:  {len(drivers)} ({len(problems_data) * 4} expected, 4 per problem)")


if __name__ == "__main__":
    asyncio.run(seed_database())