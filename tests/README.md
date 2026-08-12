# Tests 目录结构说明

> **撤回声明 / RETRACTION (2026-08-11).** 本文件此前两处引用 Precision 98.51% /
> Recall 100.00% / F1 99.25% / FP Rate 1.49%。**这四个数字从未由评估脚本产出。**
> 它们把 ground truth 标注数当作 true positive 计数，并把 false negative 设为 0 而非
> 实测 —— 因此 recall 按构造必为 100%，F1 是在常数上做算术。同一次提交里的评估输出
> 实测 124 个 false negative、47.46% recall。**四个数字全部撤回，而非更新**：没有任何
> 重跑能复现它们，因为它们从来不是它们所命名的那件事的测量值。
> 完整机制、时间线与逐个页面的对照见 `docs/decisions/METRICS_RETRACTION.md`。
>
> 下文所有指标均可用其后所附命令复现。

本文档介绍 `tests/` 文件夹的组织结构和各模块功能。

## 📁 目录概览

```
tests/
├── __init__.py                    # 测试包初始化
├── conftest.py                    # Pytest 全局配置和共享 fixtures
├── test_owasp_agentic.py          # OWASP Agentic Top 10 规则覆盖测试
│
├── fixtures/                      # 测试用例样本文件
│   ├── asi-01-goal-hijack/        # ASI-01: 目标劫持漏洞样本
│   ├── asi-02-tool-misuse/        # ASI-02: 工具滥用漏洞样本
│   ├── asi-03-privilege-abuse/    # ASI-03: 权限滥用漏洞样本
│   ├── asi-04-supply-chain/       # ASI-04: 供应链漏洞样本
│   ├── asi-05-rce/                # ASI-05: 代码执行漏洞样本
│   ├── asi-06-memory-poisoning/   # ASI-06: 内存投毒漏洞样本
│   ├── asi-07-inter-agent/        # ASI-07: 代理间通信漏洞样本
│   ├── asi-08-cascading/          # ASI-08: 级联故障漏洞样本
│   ├── asi-09-trust/              # ASI-09: 信任利用漏洞样本
│   ├── asi-10-rogue/              # ASI-10: 恶意代理漏洞样本
│   ├── benign/                    # 良性代码样本（用于误报测试）
│   ├── vulnerable_agents/         # 完整漏洞代理示例
│   ├── safe_agents/               # 安全代理示例
│   └── mcp_configs/               # MCP 配置测试样本
│
├── ground_truth/                  # 基准测试数据集
│   ├── schema.yaml                # Ground Truth 数据格式定义
│   └── labeled_samples.yaml       # 标注的漏洞样本（v2.1，42 样本，198 标注）
│
├── benchmark/                     # 性能与精度基准测试
│   ├── precision_recall.py        # 精确率/召回率/F1 评估脚本
│   ├── performance_test.py        # 性能基准测试
│   ├── asi_coverage.py            # ASI 类别覆盖度分析
│   ├── atlas_report.py            # ATLAS 映射报告生成
│   ├── run_benchmark.py           # 基准测试运行器
│   ├── benchmark_config.yaml      # 基准测试配置（11 个目标项目）
│   ├── gates.yaml                 # 质量门限配置（唯一真源）
│   └── fixtures/                  # 基准测试专用 fixtures
│
├── test_scanners/                 # 扫描器单元测试
│   ├── test_python_scanner.py     # Python 代码扫描器测试
│   ├── test_python_scanner_ext.py # Python 扫描器扩展测试
│   ├── test_langchain_rules_v030.py # LangChain 规则测试 (v0.3.0)
│   ├── test_mcp_scanner.py        # MCP 配置扫描器测试
│   ├── test_mcp_scanner_v030.py   # MCP 扫描器测试 (v0.3.0)
│   ├── test_mcp_config_scanner_ext.py # MCP 配置扫描器扩展测试
│   ├── test_mcp_inspector.py      # MCP 检查器测试
│   ├── test_config_scanner.py     # 配置文件扫描器测试
│   ├── test_secret_scanner.py     # 密钥扫描器测试
│   ├── test_asi_coverage_v030.py  # ASI 覆盖度测试 (v0.3.0)
│   └── test_memory_poisoning_v030.py # 内存投毒测试 (v0.3.0)
│
├── test_rules/                    # 规则引擎测试
│   └── test_engine.py             # 规则引擎核心功能测试
│
├── test_cli/                      # CLI 命令测试
│   ├── test_scan_command.py       # scan 命令测试
│   ├── test_inspect_command.py    # inspect 命令测试
│   ├── test_init_command.py       # init 命令测试
│   ├── test_formatters.py         # 输出格式化测试
│   └── test_inspect_render.py     # inspect 渲染测试
│
├── test_config/                   # 配置功能测试
│   └── test_ignore.py             # 忽略规则测试
│
├── test_models/                   # 数据模型测试
│   └── test_finding.py            # Finding 模型测试
│
├── test_utils/                    # 工具函数测试
│   ├── test_compat.py             # 兼容性测试
│   ├── test_compat_extended.py    # 扩展兼容性测试
│   └── test_mcp_client.py         # MCP 客户端测试
│
├── BENCHMARK_UPGRADE_PROMPT.md    # 基准测试升级指南
└── improve.md                     # 测试改进文档
```

---

## 📂 核心目录详解

### 1. `fixtures/` - 测试样本文件

包含按 OWASP Agentic Top 10 (ASI) 分类组织的漏洞样本和安全代码样本。

#### 漏洞样本结构
- **直接漏洞** (`direct/`): 明显的漏洞实现
- **间接漏洞** (`indirect/`): 通过依赖或间接调用触发的漏洞
- **绕过技术** (`bypass/`): 绕过安全控制的示例
- **边界情况** (`edge_cases/`): 特殊场景和边界条件

#### 良性样本 (`benign/`)
- `validated/`: 包含输入验证的安全代码
- `sandboxed/`: 使用沙箱隔离的代码
- `hardened/`: 加固的安全实现

**当前状态**: 81 个样本文件、238 条标注（语料 v2.2）

### 2. `ground_truth/` - 基准数据集

用于评估扫描器精确率和召回率的标注数据集。

#### `labeled_samples.yaml`
- **版本**: v2.2
- **样本数**: 81 个文件
- **标注数**: 238 个漏洞标注
- 复现：`python3 -c "import yaml;d=yaml.safe_load(open('tests/ground_truth/labeled_samples.yaml'));print(d.get('version'), len(d['samples']), sum(len(s.get('vulnerabilities',[])) for s in d['samples']))"`
- **格式**: YAML，每个样本包含文件路径和漏洞列表（行号、规则ID、OWASP ID等）

#### `schema.yaml`
定义 ground truth 数据格式规范，确保数据一致性。

**当前性能指标** — 复现命令 `python3 tests/benchmark/precision_recall.py`（v0.20.0，2026-08-11）:
- Precision: **68.86%**
- Recall: **84.32%**
- F1-Score: **0.7581**
- FP Rate: **31.14%**
- TP 199 / FP 90 / FN 37，共 238 条标注、81 个文件

括号里的「目标」曾写在这里，像是已达成的标准。它们是 `tests/benchmark/gates.yaml`
的 `layer1.target`，**从不阻塞任何构建**，且自 2026-02-04 写下之日起从未被满足过。
真正阻塞 CI 的是同一文件的 `layer1.thresholds`（棘轮）：P ≥0.66 / R ≥0.82 / F1 ≥0.73。

FP 90 应读作悲观值：其中至少 21 条按规则自身定义是正确的检测，只是语料尚未标注。
详见 `docs/decisions/METRICS_RETRACTION.md` § 3(b) —— 那里也说明了为什么不应该
「调整后」再报一个更好看的数字。

### 3. `benchmark/` - 基准测试套件

用于评估扫描器性能和准确性的综合测试套件。

#### 核心脚本

**`precision_recall.py`**
- 计算精确率、召回率、F1 分数
- 生成详细的误报/漏报报告
- 支持自定义 ground truth 路径

**`performance_test.py`**
- 测量扫描性能（速度、内存）
- 支持多项目对比
- 生成性能报告

**`asi_coverage.py`**
- 分析 ASI-01 到 ASI-10 的覆盖度
- 生成类别分布报告
- 识别覆盖盲点

**`atlas_report.py`**
- 生成 ATLAS 映射报告
- 关联规则到 ATLAS 分类

**`run_benchmark.py`**
- 统一运行所有基准测试
- 生成综合报告

#### 配置文件

**`benchmark_config.yaml`**
定义 11 个基准测试目标：
- **T1-T2**: 故意漏洞项目（damn-vulnerable-llm-agent 等）
- **T3-T9**: 真实框架（LangChain、OpenAI Agents、CrewAI 等）
- **T10**: 本地 MCP 配置测试
- **T11**: Streamlit 应用示例

**`gates.yaml`** —— 质量门限的唯一真源（`quality_gates.yaml` 与
`quality_gates_v2.yaml` 已于 v0.20.0 删除，见 `docs/decisions/DEAD_FILES.md`）：
- **棘轮 `layer1.thresholds`（阻塞 CI）**：Precision ≥0.66, Recall ≥0.82, F1 ≥0.73
- **目标 `layer1.target`（只报告，从不阻塞）**：Precision ≥0.90, Recall ≥0.85, F1 ≥0.87,
  FP Rate ≤0.05 —— 这组数字自写下之日起从未被满足，把它当作「发布标准」是本文件此前
  最大的一处误导
- 每个 ASI 类别的最小召回率
- 评估：`python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml`

### 4. `test_scanners/` - 扫描器测试

针对不同扫描器的单元测试：

- **Python 扫描器**: 检测 Python 代码中的漏洞模式
- **MCP 扫描器**: 检测 MCP 配置中的安全问题
- **配置扫描器**: 检测配置文件中的漏洞
- **密钥扫描器**: 检测硬编码密钥和敏感信息
- **LangChain 规则**: 针对 LangChain 框架的特殊规则
- **内存投毒**: ASI-06 相关检测

### 5. `test_rules/` - 规则引擎测试

测试规则引擎的核心功能：
- 规则加载和解析
- 规则匹配逻辑
- 规则优先级和冲突处理

### 6. `test_cli/` - 命令行测试

测试 CLI 命令的功能：
- `scan`: 扫描命令
- `inspect`: 检查命令
- `init`: 初始化命令
- 输出格式化（JSON、YAML、Markdown 等）

### 7. `test_config/` - 配置测试

测试配置功能：
- 忽略规则（`.agent-audit.yaml`）
- 配置文件的解析和应用

### 8. `test_models/` - 数据模型测试

测试核心数据模型：
- `Finding` 模型的结构和验证
- 模型序列化/反序列化

### 9. `test_utils/` - 工具函数测试

测试工具函数和兼容性：
- 兼容性处理
- MCP 客户端功能

---

## 🧪 运行测试

### 运行所有测试
```bash
pytest tests/
```

### 运行特定测试套件
```bash
# 扫描器测试
pytest tests/test_scanners/

# CLI 测试
pytest tests/test_cli/

# 规则引擎测试
pytest tests/test_rules/
```

### 运行基准测试
```bash
# 精确率/召回率评估
python tests/benchmark/precision_recall.py

# 性能测试
python tests/benchmark/performance_test.py

# 完整基准测试套件
python tests/benchmark/run_benchmark.py
```

### 运行 OWASP 覆盖测试
```bash
pytest tests/test_owasp_agentic.py -v
```

---

## 📊 测试统计

- **总测试文件数**: ~30+ 个测试模块
- **测试样本数**: 42 个（33 漏洞 + 9 良性）
- **漏洞标注数**: 198 个
- **基准测试目标**: 11 个项目
- **OWASP ASI 覆盖**: 10/10 类别

---

## 📝 相关文档

- `BENCHMARK_UPGRADE_PROMPT.md`: 基准测试升级指南
- `improve.md`: 测试改进建议和计划
- `ground_truth/schema.yaml`: Ground Truth 数据格式规范

---

## 🔄 更新历史

- **v2.2** (2026-08-11): 81 个文件 / 238 条标注；三处 `rule_id` 标注纠正（DECISIONS.md item 39）
- **v2.1** (2026-02-04): Ground Truth 更新，添加 87 个新标注。~~达到 98.51% Precision~~
  —— 该因果说法已撤回：在「FN 设为 0」的算法下，增加标注按构造就会抬高 TP，这句话
  描述的不是一次测量
- **v2.0**: 初始 Ground Truth 数据集（39 样本，111 标注）
- **v1.0**: 基准测试基础设施建立

---

## 🎯 质量目标

当前状态（语料 v2.2，工具 v0.20.0，2026-08-11 实测）:
- Precision: 68.86%
- Recall: 84.32%
- F1-Score: 0.7581
- FP Rate: 31.14%

复现：`python3 tests/benchmark/precision_recall.py`。棘轮（阻塞 CI）是
P ≥0.66 / R ≥0.82 / F1 ≥0.73，写在 `tests/benchmark/gates.yaml`。

剩余改进空间:
- 3 个误报需要规则逻辑优化（AGENT-026, AGENT-034）
