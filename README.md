# fin-compliance · 金融内容合规标注扫描器

[![compliance-scan](https://github.com/highLuo/fin-compliance/actions/workflows/compliance-scan.yml/badge.svg)](https://github.com/highLuo/fin-compliance/actions/workflows/compliance-scan.yml)

一个零依赖（纯 Python 标准库）的命令行工具，用来在**发布前**扫描金融营销、
投教、研报类文本，自动标出容易踩监管红线的表述。设计上和 `toksentry`（密钥扫描器）
同构：单文件、无第三方包、能直接塞进 CI 当质量门禁。

## 它查什么

| 类别 | 严重级 | 典型触发 | 对应监管点 |
|------|--------|----------|------------|
| 收益承诺 | high | 保本、保收益、刚性兑付、年化 15%、保证 xx% | 《广告法》第 25 条、基金销售规范 |
| 荐股暗示 | high / medium | 买入这只、必涨、内部消息、代码 600xxx、目标价 | 投顾/荐股资质、误导性宣传 |
| 夸大宣传 | medium | 100% 准确、稳赢、包赚、零风险 | 绝对化用语禁止 |
| 引流话术 | medium | 加微信、老师带单、扫码进群 | 非法荐股、私域引流 |
| AI 生成未标识 | low | 全文无"AI 生成"显著标识 | 生成式内容显著标识要求 |

规则都在 `rules.json` 里，按需增删即可，不碰代码。

## 用法

```bash
# 扫描单个文件
python fin_compliance.py samples/violation.md --format table

# 扫描整个目录（递归，自动跳过二进制/大文件）
python fin_compliance.py samples/ --format json

# 跑内置自检（不需要任何外部数据）
python fin_compliance.py --self-test

# CI 门禁：命中 high 即非零退出（默认），可改 --fail-on
python fin_compliance.py docs/ --fail-on high
```

退出码：`0` 通过 / `1` 命中（达到 `--fail-on` 级别）/ `2` 规则加载失败。

## 接入 CI

`.github/workflows/compliance-scan.yml` 已启用：每次 push/PR 先跑自检，再扫描
`samples/clean/`（合规示例集，应当零命中）。上方状态徽章是这个仓库的真实运行结果。

在自己的仓库里，把该文件复制过去、把扫描路径换成自己的内容目录即可。注意别把
讲解规则的文档一起扫进去——文档里引用违规例句属于说明，不是待发布文案。

## 产品化方向

- **私有化交付**：金融机构把本文档/推文/研报过一遍再做发布审批，审计留痕。
- **合规标注 SaaS（轻量版）**：上传文档 → 返回风险标注 + 修订建议，复用本规则引擎。
- **与 toksentry 组成"发布前双闸"**：密钥闸 + 内容合规闸，一体接入 CI/CD 流水线。

## 边界说明

本工具做的是**文本模式风险标注**，不是法律意见、不是荐股、不接触任何账号或交易。
规则依据公开监管口径整理，正式合规以最新法规与持牌法务意见为准。

## Sponsors

如果这个扫描器在你的发布流程里拦下了一条"保本保收益"，欢迎通过 GitHub Sponsors 支持本项目。
赞助用于维持规则集更新（监管口径、新型话术）、减少误报，并保持零依赖可离线运行。
完整档位（Backer / Supporter / Team / Enterprise）与权益见
[SPONSORS.md](https://github.com/highLuo/fin-compliance/blob/main/SPONSORS.md)。
