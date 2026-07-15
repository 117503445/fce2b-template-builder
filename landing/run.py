#!/usr/bin/env python3
"""构建 fce2b Template，创建 Sandbox 并用 run_code 验证镜像内的自定义依赖。"""

import json
import os
from pathlib import Path

from e2b import ApiParams, Template, default_build_logger
from e2b_code_interpreter import Sandbox


required_env_names = (
    "FCE2B_API_KEY",
    "FCE2B_API_URL",
    "FCE2B_DOMAIN",
    "SOURCE_IMAGE",
    "FINAL_IMAGE",
    "GHCR_USERNAME",
    "GHCR_TOKEN",
    "TEMPLATE_NAME",
    "FCE2B_REGION",
    "GITHUB_SHA",
    "RELEASE_CREATED_AT",
)
config = {}
for name in required_env_names:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    config[name] = value

API_KEY = config["FCE2B_API_KEY"]
API_URL = config["FCE2B_API_URL"]
DOMAIN = config["FCE2B_DOMAIN"]
SOURCE_IMAGE = config["SOURCE_IMAGE"]
FINAL_IMAGE = config["FINAL_IMAGE"]
GHCR_USERNAME = config["GHCR_USERNAME"]
GHCR_TOKEN = config["GHCR_TOKEN"]
TEMPLATE_NAME = config["TEMPLATE_NAME"]
REGION = config["FCE2B_REGION"]
COMMIT = config["GITHUB_SHA"]
CREATED_AT = config["RELEASE_CREATED_AT"]

headers = {
    "X-E2B-Template-Build-Mode": "builder",
    "X-E2B-Template-Source-Registry-Type": "oci",
    "X-E2B-Template-Dest-Image-Ref": FINAL_IMAGE,
    "X-E2B-Template-Source-Username": GHCR_USERNAME,
    "X-E2B-Template-Source-Password": GHCR_TOKEN,
    "X-E2B-Template-Dest-Username": GHCR_USERNAME,
    "X-E2B-Template-Dest-Password": GHCR_TOKEN,
}
api_params = ApiParams(
    request_timeout=1200,
    headers=headers,
    api_key=API_KEY,
    validate_api_key=False,
    api_url=API_URL,
    domain=DOMAIN,
)

print(
    json.dumps(
        {
            "event": "landing_started",
            "region": REGION,
            "source_image": SOURCE_IMAGE,
            "final_image": FINAL_IMAGE,
            "template_name": TEMPLATE_NAME,
        },
        ensure_ascii=False,
    ),
    flush=True,
)

build = Template.build(
    Template().from_image(SOURCE_IMAGE),
    name=TEMPLATE_NAME,
    cpu_count=2,
    memory_mb=2048,
    skip_cache=False,
    on_build_logs=default_build_logger(),
    **api_params,
)
print(
    json.dumps(
        {
            "event": "template_build_ready",
            "template_id": build.template_id,
            "build_id": build.build_id,
        },
        ensure_ascii=False,
    ),
    flush=True,
)

sandbox = Sandbox.create(
    template=build.template_id,
    timeout=900,
    request_timeout=600,
    api_key=API_KEY,
    validate_api_key=False,
    api_url=API_URL,
    domain=DOMAIN,
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
    "region": REGION,
    "commit": COMMIT,
    "created_at": CREATED_AT,
    "source_image": SOURCE_IMAGE,
    "final_image": FINAL_IMAGE,
    "template_name": TEMPLATE_NAME,
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
            f"- Region: `{REGION}`",
            f"- Source image: `{SOURCE_IMAGE}`",
            f"- Final image: `{FINAL_IMAGE}`",
            f"- Template name: `{TEMPLATE_NAME}`",
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
