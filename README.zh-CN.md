# Research Paper Workflow

[![CI](https://github.com/XuQingAcademic/research-paper-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/XuQingAcademic/research-paper-workflow/actions/workflows/ci.yml)
[![Tag](https://img.shields.io/github/v/tag/XuQingAcademic/research-paper-workflow?label=tag)](https://github.com/XuQingAcademic/research-paper-workflow/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-3da9fc.svg)](LICENSE)
[![skills.sh compatible](https://img.shields.io/badge/skills.sh-compatible-14b8a6.svg)](https://www.skills.sh/docs)

[English](README.md) · [更新记录](CHANGELOG.md) ·
[安全策略](SECURITY.md) · [隐私说明](PRIVACY.md) ·
[兼容性矩阵](docs/COMPATIBILITY.md) · [试用计划](docs/PILOT_PROGRAM.md) ·
[合成案例](docs/SYNTHETIC_CASE_STUDY.md) ·
[第三方来源](THIRD_PARTY.md) ·
[项目主页](https://xuqingacademic.github.io/research-paper-workflow/)

状态格式及迁移规则见[状态格式说明](docs/STATE_SCHEMAS.md)。
命令行自动化还应遵循[退出码约定](docs/EXIT_CODES.md)：退出码 `1` 通常表示记录有效但
尚未满足当前门槛，而不是输入损坏。

一个通用、循证的科研论文工作流，并对计量经济学和数量经济学提供重点支持。

Research Paper Workflow 负责连接 idea、文献、研究设计、理论证明、实证、模拟、
论文写作、独立复核、修订和可复现交付，并要求论文主张始终受实际证据约束。
它的编排与状态框架可用于不同领域的定量研究；目前最深入的专门路由、接口和示例
集中在计量经济学、统计方法与数量经济学。

> **当前状态：v0.1.1 Research Preview。** 控制器已具备本地回归测试，但本项目
> 不保证 idea 一定原创、文献检索穷尽、定理正确、识别成立、论文发表或所有维度
> 单调改善。详细边界见[能力与声明范围](docs/CLAIMS.md)。

## 适合谁，以及五分钟内能得到什么

| 你的工作 | 工作流提供 |
| --- | --- |
| 计量理论或统计方法研究 | 显式管理 idea、文献、证明、模拟与写作依赖 |
| 证据尚未齐全的定量论文 | 找到第一项未满足要求，只推进不受阻塞影响的工作 |
| 长时间或跨会话研究项目 | 保存紧凑状态、任务句柄、阻塞和恢复条件 |
| 科研 Agent 基础设施 | 复用可移植编排层，同时接入自己的领域验证能力 |

一次符合约束的初始运行应在五分钟内给出暂定项目类型、可见证据缺口、有边界的下一步，
并在获得授权时生成可恢复的 `.paper/workflow/` 状态；它不会凭空生成文献结论、定理、
数值结果或原创性声明。

## 安装并开始使用

添加 GitHub marketplace 并安装插件：

```bash
codex plugin marketplace add XuQingAcademic/research-paper-workflow
codex plugin add research-paper-workflow@research-paper-workflows
```

新建一个 Codex 会话，在定量研究项目目录中发送：

```text
请使用 $research-paper-workflow 检查当前项目，从已有材料续接，识别下一项未满足的
证据要求，并继续所有不受当前阻塞影响的工作。
```

可选验证：

```bash
codex plugin list
```

输出中应包含已安装并启用的
`research-paper-workflow@research-paper-workflows`。

对于使用开放 `SKILL.md` 生态的 Agent，也可以通过
[skills.sh](https://skills.sh/) 仅安装工作流 Skill：

```bash
npx skills add XuQingAcademic/research-paper-workflow --skill research-paper-workflow
```

该路径会安装工作流 Skill 及其引用文件；前面的 Codex plugin 命令还会安装仓库中的
插件元数据。

## 工作流具体能做什么

本项目是编排和证据控制层，不替代真正负责文献检索、理论证明、模拟审计或模型估计的
专门能力。它负责判断当前主张需要哪些证据、哪些工作可以继续、哪些工作必须等待，
并保存跨会话恢复所需的最小状态，避免项目在续接时悄悄改变科学主张。

| 功能 | 具体行为 | 可检查产物 |
| --- | --- | --- |
| 项目接入 | 读取论文、代码、状态、项目指令和已有结果；暂定为 theory、methods、empirical 或 hybrid | 当前目标、论文类型、已有材料和第一项未满足要求 |
| Idea 挖掘 | 形成机制上真正不同的候选，分别绑定最近邻检索、低成本反证、选择标准和重开条件 | 候选组合，而不是过早押注单一 idea |
| 文献治理 | 区分已检索、已筛选和已精读来源；禁止只凭摘要或搜索片段形成原创性表述 | 检索前沿、覆盖缺口、来源状态和有边界的 novelty 表述 |
| 研究设计 | 冻结 estimand、目标总体、识别逻辑、假设、比较对象和每项主张所需证据 | 设计契约，以及主张和证据之间的显式依赖 |
| 理论与证明交接 | 将定理任务交给实际安装的专业能力，只交换哈希绑定的谱系摘要，不复制第二套证明真值 | 定理接口、依赖图、证明状态和未完成义务 |
| 实证证据 | 分开管理数据来源、估计契约、诊断、稳健性检查和结果可支持的表述 | 明确“可以支持什么／不能支持什么”的结果契约 |
| 模拟控制 | 区分 smoke、pilot 和 production；登记真实离线任务句柄与求解失败；运行未结束时阻止依赖结果的文字 | 任务句柄、等待状态、恢复条件、失败谱系和结果范围 |
| 写作与引用 | 允许结构性和已有来源支持的写作继续，同时冻结依赖缺失文献、证明或结果的句子 | 写作权限、缺失引用和 claim 级阻塞 |
| 独立复核 | 将科学依赖、证据上限、可复现性和发布声明与格式／schema 通过分开检查 | 复核意见和有边界的发布结论，而不是笼统的“通过” |
| 连续修订 | 事先声明必须改善项、不可退化项、允许权衡、修改前后证据、回退条件和全稿复核 | 非退化契约及可审计的修订决定 |
| 可恢复状态 | 在 `.paper/workflow/` 中保存阶段状态、下一项安全动作、阻塞、任务句柄和重开条件 | 不需要重做已完成工作的跨会话续接状态 |
| 可复现交付 | 区分结构检查与科学就绪状态，用确定性哈希和来源证明打包公开产物 | 发布状态、校验值、清单和仍然存在的限制 |

### 执行方式

1. 先检查现有证据，再提出新工作。
2. 冻结最近目标以及每项主张所需证据。
3. 只调用当前环境中实际存在的 specialist capability。
4. 继续那些在未来结果变化后仍然有效的独立工作。
5. 文献、证明、数据或模拟缺失时，让依赖分支保持 pending。
6. 保存下一步、阻塞和恢复条件，不把一次局部运行写成项目完成。

可以直接使用隐私安全的合成示例
[`examples/minimal-paper`](examples/minimal-paper/README.md)，或运行确定性的控制器
smoke path：

```bash
python3 scripts/smoke_example.py
```

它会初始化 methods-paper 工作流，把 production simulation 标记为 deferred，识别
`framing` 为下一项可运行阶段，并且不生成任何科学结果主张。完整说明见
[快速开始演示](docs/QUICKSTART.zh-CN.md)。
从输入、门控到交接产物的完整叙述见[合成案例](docs/SYNTHETIC_CASE_STUDY.md)。

## 定位与专业范围

工作流核心刻意保持领域可扩展：即使论文不属于经济学，也能复用证据门控、可恢复
状态、离线任务等待和非退化复核。计量经济学是当前的参考领域，而不是排他边界。
内置的证明谱系接口和第一方 companion 路由最适用于计量理论、统计方法和数量经济学；
其他领域若要获得专业层面的科学验证，需要接入相应的 specialist provider。

## 主要能力

- 用候选组合、最近邻、判别性探路、搜索前沿和重开条件控制 idea 挖掘；
- 用哈希绑定的阶段回执保持跨任务连续性，但不另建科学事实数据库；
- 明确连接证明、实证、模拟、写作和复核的依赖关系；
- 提供“导航—定理接口—证明真值—项目迁移—工作流交接”分层的公共证明谱系框架、接口和哈希绑定检查，不包含具体证明正文；
- 对实质修订建立“必须改善／不得退化／允许权衡／回退条件”契约；
- 保存追加式运行记录、阻塞、资源用量和下一步动作；
- 离线模拟运行时保存真实句柄并等待，只继续不依赖结果的工作；
- 区分结构检查通过、科学证据通过和投稿候选资格。

## 备选的本地开发安装

当前公开预览版需要 Python 3.9+，控制脚本支持 macOS 和 Linux。若要直接从本地
checkout 开发和调试，可以执行：

```bash
git clone https://github.com/XuQingAcademic/research-paper-workflow.git
cd research-paper-workflow
codex plugin marketplace add "$PWD"
codex plugin add research-paper-workflow@research-paper-workflows
```

安装后重启桌面应用或新建 Codex 会话。当前 OpenAI 官方结构以 plugin 根目录的
`plugin.json` 为可移植入口，并从 `skills/` 发现工作流；本仓库同时保留 Codex
兼容 manifest。

## 其他使用路径

在论文项目目录中发送：

```text
请使用 $research-paper-workflow 检查当前项目，从已有材料续接，识别下一项未满足的
证据要求，并继续所有不受当前阻塞影响的工作。
```

没有可公开论文时，可使用[`examples/minimal-paper`](examples/minimal-paper/README.md)
中的合成示例。
[`offline-wait` 示例](examples/offline-wait/README.md)还会实际验证：离线模拟等待期间，
依赖结果的写作会被阻止，只有登记终态和结果文件后才解除等待屏障。

首批用户可以按照公开的[20 分钟试用计划](docs/PILOT_PROGRAM.md)完成一次测试，并通过
专用 Issue 表单或 GitHub Discussions 报告安装、路由、状态或证据边界问题。

## Companion skills 与第三方说明

完整流程会调用若干 companion skills。公开版会在运行时重新发现它们；缺少某个
provider 时，只暂停依赖该能力的分支，不会把缺失能力伪装成已完成。

可使用以下只读命令检查当前环境中有哪些 companion skills：

```bash
python3 plugins/research-paper-workflow/scripts/check_companions.py
```

该报告只表示“能否发现”，不会把安装状态写成科学有效性。公开命令入口及其证据
上限见[控制器说明](docs/CONTROLLERS.md)，机器记录的版本、兼容范围和迁移规则见
[状态格式说明](docs/STATE_SCHEMAS.md)。

我们确实应该提及所使用或借鉴的他人 skill，并区分三种关系：

1. **运行时集成**：记录 skill、上游仓库、检查过的版本和许可证；
2. **设计借鉴**：记录采用了什么机制，同时说明没有复制代码；
3. **复制或修改实现**：除来源外，还必须保留许可证要求的版权与 notice。

完整记录见 [THIRD_PARTY.md](THIRD_PARTY.md)，机器可读依赖见
[`dependencies/skills.json`](plugins/research-paper-workflow/dependencies/skills.json)。
v0.1.1 没有打包第三方 skill 的实现代码。
CI 中执行的 GitHub Actions 另行记录在 `.github/actions-dependencies.json`，不会与
运行时科研能力混为一谈。

## 验证

```bash
python3 scripts/run_checks.py
```

该命令会检查公开发布边界、manifest、内部链接和 Python 语法，运行工作流与仓库测试，
并在隔离的临时目录中执行一次合成示例 smoke test。
GitHub Actions 会在 Linux、macOS 和多个 Python 版本上执行同一检查。

可使用以下命令生成独立 plugin ZIP：

```bash
python3 scripts/package_plugin.py
```

打包过程同时生成外部 `.sha256` 校验文件；ZIP 内还包含 `MANIFEST.sha256`，用于
逐文件核验解压后的插件内容。

可使用跨平台的标准库验包命令同时核对两层哈希、路径和 manifest 身份：

```bash
python3 scripts/verify_release.py dist/research-paper-workflow-0.1.1.zip
```

## 隐私边界

公开仓库明确排除未发表论文切片、私有导师语料或通信、真实项目的 `.paper/` 状态、
个人绝对路径、凭证和原始研究数据。公开示例必须是合成的、开放许可的，或已明确
允许再分发的材料。

## 参与和许可

贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)，
软件引用信息见 [CITATION.cff](CITATION.cff)；本项目不要求配套论文，维护者的公开
联系邮箱已列入其中，ORCID 仍为可选项且暂未填写。参考资料、运行时集成以及使用或
借鉴的 GitHub 项目统一记录在 [THIRD_PARTY.md](THIRD_PARTY.md)。项目采用
[MIT License](LICENSE)。隐私与使用边界见 [PRIVACY.md](PRIVACY.md) 和
[TERMS.md](TERMS.md)。
