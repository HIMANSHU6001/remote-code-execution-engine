import asyncio
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import AsyncSessionLocal
from db.models import User, Topic, Problem, TestCase, ProblemLanguageConfig
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
                email="admin@system.local", name="Himanshu Kaushik", role="admin", is_verified=True
            )
            db.add(admin_user)
            await db.flush()
            print("Created Admin User.")

        # ==========================================
        # 2. SEED TOPICS
        # ==========================================
        topics_data = [
            {"id": 1, "name": "Array", "slug": "array"},
            {"id": 2, "name": "Hash Table", "slug": "hash-table"},
            {"id": 3, "name": "Linked List", "slug": "linked-list"},
            {"id": 4, "name": "Math", "slug": "math"},
            {"id": 5, "name": "Dynamic Programming", "slug": "dynamic-programming"},
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
            {
                "title": "Two Sum",
                "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
                "difficulty": Difficulty.EASY,
                "base_time_limit_ms": 1000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Hash Table"],
            },
            {
                "title": "Reverse Linked List",
                "description": "Given the head of a singly linked list, reverse the list, and return the reversed list.",
                "difficulty": Difficulty.EASY,
                "base_time_limit_ms": 1000,
                "base_memory_limit_mb": 256,
                "topics": ["Linked List"],
            },
            {
                "title": "Maximum Subarray",
                "description": "Given an integer array nums, find the subarray with the largest sum, and return its sum.",
                "difficulty": Difficulty.MEDIUM,
                "base_time_limit_ms": 2000,
                "base_memory_limit_mb": 256,
                "topics": ["Array", "Dynamic Programming"],
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
                ({"nums": [2, 7, 11, 15], "target": 9}, [0, 1], True),
                ({"nums": [3, 2, 4], "target": 6}, [1, 2], True),
                ({"nums": [3, 3], "target": 6}, [0, 1], True),
                ({"nums": [0, 4, 3, 0], "target": 0}, [0, 3], False),
                ({"nums": [-1, -2, -3, -4, -5], "target": -8}, [2, 4], False),
                ({"nums": [100, 200, 300, 400], "target": 700}, [2, 3], False),
                ({"nums": [1, 5, 8, 3], "target": 11}, [2, 3], False),
                ({"nums": [-3, 4, 3, 90], "target": 0}, [0, 2], False),
            ],
            "Reverse Linked List": [
                ([1, 2, 3, 4, 5], [5, 4, 3, 2, 1], True),
                ([1, 2], [2, 1], True),
                ([], [], True),
                ([7, 8, 9], [9, 8, 7], False),
                ([1], [1], False),
                ([10, 20, 30, 40, 50, 60], [60, 50, 40, 30, 20, 10], False),
                ([2, 4, 6, 8, 10, 12, 14, 16], [16, 14, 12, 10, 8, 6, 4, 2], False),
                ([0, 0, 0], [0, 0, 0], False),
            ],
            "Maximum Subarray": [
                ({"nums": [-2, 1, -3, 4, -1, 2, 1, -5, 4]}, 6, True),
                ({"nums": [1]}, 1, True),
                ({"nums": [5, 4, -1, 7, 8]}, 23, True),
                ({"nums": [-1]}, -1, False),
                ({"nums": [-2, -1]}, -1, False),
                ({"nums": [8, -19, 5, -4, 20]}, 21, False),
                ({"nums": [2, -1, 2, 3, 4, -5]}, 10, False),
                ({"nums": [-2, 3, 1, 3]}, 7, False),
            ],
        }

        for p_title, cases in test_cases_data.items():
            prob = problem_map[p_title]
            # Clear existing to prevent duplicates during re-runs
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
        # 5. SEED LANGUAGE DRIVERS (all 4 languages)
        # ==========================================
        drivers = []
        prob_two = problem_map["Two Sum"]
        prob_rev = problem_map["Reverse Linked List"]
        prob_max = problem_map["Maximum Subarray"]

        # ── TWO SUM ──────────────────────────────
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_two.id,
                language=SupportedLanguage.PYTHON,
                boilerplate="class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        pass\n",
                driver_code='import sys, json\ninput_data = sys.stdin.read().strip()\nif not input_data: sys.exit(0)\ntc = json.loads(input_data)\nsol = Solution()\nres = sol.twoSum(tc["nums"], tc["target"])\nprint("\\n---RCE_EXEC_{job_id}---")\nprint(json.dumps(res))\n',
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_two.id,
                language=SupportedLanguage.NODEJS,
                boilerplate="class Solution {\n    twoSum(nums, target) {\n    }\n}\n",
                driver_code='const fs=require("fs");const tc=JSON.parse(fs.readFileSync(0,"utf-8").trim());const sol=new Solution();const res=sol.twoSum(tc.nums,tc.target);console.log("\\n---RCE_EXEC_{job_id}---");console.log(JSON.stringify(res));\n',
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_two.id,
                language=SupportedLanguage.CPP,
                boilerplate="#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        return {};\n    }\n};\n",
                driver_code=r"""#include <iostream>
#include <sstream>
#include <vector>
#include <string>
using namespace std;

{user_code}

int main(){
    string line; getline(cin,line);
    // parse {"nums":[...],"target":...}
    auto p1=line.find('['); auto p2=line.find(']');
    string arr_s=line.substr(p1+1,p2-p1-1);
    vector<int> nums;
    stringstream ss(arr_s); string tok;
    while(getline(ss,tok,',')){if(!tok.empty()) nums.push_back(stoi(tok));}
    auto tp=line.find("target"); auto cp=line.find(':',tp);
    string tv=line.substr(cp+1);
    tv.erase(tv.find_last_not_of(" \t\n\r}")+1);
    int target=stoi(tv);
    Solution sol;
    vector<int> res=sol.twoSum(nums,target);
    cout<<"\n---RCE_EXEC_{job_id}---"<<endl;
    cout<<"[";
    for(int i=0;i<(int)res.size();i++){if(i)cout<<", ";cout<<res[i];}
    cout<<"]"<<endl;
}
""",
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_two.id,
                language=SupportedLanguage.JAVA,
                boilerplate="import java.util.*;\n\nclass Solution {\n    public int[] twoSum(int[] nums, int target) {\n        return new int[]{};\n    }\n}\n",
                driver_code=r"""import java.util.*;
import java.util.regex.*;

{user_code}

public class Main {
    public static void main(String[] args){
        Scanner sc=new Scanner(System.in);
        StringBuilder sb=new StringBuilder();
        while(sc.hasNextLine()) sb.append(sc.nextLine());
        String line=sb.toString().trim();
        // parse nums
        int p1=line.indexOf('['),p2=line.indexOf(']');
        String arrS=line.substring(p1+1,p2).trim();
        int[] nums;
        if(arrS.isEmpty()){nums=new int[0];}
        else{String[] parts=arrS.split(",");nums=new int[parts.length];
        for(int i=0;i<parts.length;i++) nums[i]=Integer.parseInt(parts[i].trim());}
        // parse target
        int ti=line.indexOf("target");int ci=line.indexOf(':',ti);
        String tv=line.substring(ci+1).replaceAll("[^\\d-]","");
        int target=Integer.parseInt(tv);
        Solution sol=new Solution();
        int[] res=sol.twoSum(nums,target);
        System.out.println("\n---RCE_EXEC_{job_id}---");
        System.out.print("[");
        for(int i=0;i<res.length;i++){if(i>0)System.out.print(", ");System.out.print(res[i]);}
        System.out.println("]");
    }
}
""",
            )
        )

        # ── MAXIMUM SUBARRAY ─────────────────────
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_max.id,
                language=SupportedLanguage.PYTHON,
                boilerplate="class Solution:\n    def maxSubArray(self, nums: list[int]) -> int:\n        pass\n",
                driver_code='import sys, json\ninput_data = sys.stdin.read().strip()\nif not input_data: sys.exit(0)\ntc = json.loads(input_data)\nsol = Solution()\nres = sol.maxSubArray(tc["nums"])\nprint("\\n---RCE_EXEC_{job_id}---")\nprint(json.dumps(res))\n',
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_max.id,
                language=SupportedLanguage.NODEJS,
                boilerplate="class Solution {\n    maxSubArray(nums) {\n    }\n}\n",
                driver_code='const fs=require("fs");const tc=JSON.parse(fs.readFileSync(0,"utf-8").trim());const sol=new Solution();const res=sol.maxSubArray(tc.nums);console.log("\\n---RCE_EXEC_{job_id}---");console.log(JSON.stringify(res));\n',
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_max.id,
                language=SupportedLanguage.CPP,
                boilerplate="#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    int maxSubArray(vector<int>& nums) {\n        return 0;\n    }\n};\n",
                driver_code=r"""#include <iostream>
#include <sstream>
#include <vector>
#include <string>
using namespace std;

{user_code}

int main(){
    string line; getline(cin,line);
    auto p1=line.find('['); auto p2=line.find(']');
    string arr_s=line.substr(p1+1,p2-p1-1);
    vector<int> nums;
    stringstream ss(arr_s); string tok;
    while(getline(ss,tok,',')){if(!tok.empty()) nums.push_back(stoi(tok));}
    Solution sol;
    int res=sol.maxSubArray(nums);
    cout<<"\n---RCE_EXEC_{job_id}---"<<endl;
    cout<<res<<endl;
}
""",
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_max.id,
                language=SupportedLanguage.JAVA,
                boilerplate="class Solution {\n    public int maxSubArray(int[] nums) {\n        return 0;\n    }\n}\n",
                driver_code=r"""import java.util.*;

{user_code}

public class Main {
    public static void main(String[] args){
        Scanner sc=new Scanner(System.in);
        StringBuilder sb=new StringBuilder();
        while(sc.hasNextLine()) sb.append(sc.nextLine());
        String line=sb.toString().trim();
        int p1=line.indexOf('['),p2=line.indexOf(']');
        String arrS=line.substring(p1+1,p2).trim();
        int[] nums;
        if(arrS.isEmpty()){nums=new int[0];}
        else{String[] parts=arrS.split(",");nums=new int[parts.length];
        for(int i=0;i<parts.length;i++) nums[i]=Integer.parseInt(parts[i].trim());}
        Solution sol=new Solution();
        int res=sol.maxSubArray(nums);
        System.out.println("\n---RCE_EXEC_{job_id}---");
        System.out.println(res);
    }
}
""",
            )
        )

        # ── REVERSE LINKED LIST ──────────────────
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_rev.id,
                language=SupportedLanguage.PYTHON,
                boilerplate="class Solution:\n    def reverseList(self, head):\n        pass\n",
                driver_code="""import sys, json

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

input_data = sys.stdin.read().strip()
if not input_data: sys.exit(0)
arr = json.loads(input_data)
head = build_list(arr)
sol = Solution()
res_head = sol.reverseList(head)
print("\\n---RCE_EXEC_{job_id}---")
print(json.dumps(flatten_list(res_head)))
""",
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_rev.id,
                language=SupportedLanguage.NODEJS,
                boilerplate="class Solution {\n    reverseList(head) {\n    }\n}\n",
                driver_code="""const fs=require("fs");
class ListNode{constructor(v=0,n=null){this.val=v;this.next=n;}}
function buildList(a){if(!a||!a.length)return null;let h=new ListNode(a[0]),c=h;for(let i=1;i<a.length;i++){c.next=new ListNode(a[i]);c=c.next;}return h;}
function flattenList(h){let r=[];while(h){r.push(h.val);h=h.next;}return r;}
const arr=JSON.parse(fs.readFileSync(0,"utf-8").trim()||"[]");
const head=buildList(arr);const sol=new Solution();const res=sol.reverseList(head);
console.log("\\n---RCE_EXEC_{job_id}---");console.log(JSON.stringify(flattenList(res)));
""",
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_rev.id,
                language=SupportedLanguage.CPP,
                boilerplate="#include <vector>\nusing namespace std;\n\nstruct ListNode {\n    int val;\n    ListNode *next;\n    ListNode(int x) : val(x), next(nullptr) {}\n};\n\nclass Solution {\npublic:\n    ListNode* reverseList(ListNode* head) {\n        return nullptr;\n    }\n};\n",
                driver_code=r"""#include <iostream>
#include <sstream>
#include <vector>
#include <string>
using namespace std;

struct ListNode {int val; ListNode* next; ListNode(int x):val(x),next(nullptr){}};

{user_code}

ListNode* buildList(vector<int>& a){
    if(a.empty()) return nullptr;
    ListNode* h=new ListNode(a[0]); ListNode* c=h;
    for(int i=1;i<(int)a.size();i++){c->next=new ListNode(a[i]);c=c->next;}
    return h;
}

int main(){
    string line; getline(cin,line);
    // parse JSON array e.g. [1,2,3]
    auto p1=line.find('['); auto p2=line.find(']');
    vector<int> arr;
    if(p1!=string::npos && p2!=string::npos && p2>p1+1){
        string s=line.substr(p1+1,p2-p1-1);
        stringstream ss(s); string tok;
        while(getline(ss,tok,',')){if(!tok.empty()) arr.push_back(stoi(tok));}
    }
    ListNode* head=buildList(arr);
    Solution sol;
    ListNode* res=sol.reverseList(head);
    cout<<"\n---RCE_EXEC_{job_id}---"<<endl;
    cout<<"[";
    bool first=true;
    while(res){if(!first)cout<<", ";cout<<res->val;first=false;res=res->next;}
    cout<<"]"<<endl;
}
""",
            )
        )
        drivers.append(
            ProblemLanguageConfig(
                problem_id=prob_rev.id,
                language=SupportedLanguage.JAVA,
                boilerplate="class ListNode {\n    int val;\n    ListNode next;\n    ListNode(int x) { val = x; }\n}\n\nclass Solution {\n    public ListNode reverseList(ListNode head) {\n        return null;\n    }\n}\n",
                driver_code=r"""import java.util.*;

class ListNode {int val; ListNode next; ListNode(int x){val=x;}}

{user_code}

public class Main {
    static ListNode buildList(int[] a){
        if(a.length==0) return null;
        ListNode h=new ListNode(a[0]),c=h;
        for(int i=1;i<a.length;i++){c.next=new ListNode(a[i]);c=c.next;}
        return h;
    }
    public static void main(String[] args){
        Scanner sc=new Scanner(System.in);
        StringBuilder sb=new StringBuilder();
        while(sc.hasNextLine()) sb.append(sc.nextLine());
        String line=sb.toString().trim();
        int p1=line.indexOf('['),p2=line.indexOf(']');
        int[] arr;
        if(p1>=0 && p2>p1+1){
            String s=line.substring(p1+1,p2).trim();
            if(s.isEmpty()){arr=new int[0];}
            else{String[] parts=s.split(",");arr=new int[parts.length];
            for(int i=0;i<parts.length;i++) arr[i]=Integer.parseInt(parts[i].trim());}
        } else { arr=new int[0]; }
        ListNode head=buildList(arr);
        Solution sol=new Solution();
        ListNode res=sol.reverseList(head);
        System.out.println("\n---RCE_EXEC_{job_id}---");
        System.out.print("[");
        boolean first=true;
        while(res!=null){if(!first)System.out.print(", ");System.out.print(res.val);first=false;res=res.next;}
        System.out.println("]");
    }
}
""",
            )
        )

        # Clear existing configs to prevent unique constraint errors during re-runs
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


if __name__ == "__main__":
    asyncio.run(seed_database())
