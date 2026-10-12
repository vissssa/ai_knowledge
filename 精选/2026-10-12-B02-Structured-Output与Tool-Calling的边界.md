---
type: featured-question
source_date: 2026-10-12
source_file: ../2026-10/2026-10-12-AI-Agent-面试训练.md
question_id: Q-20261012-B02
question_no: B02
question_type: 基础定义题
primary_category: LLM 应用工程
secondary_topic: Structured Output 与 Function / Tool Calling
difficulty: 基础题（中高）
featured_on: 2026-10-12
status: generated
tags:
  - AI-Agent
  - 面试训练
  - Structured-Output
  - Function-Calling
  - 精选题
---

# 精选题｜Structured Output 与 Function / Tool Calling 的边界

> **来源**：[2026-10-12 AI Agent 面试训练](../2026-10/2026-10-12-AI-Agent-面试训练.md)
> **来源日期**：2026-10-12 ｜ **题目 ID**：`Q-20261012-B02` ｜ **编号**：B02 ｜ **题型**：基础定义题
> **一级类型**：LLM 应用工程 ｜ **二级主题**：Structured Output 与 Function / Tool Calling
> **精选说明**：本题覆盖了 LLM 应用工程中最容易被"想当然"的一块——结构化输出的保证级别。它同时考察机制理解（约束采样 vs 事后解析）、职责边界（输出形态 vs 控制流）、可靠性工程（四层防线）和成本意识（重试预算），是区分"用过 API"和"能上线"的分水岭题。
> **注意**：本文件内容与原始训练文件一致，未修改原题核心内容；如需作答记录，请回到原始训练文件追加。

---

## 一、题目

> 生产 Agent 需要把模型输出交给下游代码消费。三个声音：
>
> - 甲："让模型输出 JSON，我们 `json.loads`，失败就重试。"
> - 乙："用 Structured Outputs，传 JSON Schema。"
> - 丙："这不就是 Function Calling 吗？"
>
> 请回答：
> 1. **Structured Output 与 Function / Tool Calling 分别解决什么问题，边界在哪？**
> 2. 所谓的 **JSON mode 与严格模式（strict）的结构化输出，差别是什么？** 甲的方案差在哪？
> 3. 在生产中如何设计**校验、重试与降级**，既能保证可靠，又不把成本和延迟打爆？

**难度**：中高。**考察方向**：约束解码 vs 事后解析、形状保证 vs 语义正确、重试预算与降级、schema 作为版本化接口。

---

## 二、考察点

1. **机制差异**：严格模式通过约束采样保证输出完全符合 schema，非严格只是尽力而为。
2. **职责边界**：结构化输出管"最终答案的形态"，工具调用管"触发外部副作用的控制流"。
3. **JSON mode 的真实保证级别**：只保证能解析成 JSON，不保证匹配任何 schema。
4. **可靠性工程分层**：约束 → 校验 → 修复式重试 → 降级与人工兜底。
5. **失败模式**：截断、枚举外值、类型不符、多余字段、可选字段缺失、转义与编码。
6. **工程影响**：schema 复杂度与 token 成本、schema 变更即接口变更、重试预算与熔断。

---

## 三、准确定义与适用边界

**Structured Output（结构化输出）**：为模型输出提供一个 JSON Schema，让输出形态可被机器直接消费。严格模式（strict）下通过约束采样保证输出完全符合 schema；非严格模式只是尽力而为，仍需自行校验。

**Function / Tool Calling**：模型不是"输出一段文本"，而是输出一个**调用决策**——选择哪个工具、传什么参数；执行权在宿主程序，结果通过 `call_id` 之类的标识回关联到上下文。它改变的是**控制流**，并且会触发**外部副作用**。

**适用边界**：

- 结构化输出适用于：信息抽取、分类与路由、评测打分、planner 的步骤列表、把非结构化输入转成对象。
- 不适用于：需要模型自由表达的任务；以及**业务规则的校验**——schema 保证的是"形状"，跨字段约束（如"结束日期必须晚于开始日期"）应交给代码，不要硬塞进 schema。

**关键边界一句话**：schema 保证形状，不保证语义正确，也不保证依据真实。

---

## 四、简洁示例

```python
schema = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id":   {"type": "string"},
                    "text": {"type": "string"},
                    "span": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["id", "text", "span"],
                "additionalProperties": False,
            },
        },
        "needs_human": {"type": "boolean"},
    },
    "required": ["risk_level", "clauses", "needs_human"],
    "additionalProperties": False,
}

async def extract_contract(text: str) -> dict:
    raw = await llm(structured_schema=schema, strict=True, user=text)   # 第 1 层：约束
    try:
        obj = validator.validate(raw)                                    # 第 2 层：形状校验
        assert_business_rules(obj)                                       # 第 2 层：业务规则
        return obj
    except ValidationError as e:
        retry = await llm(                                               # 第 3 层：修复式重试
            structured_schema=schema, strict=True,
            messages=[{"role": "user", "content": text},
                      {"role": "assistant", "content": raw},
                      {"role": "user", "content": f"校验失败：{e}。请修正后重新输出。"}],
        )
        try:
            obj = validator.validate(retry)
            assert_business_rules(obj)
            return obj
        except ValidationError:
            return {"_degraded": True, "reason": "schema_retry_exhausted"}  # 第 4 层：降级
```

四层缺一不可：约束降低失败率，校验是唯一可信的判定，重试必须带上一次的错误信息，降级保证系统不会因为一次解析失败而卡死。

---

## 五、与相近概念的区别

| 对比 | 区别 |
|---|---|
| JSON mode vs 严格模式结构化输出 | JSON mode 只保证"能解析成 JSON"，官方明确说明它不保证匹配任何特定 schema |
| 结构化输出 vs Function Calling | 前者是最终答案的形态；后者是控制流与外部副作用，参数即调用契约，结果用 `call_id` 关联 |
| schema 校验 vs 业务规则校验 | 前者验形状，后者验语义；二者都要，且业务规则不要塞进 schema |
| 约束解码 vs 事后解析 | 前者在采样时排除非法 token（保证形状），后者在生成后修补（只能兜底） |
| 可选字段 vs nullable 字段 | strict 模式下建议把所有字段标为 required 并用 nullable 表达"可能没有"，下游才不会 KeyError |

---

## 六、在 AI Agent 系统中的典型应用

- **工具参数 schema 是安全边界的一部分**：它是"入口契约"，但服务端必须独立再校验一次——模型输出不可信，schema 也不能替代授权检查。
- **结构化输出用于中间决策**：路由（交给哪个子 Agent）、是否继续检索、是否需要人工、评测打分，这些都是"决策对象"，用结构化输出比解析自然语言稳健得多。
- **schema 是版本化接口**：与 prompt 版本、模型版本一起记录到 trace 上。线上质量问题归因时，"schema 改了"和"模型换了"是两类完全不同的根因，必须能分开看。
- **与重试预算耦合**：Agent 是多步的，单步重试预算失控会在多步链路上被放大，必须在编排层设全局重试预算与熔断。

---

## 七、常见误区或错误用法

1. **以为 JSON mode 就等于 schema 保证**：官方明确说明 JSON mode 不保证输出匹配任何 schema，只保证可解析。
2. **重试无上限**：一次 3 分钱的调用，在 20 步 Agent 链路上指数放大，成本与延迟同时爆炸。正确做法是设重试预算（通常 1 次修复式重试）后降级。
3. **重试时不带上一次的校验错误**：只说"请重新输出"，模型大概率重复同样的错误。
4. **把跨字段业务规则塞进 JSON Schema**：表达力有限且失败信息难定位，应交由代码校验。
5. **忽略截断**：`finish_reason == "length"` 导致的截断被当成"解析失败"处理，重试后照样截断，正确做法是提高 `max_tokens` 或拆分抽取任务。
6. **schema 过宽**：大量可选字段导致下游拿到 `None` 或缺失键；应显式标注 nullable 并全部 required。
7. **把 schema 当输入校验的全部**：模型可能输出符合 schema 但语义荒谬的值（如 `risk_level="high"` 但理由为空），schema 不会拦住它。

---

## 八、面试现场参考回答（1-2 分钟）

> "这是三件不同的事。Structured Output 解决的是'最终答案的形态可靠'，严格模式下通过约束采样保证输出完全符合 schema。Function Calling 解决的是'控制流与外部副作用'——模型输出的是调用哪个工具、传什么参数，执行权在宿主程序，结果用 call_id 关联回上下文。前者管输出，后者管动作。
>
> 甲的方案差在：JSON mode 只保证能解析成 JSON，官方明确说它不保证匹配任何特定 schema，所以'输出 JSON 再自己解析'必须再配一层校验和重试，本质上是用更多工程成本去补一个已经存在的官方能力。
>
> 生产上我会做四层。第一层用 strict schema 约束；第二层用校验器做形状校验加业务规则校验，业务规则不要塞进 schema，跨字段约束交给代码；第三层是修复式重试，把上一次的原始输出和校验错误一起回传给模型，且只重试一次；第四层是降级，标记为低置信度并进人工队列，而不是让整条链路卡死。
>
> 成本上我要设全局重试预算，因为 Agent 是多步的，单步失控会在链路上被放大。另外 schema 是版本化接口，我会把 schema 版本、prompt 版本、模型版本一起打到 trace 上，出问题才能分开归因。最后提醒一点：schema 只保证形状，不保证语义正确，也不保证依据真实，语义校验和授权检查仍然必须存在。"

---

## 九、面试官追问及回答要点

**追问：同一个 schema，换新模型后失败率从 0.3% 涨到 4%，你怎么排查？**

回答要点：

1. **先分类，不要先看总数**：按失败类型分布拆——截断、枚举外值、类型不符、多余字段、必填缺失。不同类型的根因完全不同。
2. **分层归因**：是 schema 侧（嵌套过深、枚举过多、字段过多），还是请求侧（`max_tokens` 太小、温度过高、prompt 变更），还是模型侧（新模型对 strict 的支持差异、约束采样实现差异）。
3. **对照实验**：固定输入的回归集，在"旧模型 / 新模型 × 旧 prompt / 新 prompt × 旧 schema / 新 schema"上做对照，一次只变一个变量。
4. **工程处置**：提高 `max_tokens`、拆分大 schema 为多次小抽取、收紧枚举、把嵌套层级压平、必要时对该模型关闭 strict 并加强校验与降级。
5. **上线把关**：把 schema 兼容性纳入模型升级的准入测试，禁止"换模型不跑结构化输出回归集"。
6. **观测**：按 (schema 版本, 模型版本, 失败类型) 三维看板，异常升高自动告警。

---

## 十、延伸资料

| 资料 | 类型 | 核验状态 |
|---|---|---|
| OpenAI《Structured model outputs》https://platform.openai.com/docs/guides/structured-outputs | 官方文档 | **已核验要点**：仅 strict 模式通过约束采样保证完全符合 schema；JSON mode 不保证匹配任何 schema |
| OpenAI《Migrate to the Responses API》（Structured Outputs 定义从 `response_format` 迁移到 `text.format`）https://platform.openai.com/docs/guides/migrate-to-responses | 官方文档 | **已核验**迁移说明要点 |

---

## 十一、复习记录

（本区块留空，供后续周期复盘或复习时追加；复习后请同步更新根目录 `题目索引.md` 中 `Q-20261012-B02` 的状态字段。）
