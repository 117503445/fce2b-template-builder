# fce2b GHCR Template Builder

本仓库是 GitHub Template Repository 示例：提交 Dockerfile 后，GitHub Actions 会构建私有 GHCR 镜像，通过 fce2b builder 创建 Template，再创建 Sandbox 并执行 `run_code` 验收。

## 执行链路

```text
Dockerfile
  -> ghcr.io/<owner>/<repo>:source-sha-<commit>-<date>
  -> fce2b builder 注入 runtime
  -> ghcr.io/<owner>/<repo>:sha-<commit>-<date>
  -> Template
  -> Sandbox
  -> run_code
```

- `<commit>` 为 Git commit SHA 前 12 位。
- `<date>` 为 Action 开始时的 UTC 时间，格式为 `YYYYMMDD-HHmmss`。
- source 和 final 使用不同 tag，避免 builder 因目标 tag 已存在而跳过注入。
- 每次执行都产生新的镜像 tag 和 Template，不覆盖历史版本。

## 配置

在仓库 Settings 中配置：

### Actions variable

| 名称 | 示例 | 说明 |
| --- | --- | --- |
| `FCE2B_REGION` | `cn-hangzhou` | fce2b 地域，必须在 `landing/regions.json` 白名单中。 |

### Actions secrets

| 名称 | 说明 |
| --- | --- |
| `FCE2B_API_KEY` | 目标地域的 fce2b API Key。 |
| `GHCR_TOKEN` | GitHub PAT classic，需要 `read:packages` 和 `write:packages`。 |

Action 会用 `GHCR_TOKEN` 调用 GitHub `GET /user` 自动获取用户名，不需要额外配置 GHCR username。如果组织启用 SSO，PAT 还需要完成组织授权。

landing 执行器会关闭 E2B SDK 的 `e2b_<hex>` 本地格式校验，以兼容 fce2b 的纯数字历史 API Key；请求仍使用原始 `FCE2B_API_KEY` 进行线上鉴权。

> 当前 sandbox-gateway 会将 Dest Registry 凭证持久化到 Template，以便 FC 后续拉取私有 final image。因此 PAT 必须保持有效；轮换 PAT 后需重新运行 landing。

## 触发

- 向 `master` 提交 Dockerfile、Python 依赖或 landing 文件。
- 在 Actions 页面手工触发 `Build fce2b template`。

CI 成功后，GitHub Step Summary 和 `landing-result` artifact 会输出：

- source/final image；
- final image digest；
- Template ID 和 Build ID；
- Sandbox ID；
- `run_code` 的自定义依赖验收结果。

## 本地检查

```bash
uv sync --frozen
uv run python -m compileall landing
```

完整的 Template Build 和 Sandbox 验收需要 GitHub Actions Secrets，不在本地配置文件中保存凭证。
