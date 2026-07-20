# AGENTS.md — openbid-intel

## 项目定位

本地优先（local-first）的开源招投标情报工具：把招标公告归一化、去重，按可编辑的行业画像打分排序，生成含理由/风险/建议行动的商机日报与 HTML 仪表盘，数据全部落本地 SQLite，零运行时依赖。

## 技术栈

- Python ≥ 3.11，**零第三方运行时依赖**（纯标准库），hatchling 构建，src 布局 `src/bid_intel/`
- 测试：pytest（配置在 pyproject.toml：`pythonpath=["src"]`）；**无 lint/format 配置**
- 存储：SQLite（`src/bid_intel/storage.py`）；Windows 定时任务脚本为 PowerShell（`scripts/*.ps1`）

## 常用命令

```bash
python -m pip install -e .
python -m pip install pytest        # 无 dev extras，需单独装
python -m pytest -q
python -m compileall -q src tests run.py
python run.py validate-config
python run.py release-check
```

免安装启动器：`bid-intel.cmd` / `bid-intel.ps1`（自动设 PYTHONPATH 指向 src）。

## 本仓库 agent 的搜索范围与要求

- 只允许改动本仓库；`config/`、`data/`、`reports/` 是用户数据区，不得提交真实业务数据，示例一律用 `samples/` 合成数据。
- **零运行时依赖是红线**：不得向 pyproject 增加 runtime dependency。
- **可解释性是产品核心承诺**：评分（`src/bid_intel/matcher.py`）的任何变更必须同步保持 `explain.py` 输出的逐项加分明细、中文理由（reasons）、风险（risks）与建议行动（recommended_actions）完整、可追溯。
- PowerShell 脚本改动必须在 Windows 上验证语法（CI 有 ps1 解析检查）。

## 升级建议有效性 / 采纳规则（本仓定制）

1. 凡改动评分逻辑（matcher.py）的建议：必须同步更新 explain 输出与相关测试，且打分保持确定性（无随机、无 LLM 调用），否则无效。
2. 凡引入第三方依赖或联网调用的建议：默认**记录不做**（local-first + 零依赖是定位），需用户明确批准。
3. 画像（`profiles/*.json`）变更：必须能通过 `python run.py validate-config`，且 explain 示例输出需同步核对。
4. CLI 默认路径/可用性改进：有效即可排期做（见 backlog #1）。
5. 报告模板（digest/dashboard/exports）变更：必须保持 reasons/actions 字段不丢失。

## 升级建议 backlog

### 1. CLI 默认 --profile/--sources 为相对路径，离开仓库根目录即报错

- **描述**：`src/bid_intel/cli.py:48-50` 中 `DEFAULT_DB = Path("data/bids.db")`、`DEFAULT_PROFILE = Path("config/profile.json")`、`DEFAULT_SOURCES = Path("config/sources.json")` 均相对当前工作目录；`run.py` 与 `bid-intel.cmd/ps1` 均不做路径锚定。离开仓库根目录运行时，explain/score 等命令报 `invalid profile configuration`（退出码 2），数据库则会在当前目录静默新建 `data/bids.db` 造成分叉。建议：CLI 将默认值解析为包内/安装锚定的绝对路径，或至少在 README 明确"须在仓库根目录运行"。
- **发现日期**：2026-07-20
- **来源任务**：agent 可用性排查（AGENTS.md 建立任务核对）
- **预估价值/成本**：价值中（影响所有非常规目录调用者，含计划任务场景）；成本小-中（路径解析改造 + 测试，或纯文档注明）。
- **状态**：待评审

### 2. ~~README explain 示例预算参数与 demo 数据不对应~~ —— 已核对，不成立

- 2026-07-20 核对：`README.md:82` 的 explain 示例与 `samples/demo_notices.json` 第一条逐项吻合（title/buyer/stage/region/budget_cny=4200000/published_at/deadline_at 全部一致）。该建议**不采纳**，理由：问题已不存在。
