# 快速开始演示

本演示让新用户在大约一分钟内完成一次边界明确的首次运行。它只使用仓库中的合成
项目，不生成或声称新的科学结果。

## 1. 安装

```bash
codex plugin marketplace add XuQingAcademic/research-paper-workflow
codex plugin add research-paper-workflow@research-paper-workflows
```

安装后请新建 Codex 会话。

## 2. 打开示例

如果还没有定量研究项目，可以克隆仓库并进入合成示例：

```bash
git clone https://github.com/XuQingAcademic/research-paper-workflow.git
cd research-paper-workflow/examples/minimal-paper
```

这个示例研究：当 nuisance function 由 flexible learner 估计时，specification test
是否仍然有用。它不包含未发表论文、私有来源、参与者数据或已声称的研究结果。

## 3. 运行工作流

在以 `minimal-paper` 为项目的新 Codex 会话中发送：

```text
请使用 $research-paper-workflow 检查 project-brief.md，建立比较候选机制所需的最小
项目状态，记录缺失的文献证据，并识别成本最低且安全的下一步。不要声称原创性，
也不要生成数值结果。
```

具体措辞和候选 idea 可以不同，但符合约定的运行应当：

- 在阅读已识别来源前，把原创性判断保持为 pending；
- 比较机制上实质不同的候选，而不是标题变体；
- 为保留或暂存的路线记录低成本 falsifier 和重开条件；
- 继续在各种合理未来结果下都有效的准备工作；
- 如实报告缺失的 companion capability，不假装它已经运行。

## 4. 检查产物

运行后应能检查当前状态、下一项安全动作、待补证据和被阻止的结果依赖工作。编排层
只在 `.paper/workflow/` 下保存工作流状态和哈希绑定的交接记录；文献、证明、模拟、
实证结果和论文主张仍由对应的专门记录负责。

若要离线、确定性地检查控制器路径，回到仓库根目录运行：

```bash
python3 scripts/smoke_example.py
```

预期输出结构：

```json
{
  "example": "minimal-paper",
  "initialized": true,
  "status_schema": "paper-workflow-status.v1",
  "paper_type": "methods",
  "simulation": "deferred",
  "scientific_result_claimed": false
}
```

这个 smoke path 会验证初始化、状态格式、初始 `framing` 门槛，以及没有伪造科学
结果。它不能替代完整的 Agent 运行，也不验证科学主张。

## 下一步

- 阅读[架构说明](ARCHITECTURE.md)了解组件边界；
- 缺少 companion skill 时阅读[依赖解析](DEPENDENCIES.md)；
- 运行 [`offline-wait`](../examples/offline-wait/README.md)，观察长时间模拟如何暂停
  结果依赖工作而不阻塞独立工作；
- 安装问题参见[支持说明](../SUPPORT.md)，可复现的 bug 或功能建议请使用仓库的 issue
  模板。
