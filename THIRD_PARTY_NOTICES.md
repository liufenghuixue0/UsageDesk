# 来源、实现与许可证

本程序以 Python / HTML / CSS / JavaScript 重新实现仪表盘，不要求用户安装或运行 ccusage。

## codex_usage

- 参考用户提供的 MIT 源码包 `codex_usage-master` 中的 `codex_usage.py`、`desktop.py`、`codex_usage.html`；运行本程序不需要该源码包。
- 参考内容：Codex 本地 JSONL、sessions 与 archived_sessions 目录、session_meta 中的 cwd、token_count 用量和本机 HTTP 仪表盘入口。
- 本地原版的图标仅作早期参考；当前 EXE 使用重新绘制的淡紫色图标 `assets/app.ico`。
- MIT 许可证原文：`licenses/codex_usage-MIT.txt`。

## ccusage

- 上游：https://github.com/ccusage/ccusage
- 本次参考提交：`615bd802bc5c50246b84e98406f20ab048e27cf6`；运行本程序不需要克隆该仓库。
- 主要参考：`rust/adapters/codex/src/parser.rs`、`types.rs`、`loader.rs`、`rust/crates/ccusage-core/src/pricing.rs`，以及 Claude 用量字段与报表设计。
- 使用思路：累计值不变时去重；优先采用有效的 last_token_usage，缺少时从累计差值推导；推理属于输出；只把匹配 compaction marker 且未被累计覆盖的用量记录视为额外压缩用量；Claude 输入与缓存字段分开记录；按天、周、月、项目、会话、模型聚合。
- 本程序不是 ccusage 的完整移植：不实现其所有 CLI 适配器、压缩日志、无父记录时的分叉重放推断等高级情况。
- MIT 许可证原文：`licenses/ccusage-MIT.txt`。

## 价格数据

- 与 ccusage 相同的公开数据源：https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
- 源项目：https://github.com/BerriAI/litellm
- 许可证原文：`licenses/LiteLLM-LICENSE.txt`。
- 构建时保留模型价格快照用于离线运行，日期记录在 `prices.json`；可在 UI 中手动更新。
- 此数据不表示服务商实际扣款；第三方价格表可能滞后或有误，请以供应商计费和用户自定义单价为准。

## 打包工具

Windows EXE 由 PyInstaller 构建，其 GPL 许可证附带允许分发打包应用的例外：https://pyinstaller.org/en/stable/license.html 。随包保留 `licenses/PyInstaller-COPYING.txt` 和 `licenses/Python-PSF.txt`。
