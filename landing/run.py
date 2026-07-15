#!/usr/bin/env python3
"""构建 fce2b Template，创建 Sandbox 并用 run_code 验证镜像内的自定义依赖。"""

import json
import os
from pathlib import Path

from e2b import ApiParams, Template, default_build_logger
from e2b_code_interpreter import Sandbox


def required_env(name: str) -> str:
    """读取必填环境变量。

    name: 环境变量名称。
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


api_key = required_env("FCE2B_API_KEY")
api_url = required_env("FCE2B_API_URL")
domain = required_env("FCE2B_DOMAIN")
source_image = required_env("SOURCE_IMAGE")
final_image = required_env("FINAL_IMAGE")
ghcr_username = required_env("GHCR_USERNAME")
ghcr_token = required_env("GHCR_TOKEN")
template_name = required_env("TEMPLATE_NAME")
region = required_env("FCE2B_REGION")
commit = required_env("GITHUB_SHA")
created_at = required_env("RELEASE_CREATED_AT")

headers = {
    "X-E2B-Template-Build-Mode": "builder",
    "X-E2B-Template-Source-Registry-Type": "oci",
    "X-E2B-Template-Dest-Image-Ref": final_image,
    "X-E2B-Template-Source-Username": ghcr_username,
    "X-E2B-Template-Source-Password": ghcr_token,
    "X-E2B-Template-Dest-Username": ghcr_username,
    "X-E2B-Template-Dest-Password": ghcr_token,
}
build_params = ApiParams(request_timeout=1200, headers=headers)
connection = {
    "api_key": api_key,
    # fce2b 仍支持纯数字历史 API Key，关闭 E2B SDK 的 e2b_<hex> 本地格式校验。
    "validate_api_key": False,
    "api_url": api_url,
    "domain": domain,
}

print(
    json.dumps(
        {
            "event": "landing_started",
            "region": region,
            "source_image": source_image,
            "final_image": final_image,
            "template_name": template_name,
        },
        ensure_ascii=False,
    ),
    flush=True,
)

build = Template.build(
    Template().from_image(source_image),
    name=template_name,
    cpu_count=2,
    memory_mb=2048,
    skip_cache=False,
    on_build_logs=default_build_logger(),
    **connection,
    **build_params,
)

sandbox = Sandbox.create(
    template=build.template_id,
    timeout=900,
    request_timeout=600,
    **connection,
)

sandbox_id = sandbox.sandbox_id
try:
    execution = sandbox.run_code(
        "import humanize; print('fce2b-ghcr-ok', humanize.intcomma(1234567))",
        timeout=120,
        request_timeout=180,
    )
    stdout = "".join(execution.logs.stdout or []).strip()
    stderr = "".join(execution.logs.stderr or []).strip()
    print(f"run_code stdout: {stdout}", flush=True)
    print(f"run_code stderr: {stderr}", flush=True)
    if execution.error is not None:
        raise RuntimeError(f"run_code 失败: {execution.error}")
    if "fce2b-ghcr-ok 1,234,567" not in stdout:
        raise RuntimeError(f"自定义依赖验收失败: {stdout!r}")
finally:
    sandbox.kill()
    print(f"sandbox killed: {sandbox_id}", flush=True)

result = {
    "region": region,
    "commit": commit,
    "created_at": created_at,
    "source_image": source_image,
    "final_image": final_image,
    "template_name": template_name,
    "template_id": build.template_id,
    "build_id": build.build_id,
    "sandbox_id": sandbox_id,
    "run_code_stdout": stdout,
}
Path("landing.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

summary_path = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
if summary_path:
    summary = "\n".join(
        [
            "# fce2b landing 成功",
            "",
            f"- Region: `{region}`",
            f"- Source image: `{source_image}`",
            f"- Final image: `{final_image}`",
            f"- Template name: `{template_name}`",
            f"- Template ID: `{build.template_id}`",
            f"- Build ID: `{build.build_id}`",
            f"- Sandbox ID: `{sandbox_id}`",
            f"- run_code: `{stdout}`",
            "",
        ]
    )
    with Path(summary_path).open("a", encoding="utf-8") as summary_file:
        summary_file.write(summary)

print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
