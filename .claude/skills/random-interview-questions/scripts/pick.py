#!/usr/bin/env python3
"""从 题目索引.md 随机抽取 4 题：Agent 基础、Agent 场景、非 Agent 基础、非 Agent 场景。

题面打印到标准输出；题面与参考答案一起写入 random-interview/interview-yy-mm-dd.md。
"""
import argparse
import datetime
import random
import re
import sys
from pathlib import Path

CATEGORIES = [
    ("agent_basic", "Agent 基础"),
    ("agent_scenario", "Agent 场景"),
    ("non_agent_basic", "非 Agent 基础"),
    ("non_agent_scenario", "非 Agent 场景"),
]

# 题型列在不同日期写法不一：「Agent 基础」「基础（Agent）」「非 Agent 场景」「场景（非 Agent）」。
# 早期仅写「基础」「场景」的行无法判定是否属于 Agent，直接跳过。
def classify(kind):
    k = kind.replace(" ", "")
    if "Agent" not in k:
        return None
    side = "non_agent" if "非Agent" in k else "agent"
    if "基础" in k:
        return f"{side}_basic"
    if "场景" in k:
        return f"{side}_scenario"
    return None


def load_rows(index_path):
    rows = {key: [] for key, _ in CATEGORIES}
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| Q-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 13:
            continue
        key = classify(cells[3])
        if key:
            rows[key].append(
                {"id": cells[0], "date": cells[1], "no": cells[2], "level1": cells[4],
                 "title": cells[6], "points": cells[7], "file": cells[12]}
            )
    return rows


ANSWER_HEADING = re.compile(r"### (问题拆解|先思考|参考答案|考察点|关键点|准确定义)")
SECTION_HEADING = re.compile(r"#{1,3} (?:[BSL]\d|Q-\d)")
OUTPUT_DIR = "random-interview"


def extract_qa(path, no, qid):
    """按编号（B01 / S02）或题目 ID 定位小节，返回 {question, answer, line}；找不到返回 None。

    各日期文件格式不一：
    - 题目与答案同在一个小节（「## B01 · …」「## Q-…-B01 · …」）：「### 题目」之后是题面，
      题面之后到小节末尾是答案；没有「### 题目」时，题面取到第一个解析类子标题之前。
    - 早期格式（2026-10-13、10-14）：题面在「### B01｜…」，答案在文件后部同编号的第二个标题下。
    """
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()

    hits = [i for i, l in enumerate(lines) if re.match(rf"#{{1,3}} (?:{no}|{qid})\b", l)]
    if not hits:
        return None

    def section_end(s):
        return next((i for i in range(s + 1, len(lines)) if SECTION_HEADING.match(lines[i])), len(lines))

    start = hits[0]
    end = section_end(start)
    q_from = next((j for j in range(start + 1, end) if lines[j].strip() == "### 题目"), None)
    if q_from is not None:
        body_start, is_stop = q_from + 1, lambda l: l.startswith("### ")
    else:
        body_start, is_stop = start + 1, ANSWER_HEADING.match
    q_end = next((j for j in range(body_start, end) if is_stop(lines[j])), end)

    if q_end < end:
        answer = _clean(lines[q_end:end])
    elif len(hits) > 1:
        answer = _clean(lines[hits[1] + 1:section_end(hits[1])])
    else:
        answer = ""
    return {"question": _clean(lines[body_start:q_end]), "answer": answer, "line": body_start + 1}


def _clean(lines):
    return re.sub(r"\n*---$", "", "\n".join(lines).strip()).strip()


def render_file(date, picks):
    out = [f"# 随机面试题 {date}\n"]
    for n, label, row, qa in picks:
        out.append(f"## {n}. {label}｜{row['title']}\n")
        out.append(f"- 题目 ID：{row['id']}（{row['date']}，{row['level1']}）")
        out.append(f"- 来源：{row['file']}" + (f":{qa['line']}" if qa else "") + "\n")
        if qa and qa["question"]:
            out.append("### 题目\n\n" + qa["question"] + "\n")
        else:
            out.append(f"（未能从来源文件提取题面，核心考点：{row['points']}）\n")
        if qa and qa["answer"]:
            out.append("<details>\n<summary>参考答案</summary>\n\n" + qa["answer"] + "\n\n</details>\n")
        else:
            out.append("（未能提取参考答案，请查看来源文件）\n")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4],
                        help="题库根目录（含 题目索引.md），默认按 skill 所在位置推断")
    parser.add_argument("--seed", type=int, help="固定随机种子，便于复现")
    args = parser.parse_args()

    index_path = args.root / "题目索引.md"
    if not index_path.exists():
        sys.exit(f"找不到 {index_path}，请用 --root 指定题库根目录")

    rows = load_rows(index_path)
    rng = random.Random(args.seed)

    picks = []
    for n, (key, label) in enumerate(CATEGORIES, 1):
        if not rows[key]:
            print(f"## {n}. {label}\n\n（题目索引中没有可判定的{label}题）\n")
            continue
        row = rng.choice(rows[key])
        picks.append((n, label, row, extract_qa(args.root / row["file"], row["no"], row["id"])))

    date = datetime.date.today().strftime("%y-%m-%d")
    out_path = args.root / OUTPUT_DIR / f"interview-{date}.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(render_file(date, picks), encoding="utf-8")

    print(f"已写入：{out_path.relative_to(args.root)}\n")
    for n, label, row, qa in picks:
        print(f"## {n}. {label}｜{row['title']}\n")
        print(f"- 题目 ID：{row['id']}（{row['date']}，{row['level1']}）")
        print(f"- 来源：{row['file']}" + (f":{qa['line']}" if qa else "") + "\n")
        print((qa["question"] if qa and qa["question"] else f"（未能提取题面，核心考点：{row['points']}）") + "\n")


if __name__ == "__main__":
    main()
