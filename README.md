# fce2b GHCR Template Builder

使用本模板仓库，可以把自己的 Dockerfile 发布为私有 GHCR 镜像，并自动创建可用的 fce2b Template。

## 快速开始

### 1. 创建自己的仓库

点击仓库页面右上角的 **Use this template**，选择 **Create a new repository**。

创建仓库后，根据需要修改根目录的 `Dockerfile`。提交代码前，请确保 Dockerfile 可以构建 `linux/amd64` 镜像。

### 2. 创建 GitHub Token

创建一个 GitHub PAT classic，并授予以下权限：

- `read:packages`
- `write:packages`

Token 所属用户必须对当前仓库及其 private GHCR package 具有读写权限。如果组织启用了 SSO，还需要为该 Token 完成组织授权。

### 3. 配置 GitHub Actions

进入仓库的 **Settings → Secrets and variables → Actions**。

在 **Secrets** 中添加：

| 名称 | 说明 |
| --- | --- |
| `FCE2B_API_KEY` | 目标地域的 fce2b 托管 API Key。 |
| `GHCR_TOKEN` | 上一步创建的 GitHub PAT classic。 |

在 **Variables** 中添加：

| 名称 | 示例 | 说明 |
| --- | --- | --- |
| `FCE2B_REGION` | `us-west-1` | 创建 Template 的 fce2b 地域。 |

API Key 按地域隔离。修改 `FCE2B_REGION` 时，必须同时把 `FCE2B_API_KEY` 替换为该地域的 API Key。

当前支持：

| 地域 | Region |
| --- | --- |
| 中国香港 | `cn-hongkong` |
| 新加坡 | `ap-southeast-1` |
| 美国（弗吉尼亚） | `us-east-1` |
| 美国（硅谷） | `us-west-1` |

### 4. 发布 Template

使用以下任一方式触发发布：

- 修改并提交 `Dockerfile`、依赖文件或 `landing` 目录中的文件到 `master` 分支；
- 进入 **Actions → Build fce2b template → Run workflow** 手工触发。

一次完整执行通常需要约 1～3 分钟，实际时间取决于地域和镜像大小。

### 5. 获取结果

执行成功后，在对应的 GitHub Actions run 中查看：

- **Summary**：Template ID、Build ID、Sandbox ID、镜像地址和验证结果；
- **Artifacts → landing-result**：下载完整的 `landing.json`。

保存输出的 Template ID，后续可使用 fce2b/E2B SDK 创建 Sandbox。

## 更新镜像

修改 Dockerfile 或依赖后重新触发 workflow。每次成功发布都会生成新的 Template ID，不会覆盖之前的 Template。

## 使用 Git tag 发布镜像

创建并推送符合 `v<major>.<minor>.<patch>` 格式的 Git tag：

```bash
git tag v1.0.0
git push origin v1.0.0
```

`Publish image by tag` workflow 会构建 `linux/amd64` 镜像并发布到：

```text
ghcr.io/<owner>/<repository>:v1.0.0
```

版本 tag 不会同时覆盖 `latest`。如需发布新版本，请创建新的 Git tag。

## 凭证维护

- 不要把 `FCE2B_API_KEY` 或 `GHCR_TOKEN` 写入仓库文件、Dockerfile 或 Action 日志。
- `GHCR_TOKEN` 必须保持有效，确保 fce2b 能够继续读取 private GHCR 镜像。
- Token 轮换后，更新 `GHCR_TOKEN` 并重新发布 Template。
- API Key 轮换或切换地域后，更新 `FCE2B_API_KEY` 并重新发布 Template。

## 常见问题

### GHCR 登录或推送返回 401/403

检查 `GHCR_TOKEN` 是否具有 `read:packages`、`write:packages` 权限，以及 Token 所属用户是否能访问当前仓库。如果仓库属于组织，还需检查 SSO 授权。

### fce2b API Key 被拒绝

检查 `FCE2B_API_KEY` 是否为目标地域的有效托管 API Key，并确认它与 `FCE2B_REGION` 对应。

### workflow 没有自动运行

自动触发仅监听 `master` 分支中的 Dockerfile、依赖、workflow 和 `landing` 相关文件。也可以在 Actions 页面手工运行。

### Template 创建成功但后续无法拉取镜像

检查 GHCR package 是否保持 private、`GHCR_TOKEN` 是否过期，以及 Token 所属用户是否仍有 package 读取权限。更新 Token 后重新发布 Template。
