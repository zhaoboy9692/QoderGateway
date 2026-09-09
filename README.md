# QoderGate

**中文** | [English](README.en.md)

把多个 Qoder 账号统一提供为 OpenAI 兼容接口的本地网关。

## 致谢

项目思路来源于 [cubk1/qoder2api](https://github.com/cubk1/qoder2api/)。Python 后端新增了 WebUI、SQLite 持久化、账号轮转和独立文档站。感谢 [LINUX DO](https://linux.do) 社区提供交流与支持。

## 功能

- OpenAI 兼容的 `/v1/chat/completions` 和 `/v1/models` 接口。
- 多账号按 UID 去重，账号级错误触发轮转。
- 管理后台与外部 API 分别鉴权。
- SQLite 保存账号、API Key 和设置。
- WebUI 提供概览、账号池、模型选择、调试对话、API Key 和日志。
- 分别展示订阅席位与组织共享资源包的 Credits 额度。
- 全量或单账号刷新额度、套餐与重置日期，提供进度和错误反馈。
- 中文与英文文档，支持搜索、目录导航和语言切换。

账号通过已有 Qoder 会话、PAT 或账号 JSON 导入。自动注册功能、独立注册工具及其浏览器依赖已移除。

## 快速开始

### 安装与构建

需要 Python 3.11 及以上、uv、Node.js 和 npm。Node.js 版本需满足前端依赖要求；当前构建使用 Node.js 22.15。

```bash
git clone https://github.com/zhaoboy9692/QoderGateway.git
cd QoderGateway
uv sync
cd frontend
npm ci
npm run build
cd ..
```

构建后的控制台和文档资源位于 `src/qoder2api/static/`。

### 配置

```bash
cp .env.example .env
```

在 `.env` 中设置管理员密码：

```env
QODER_ADMIN_PASSWORD=your-strong-password
```

默认密码为 `admin`，对外提供服务前应修改。

### 启动

```bash
uv run qoder2api
```

服务器后台运行：

```bash
nohup uv run qoder2api >>nohup.out 2>&1 &
```

默认地址为 `http://127.0.0.1:5050/`，监听地址和端口可配置。

| 路径 | 用途 |
| --- | --- |
| `/` | 项目首页 |
| `/console` | 管理控制台 |
| `/documents` | 中英文文档 |
| `/v1/chat/completions` | OpenAI 兼容对话接口 |
| `/v1/models` | 已配置模型列表，鉴权规则与对话接口相同 |

### 额度、套餐与刷新

进入**账号池**，额度面板默认显示并自动加载；查询中或查询失败时面板仍保留。

- **查看限额 / 刷新 / 刷新状态**：查询启用账号，并同步套餐和重置日期。
- 每个账号右侧的**刷新**：仅更新该账号。
- **刷新 Token**：更新登录凭据，与额度和套餐查询是不同操作。

刷新时图标旋转、额度表闪动；完成时间和通知用于确认请求已执行，即使上游余额未变。失败会显示错误，不会显示为零余额。

`userQuota` 表示订阅席位额度，`orgResourcePackage` 表示组织共享额度。同一组织的资源包不能按账号重复相加。席位耗尽但可用资源包仍有余额时，不会仅凭席位余额判断整个账号已耗尽；上游明确报告额度耗尽时仍以该标记为准。

套餐和 `RESET` 来自 `plan`、`userTag`、`nextResetAt`。未知套餐不会默认显示 Trial，资料查询失败保留此前数据。旧 `quota` 字段不等于 Credits 余额，应查看资源明细表。

管理请求使用 `X-Gateway-Token`：

| 接口 | 用途 |
| --- | --- |
| `GET /ui/accounts/quota` | 查询启用账号的额度并同步套餐、重置日期 |
| `POST /ui/accounts/{uid}/refresh` | 刷新单个账号的额度、套餐与重置日期 |
| `GET /ui/models` | 获取控制台模型名称和请求 ID |

### 调试对话的模型选择

进入**调试对话**自动加载已配置模型。下拉框显示易读名称，请求使用对应 ID，例如 `GLM-5.3 → gmodel`、`Qwen3.8-Max → qmodel_38max`、`极致 → ultimate`。

**刷新模型**可重新读取列表，包括 `model_catalog.json` 和 `QODER_MODEL_CATALOG_PATH` 的扩展配置。修改目录文件后需重启网关再刷新。这是已配置目录，不是实时权限或可用性探测。

### 第一次 API 调用

导入账号后发送：

```bash
curl http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"lite","messages":[{"role":"user","content":"Hello"}],"stream":false}'
```

开启 API Key 鉴权后，增加 `-H "Authorization: Bearer <your-api-key>"`。

## 环境变量

| 变量 | 用途 | 默认值 |
| --- | --- | --- |
| `QODER_HOST` | 监听地址 | `127.0.0.1` |
| `QODER_PORT` | 端口 | `5050` |
| `QODER_ADMIN_PASSWORD` | 管理员密码，设置后覆盖 SQLite 值 | 回退为 `admin` |
| `QODER_PROXY` | 支持该配置的上游请求路径使用的显式代理 | 空 |
| `QODER_ENABLE_DOCUMENTS` | 启用文档页 | `1` |
| `QODER_ENABLE_LANDING` | 启用项目首页 | `1` |
| `QODER_PAT` | 启动时无账号则导入的 PAT | 空 |
| `QODER_MODEL_CATALOG_PATH` | 私有 JSON 模型目录的绝对路径 | 空 |

## 项目结构

```text
src/qoder2api/          Python 后端
  app.py               路由和请求处理
  accounts.py          账号存储和资料刷新
  auth.py              Qoder 会话和用户状态
  bridge.py            HTTP 桥接及 OpenAI 响应转换
  model_catalog.json   系统模型预设
  tokens.py            凭据刷新和额度查询
  config.py            配置存储
  database.py          SQLite 表结构
  env.py               环境变量加载
  static/              前端构建产物
frontend/src/          控制台、模型与额度组件、文档站
frontend/src/docs/     配对的英文和中文文档
.env.example           环境变量模板
pyproject.toml         Python 项目配置
```

## 文档语言

每个文档主题都有完整的中文和英文版本。功能变更时应同时更新两种语言。

| 主题 | 中文 | English |
| --- | --- | --- |
| 项目说明 | [中文](README.md) | [English](README.en.md) |
| 快速开始 | [中文](frontend/src/docs/quickstart.zh.md) | [English](frontend/src/docs/quickstart.md) |
| 鉴权机制 | [中文](frontend/src/docs/authentication.zh.md) | [English](frontend/src/docs/authentication.md) |
| API 参考 | [中文](frontend/src/docs/api-reference.zh.md) | [English](frontend/src/docs/api-reference.md) |
| 账号池 | [中文](frontend/src/docs/account-pool.zh.md) | [English](frontend/src/docs/account-pool.md) |
| 运维 | [中文](frontend/src/docs/operations.zh.md) | [English](frontend/src/docs/operations.md) |
| 架构 | [中文](frontend/src/docs/architecture.zh.md) | [English](frontend/src/docs/architecture.md) |
| 桥接兼容 | [中文](docs/bridge-compatibility.zh.md) | [English](docs/bridge-compatibility.md) |
| 协议研究 | [中文](docs/qoder-protocol-research.md) | [English](docs/qoder-protocol-research.en.md) |

## 许可证

MIT，见 [LICENSE](LICENSE)。
