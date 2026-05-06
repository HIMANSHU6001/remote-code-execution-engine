import asyncio
from sqlalchemy import select, text
from db.base import AsyncSessionLocal
from db.models import Problem, TestCase, Topic, User, ProblemLanguageConfig
from shared.enums import Difficulty, SupportedLanguage

PROBLEMS = [
    {
        "title": "Two Sum",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
        "difficulty": Difficulty.EASY,
        "base_time_limit_ms": 1000,
        "base_memory_limit_mb": 256,
        "topic_slugs": ["array", "hash-table"],
        "hints": ["Use a hash map to store complements."],
        "test_cases": [
            {"input_data": '4\n2 7 11 15\n9', "expected_output": '[0, 1]', "is_sample": True, "ordering": 0},
            {"input_data": '3\n3 2 4\n6', "expected_output": '[1, 2]', "is_sample": False, "ordering": 1},
            {"input_data": '2\n3 3\n6', "expected_output": '[0, 1]', "is_sample": False, "ordering": 2}
        ],
        "language_configs": [
            {
                "language": SupportedLanguage.PYTHON,
                "boilerplate": "class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        pass\n",
                "driver_code": "import sys\nimport json\n\ndef main():\n    try:\n        input_data = sys.stdin.read().split()\n        if not input_data: return\n        n = int(input_data[0])\n        nums = [int(x) for x in input_data[1:n+1]]\n        target = int(input_data[n+1])\n        sol = Solution()\n        res = sol.twoSum(nums, target)\n        print('\\n---RCE_EXEC_{job_id}---')\n        print(json.dumps(res))\n    except Exception as e:\n        print('\\n---RCE_EXEC_{job_id}---')\n        print(json.dumps({'error': str(e)}))\n\nif __name__ == '__main__':\n    main()\n"
            },
            {
                "language": SupportedLanguage.CPP,
                "boilerplate": "#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        \n    }\n};\n",
                "driver_code": "#include <iostream>\n#include <vector>\n\nint main() {\n    try {\n        int n;\n        if (!(std::cin >> n)) return 0;\n        std::vector<int> nums(n);\n        for(int i=0; i<n; ++i) std::cin >> nums[i];\n        int target;\n        std::cin >> target;\n        Solution sol;\n        std::vector<int> res = sol.twoSum(nums, target);\n        std::cout << \"\\n---RCE_EXEC_{job_id}---\\n\";\n        if (res.size() < 2) {\n            std::cout << \"[]\\n\";\n        } else {\n            std::cout << \"[\" << res[0] << \", \" << res[1] << \"]\\n\";\n        }\n    } catch (...) {\n        std::cout << \"\\n---RCE_EXEC_{job_id}---\\n\";\n        std::cout << \"{\\\"error\\\": \\\"unknown\\\"}\\n\";\n    }\n    return 0;\n}\n"
            }
        ]
    },
    {
        "title": "Reverse Linked List",
        "description": "Given the head of a singly linked list, reverse the list, and return the reversed list.",
        "difficulty": Difficulty.EASY,
        "base_time_limit_ms": 1000,
        "base_memory_limit_mb": 256,
        "topic_slugs": ["linked-list"],
        "hints": [],
        "test_cases": [
            {"input_data": '5\n1 2 3 4 5', "expected_output": '[5, 4, 3, 2, 1]', "is_sample": True, "ordering": 0},
            {"input_data": '2\n1 2', "expected_output": '[2, 1]', "is_sample": False, "ordering": 1},
            {"input_data": '0', "expected_output": '[]', "is_sample": False, "ordering": 2}
        ],
        "language_configs": [
            {
                "language": SupportedLanguage.PYTHON,
                "boilerplate": "class Solution:\n    def reverseList(self, head):\n        pass\n",
                "driver_code": "import sys\nimport json\n\nclass ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef build_list(arr):\n    if not arr: return None\n    dummy = ListNode(0)\n    curr = dummy\n    for val in arr:\n        curr.next = ListNode(val)\n        curr = curr.next\n    return dummy.next\n\ndef serialize_list(head):\n    arr = []\n    while head:\n        arr.append(head.val)\n        head = head.next\n    return arr\n\ndef main():\n    try:\n        input_data = sys.stdin.read().split()\n        if not input_data: return\n        n = int(input_data[0])\n        nums = [int(x) for x in input_data[1:n+1]]\n        head = build_list(nums)\n        sol = Solution()\n        res = sol.reverseList(head)\n        print('\\n---RCE_EXEC_{job_id}---')\n        print(json.dumps(serialize_list(res)))\n    except Exception as e:\n        print('\\n---RCE_EXEC_{job_id}---')\n        print(json.dumps({'error': str(e)}))\n\nif __name__ == '__main__':\n    main()\n"
            },
            {
                "language": SupportedLanguage.CPP,
                "boilerplate": "class Solution {\npublic:\n    ListNode* reverseList(ListNode* head) {\n        return nullptr;\n    }\n};\n",
                "driver_code": "#include <iostream>\n\nstruct ListNode {\n    int val;\n    ListNode *next;\n    ListNode() : val(0), next(nullptr) {}\n    ListNode(int x) : val(x), next(nullptr) {}\n    ListNode(int x, ListNode *next) : val(x), next(next) {}\n};\n\nint main() {\n    try {\n        int n;\n        if (!(std::cin >> n)) return 0;\n        ListNode* dummy = new ListNode(0);\n        ListNode* curr = dummy;\n        for(int i=0; i<n; ++i) {\n            int val;\n            std::cin >> val;\n            curr->next = new ListNode(val);\n            curr = curr->next;\n        }\n        Solution sol;\n        ListNode* res = sol.reverseList(dummy->next);\n        \n        std::cout << \"\\n---RCE_EXEC_{job_id}---\\n[\";\n        bool first = true;\n        while(res) {\n            if(!first) std::cout << \", \";\n            std::cout << res->val;\n            first = false;\n            res = res->next;\n        }\n        std::cout << \"]\\n\";\n    } catch (...) {\n        std::cout << \"\\n---RCE_EXEC_{job_id}---\\n\";\n        std::cout << \"{\\\"error\\\": \\\"unknown\\\"}\\n\";\n    }\n    return 0;\n}\n"
            }
        ]
    },
    {
        "title": "Valid Parentheses",
        "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
        "difficulty": Difficulty.EASY,
        "base_time_limit_ms": 1000,
        "base_memory_limit_mb": 256,
        "topic_slugs": ["string", "stack"],
        "hints": ["Use a stack to keep track of opening brackets."],
        "test_cases": [
            {"input_data": '()[]{}', "expected_output": 'true', "is_sample": True, "ordering": 0},
            {"input_data": '(]', "expected_output": 'false', "is_sample": False, "ordering": 1},
            {"input_data": '([{}])', "expected_output": 'true', "is_sample": False, "ordering": 2}
        ],
        "language_configs": [
            {
                "language": SupportedLanguage.PYTHON,
                "boilerplate": "class Solution:\n    def isValid(self, s: str) -> bool:\n        pass\n",
                "driver_code": "import sys\nimport json\n\ndef main():\n    try:\n        s = sys.stdin.read().strip()\n        sol = Solution()\n        res = sol.isValid(s)\n        print('\\n---RCE_EXEC_{job_id}---')\n        print(json.dumps(res))\n    except Exception as e:\n        print('\\n---RCE_EXEC_{job_id}---')\n        print(json.dumps({'error': str(e)}))\n\nif __name__ == '__main__':\n    main()\n"
            },
            {
                "language": SupportedLanguage.CPP,
                "boilerplate": "#include <string>\nusing namespace std;\n\nclass Solution {\npublic:\n    bool isValid(string s) {\n        \n    }\n};\n",
                "driver_code": "#include <iostream>\n#include <string>\n\nint main() {\n    std::string s;\n    if (!(std::cin >> s)) return 0;\n    Solution sol;\n    bool res = sol.isValid(s);\n    std::cout << \"\\n---RCE_EXEC_{job_id}---\\n\";\n    std::cout << (res ? \"true\" : \"false\") << \"\\n\";\n    return 0;\n}\n"
            }
        ]
    }
]

async def seed_problems() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="admin@example.com",
                name="Admin",
                role="admin",
                is_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print("Created admin user.")

        await session.execute(text("DELETE FROM submissions"))
        await session.execute(text("DELETE FROM problems"))
        await session.commit()
        print("Cleared old submissions and problems.")

        for prob_data in PROBLEMS:
            result = await session.execute(select(Topic).where(Topic.slug.in_(prob_data["topic_slugs"])))
            topics = result.scalars().all()

            problem = Problem(
                title=prob_data["title"],
                description=prob_data["description"],
                difficulty=prob_data["difficulty"],
                base_time_limit_ms=prob_data["base_time_limit_ms"],
                base_memory_limit_mb=prob_data["base_memory_limit_mb"],
                created_by=user.id,
                topics=list(topics),
                hints=prob_data["hints"],
            )

            for tc_data in prob_data["test_cases"]:
                problem.test_cases.append(
                    TestCase(
                        input_data=tc_data["input_data"],
                        expected_output=tc_data["expected_output"],
                        is_sample=tc_data["is_sample"],
                        ordering=tc_data["ordering"],
                    )
                )

            for lc_data in prob_data.get("language_configs", []):
                problem.language_configs.append(
                    ProblemLanguageConfig(
                        language=lc_data["language"],
                        boilerplate=lc_data["boilerplate"],
                        driver_code=lc_data["driver_code"],
                    )
                )

            session.add(problem)
            print(f"Added problem: {prob_data['title']}")

        await session.commit()
        print("Seeding problems complete.")

if __name__ == "__main__":
    asyncio.run(seed_problems())
