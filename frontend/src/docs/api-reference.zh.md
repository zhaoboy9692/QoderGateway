# API 参考

[English](api-reference.md) | [中文](api-reference.zh.md)

默认基础地址：`http://127.0.0.1:5050`。

## 对话接口

```http
POST /v1/chat/completions
```

开启外部 API 鉴权时，传入 `Authorization: Bearer <your-api-key>`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `model` | string | 已配置的请求 ID，默认 `lite` |
| `messages` | array | OpenAI 风格消息列表 |
| `stream` | boolean | 为 `true` 时使用 SSE，默认 `false` |
| `max_tokens` | number | 转交上游的输出预算 |
| `temperature`、`top_p`、`stop` | 对应 OpenAI 字段类型 | 转交上游参数；实际支持取决于 Qoder |

### 非流式请求

```bash
curl http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"model":"lite","stream":false,"messages":[{"role":"user","content":"Hello"}]}'
```

### 流式请求

```bash
curl -N http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"model":"lite","stream":true,"messages":[{"role":"user","content":"Hello"}]}'
```

### 图片输入

支持将用户 `content` 数组中的 `image_url` URL 或 data URL 转交上游。图片理解能力取决于模型与账号权限。

```json
{
  "model": "qmodel_38max",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Describe this image."},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,<base64-png>"}}
    ]
  }]
}
```

## 模型列表与映射

`GET /v1/models` 使用与对话相同的 Bearer 鉴权规则。控制台使用管理员鉴权的 `GET /ui/models`。两者返回同一份已配置目录：

```json
{"object":"list","data":[{"id":"gmodel","object":"model","created":0,"owned_by":"qoder","name":"GLM-5.3"}]}
```

`name` 用于展示，`id` 用于请求。调试对话自动加载列表并完成选择映射。目录包含系统预设与私有扩展，不代表实时探测了上游权限或可用性。未知模型代码会被网关拒绝，避免上游静默回退。

## 账号管理查询

以下接口使用 `X-Gateway-Token: <gateway-token>`：

| 接口 | 用途 |
| --- | --- |
| `GET /ui/accounts` | 读取已保存的账号资料 |
| `GET /ui/accounts/quota` | 查询启用账号的订阅席位、资源包，并同步套餐与重置日期 |
| `POST /ui/accounts/{uid}/refresh` | 查询单个账号的额度与资料 |
| `PATCH /ui/accounts/{uid}/remark` | 使用 `{ "remark": "..." }` 保存或清空单个账号备注 |
| `POST /ui/accounts/refresh-tokens` | 刷新登录凭据 |

单账号刷新响应包含 `ok`、`metadata`、`quota`。全量额度查询返回 `total`、`quotas`、`metadata`，部分账号失败可通过各条目的 `ok` 和 `error` 判断。

备注接口会去除首尾空白，允许用空字符串清空备注；非字符串或超过 200 个字符时返回 HTTP 400。成功响应包含 `status`、`uid` 和保存后的 `remark`。

## 错误响应

| 状态码 | 含义 |
| --- | --- |
| `401` | 缺少或无效的对应接口密钥 |
| `400` | 管理参数无效，或对话请求没有可用的账号会话 |
| `404` | 管理刷新指定的账号不存在，或路径不存在 |
| `502` | 上游失败、模型不支持或没有产生有效回答等桥接错误 |

流式响应开始前发生错误时返回 HTTP 错误；开始后发生错误时在 SSE 中返回 OpenAI 风格错误事件。不能只凭 HTTP 200 或结束标志判断模型已回答，应检查正文或工具调用内容。
