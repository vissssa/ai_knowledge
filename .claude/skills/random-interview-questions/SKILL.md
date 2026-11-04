---
name: random-interview-questions
description: 从题库索引中随机抽取 4 道面试题，分别是 Agent 基础、Agent 场景、非 Agent 基础、非 Agent 场景各一道，并把题目和参考答案一起写入 random-interview/interview-yy-mm-dd.md。当用户说"随机抽题"、"随机出 4 道题"、"抽几道题练习"、"来一组随机题"、"random questions"时使用。不含 LeetCode，也不生成新题。
---

# 随机抽取 4 道面试题

从 `题目索引.md` 已登记的历史题目中，各随机抽 1 道：Agent 基础、Agent 场景、非 Agent 基础、非 Agent 场景。

## 用法

在题库根目录（含 `题目索引.md` 的目录）下运行：

```bash
python3 .claude/skills/random-interview-questions/scripts/pick.py
```

- `--seed N`：固定随机种子，复现同一组题。
- `--root PATH`：题库根目录，默认按 skill 所在位置推断（`.claude/skills/<name>/` 的上三级）。

## 输出

- 标准输出：文件路径，以及 4 道题的题目 ID、来源文件与行号、题面。**不含参考答案。**
- 文件 `random-interview/interview-yy-mm-dd.md`：每题含题面和参考答案，答案放在 `<details>` 折叠块里，先作答再展开。同一天重复运行会覆盖当天文件。
- `random-interview/` 已写入 `.gitignore`，不会被提交。

## 回复要求

1. 原样呈现脚本标准输出里的 4 道题，并告知答案文件路径。不要在对话里补充答案、提示或解析，除非用户继续要求。
2. 用户作答后，读取答案文件中对应题目的参考答案做对照点评。
3. 输出里出现"（未能提取题面…）"或"（未能提取参考答案…）"表示来源文件格式异常，此时读取来源文件对应小节，如实告知用户。

## 抽样口径

- 数据来源是 `题目索引.md` 的"题目总表"，按「题型」列分类：`Agent 基础` / `基础（Agent）`、`非 Agent 基础` / `基础（非 Agent）`，场景题同理。
- 2026-10-10、2026-10-12 的题目在索引里只写了"基础"或"场景"，无法判定是否属于 Agent，不参与抽样。LeetCode 题不参与。
- 索引只保留最近 3 个自然月，更早的题目不会被抽到。
- 脚本不记录抽题历史，连续运行可能重复抽到同一题。
- 脚本只读题库、索引和训练文件，只写 `random-interview/`。
