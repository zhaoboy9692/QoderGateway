# 直接 HTTP 模型与图片兼容

[English](bridge-compatibility.md) | **中文**

桥接使用带签名的 `api3.qoder.sh/.../agent_chat_generation` HTTP 协议，不启动 Qoder CLI，也不需要 Agent SDK。

此前使用的 `api2-v2.qoder.sh/model/v1/chat/completions` 对部分当前模型代码返回 HTTP 200，但 SSE 内是 `event: error`。忽略该事件会把空回答误判为成功。现在网关会转发上游错误，并拒绝没有正文或工具调用的响应。流式响应开始后的错误以 OpenAI 风格错误事件返回。

用户的 OpenAI `content` 数组会保留在上游 `contents` 中，包括 `image_url` 的 URL 和 data URL。图片理解能力由模型和账号权限决定。`max_tokens`、`temperature`、`top_p`、`stop` 会转交上游参数，实际支持情况由 Qoder 决定。

`src/qoder2api/model_catalog.json` 保存了 16 个系统模型预设的快照。网关会拒绝未知代码，因为旧版上游可能对未知代码静默回退到其他模型。添加私有组织模型或覆盖预设时，将 `QODER_MODEL_CATALOG_PATH` 指向一个绝对路径的 JSON 文件：

```json
{
  "your-organization-model-key": {
    "key": "your-organization-model-key",
    "source": "organization",
    "format": "openai",
    "display_name": "Your organization model",
    "is_vl": true
  }
}
```

私有目录与凭据应放在仓库外。修改目录后重启服务，上游账号权限仍然适用。

验证命令：

```sh
python -m unittest discover -s tests -v
```

2026-09-08 的部署验证：17 个已配置模型（16 个系统模型及 1 个私有组织模型）均通过 NewAPI、使用不走代理的 curl 返回了正文。Qwen3.8-Max、GLM-5.3、MiniMax-M3 通过 OpenAI `image_url` data URL 正确描述了包含两个图形的 PNG。这验证了回答和图片理解，不是对底层模型版本的独立证明。

## 模型目录

`GET /v1/models` 返回 OpenAI 兼容的系统及私有模型列表，使用与对话相同的 Bearer API Key 规则。NewAPI 可通过该接口获取渠道模型。它展示已配置预设，不实时查询账号权限，也不调用 CLI 或 SDK。

控制台通过管理员鉴权的 `GET /ui/models` 读取相同目录。调试对话展示模型名称，发送请求时自动使用选中的 ID。进入账号池时，账号限额面板默认显示并自动加载。

NewAPI 渠道测试的默认 16 Token 预算可能在推理阶段耗尽，导致尚未生成正文。可以仅对测试请求设置参数覆盖，正常调用仍保留调用方自己的限制：

```json
{
  "operations": [{
    "path": "max_tokens",
    "mode": "set",
    "value": 1024,
    "conditions": [
      {"path": "is_channel_test", "mode": "full", "value": true},
      {"path": "max_tokens", "mode": "lt", "value": 1024}
    ],
    "logic": "AND"
  }]
}
```

## 订阅席位与共享资源额度

额度表分别展示 `userQuota`（订阅席位）和 `orgResourcePackage`（组织资源包）。资源包总额来自 `cap`；`used` 和 `remaining` 单独展示，不跨账号合并共享余额。缺失值显示为未知，失败查询展示上游错误，不显示误导性的零余额。

账号轮转会检查所有可用资源池。可用资源包仍有余额时，席位用完并不代表账号整体耗尽。上游 `isQuotaExceeded: true` 保持权威性，余额信息不完整时不会据此轮转。

刷新会显示进行中的动画、完成时间和错误。额度刷新与账号状态刷新都会从 Qoder 用户状态接口同步 `plan`、`userTag`、`nextResetAt`。每行刷新按钮调用需要鉴权的 `POST /ui/accounts/{uid}/refresh`，只更新对应账号。资料查询失败保留上次数据；未知套餐不会猜测为 Trial。旧账号 `quota` 字段不再作为 Credits 展示，应查看分开的额度表。

前端额度测试需要 Node.js 22.6 或以上：

```sh
cd frontend
node --experimental-strip-types --test tests/quota.test.mjs
npm run build
```
