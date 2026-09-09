<h1 align="center">QoderGate</h1>

<p align="center">
  把多个 Qoder 账号统一转换成 OpenAI 兼容接口的本地网关。<br>
  A local gateway that turns multiple Qoder accounts into one OpenAI-compatible API.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-%3E%3D3.11-blue?logo=python&logoColor=white" alt="Python >= 3.11">
  <img src="https://img.shields.io/badge/fastapi-0.115+-green?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <a href="https://linux.do"><img src="https://img.shields.io/badge/LINUX_DO-%E7%A4%BE%E5%8C%BA-blue" alt="LINUX DO"></a>
</p>

---

## 致谢 / Acknowledgment

本项目思路来源于 [cubk1/qoder2api](https://github.com/cubk1/qoder2api/)，在此基础上用 Python 重写了后端并新增了 WebUI 管理控制台、SQLite 持久化、多账号池轮转和独立文档站。

This project is inspired by [cubk1/qoder2api](https://github.com/cubk1/qoder2api/). We rewrote the backend in Python and added a WebUI management console, SQLite persistence, multi-account pool rotation, and a standalone documentation site.

特别感谢 [LINUX DO](https://linux.do) 社区提供的交流与推广平台。

Special thanks to the [LINUX DO](https://linux.do) community for the platform of exchange and promotion.

## 功能 / Features

- **OpenAI 兼容接口** — 通过 `/v1/chat/completions` 向客户端提供标准 Chat Completions API
- **多账号池** — 导入多个 Qoder 账号，按 UID 自动去重，请求失败时自动轮转
- **两层鉴权** — 管理后台密钥与外部 API Key 分开配置
- **SQLite 持久化** — 账号、API Key、全局配置全部存入本地数据库
- **WebUI 控制台** — Dashboard、账号管理、API Key 管理、Playground、服务日志
- **Credits 额度明细** — 分别显示订阅席位与组织资源包的总额、已用、剩余和使用率
- **账号资料刷新** — 支持全量/单账号刷新额度、真实套餐和重置日期，提供加载动画、完成时间与错误提示
- **独立文档站** — `/documents` 提供中英文 Wiki，支持本地搜索和目录跳转
- **自动检测语言** — 根据浏览器地区自动切换中文/英文

## 快速开始 / Quickstart

### 安装 / Install

```bash
git clone https://github.com/zhaoboy9692/QoderGateway.git
cd QoderGateway
uv sync
```

### 前端构建 / Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物会输出到 `src/qoder2api/static/`，后端启动时直接托管 WebUI 与文档站。

### 配置 / Configure

```bash
cp .env.example .env
```

编辑 `.env`，修改管理员密码：

```env
QODER_ADMIN_PASSWORD=your-strong-password
```

> **默认密码是 `admin`，强烈建议第一次登录后立即修改。**

### 启动 / Start

```bash
uv run qoder2api
```

服务器后台运行：

```bash
nohup uv run qoder2api >>nohup.out 2>&1 &
```

服务默认运行在 `http://127.0.0.1:5050/`。

| 路径 | 说明 |
|------|------|
| `/` | Landing Page |
| `/console` | 管理控制台 |
| `/documents` | 文档站 / Wiki |
| `/v1/chat/completions` | OpenAI 兼容 API |
| `/v1/models` | 模型列表，使用与对话接口相同的 API Key 鉴权 |

### 账号额度、套餐与刷新

进入 `/console` → **账号池**：

账号限额表默认显示，进入账号池时自动加载，无需先点击刷新。首次查询期间显示加载状态，查询失败时保留面板供重试。

- **查看限额 / 限额表的刷新 / 刷新状态**：重新查询启用账号的额度，并同步套餐与重置日期。
- **每个账号右侧的刷新**：只查询该账号，更新其额度、套餐和 `RESET` 日期。
- **刷新 Token**：更新登录凭据，与额度及套餐查询是不同操作。

查询期间显示旋转图标；额度表刷新时淡化闪动。完成后显示查询时间和提示，
上游数值未变时余额保持原值。请求失败会显示错误，不把失败当作零额度。

订阅席位读取 `userQuota`，组织资源包读取 `orgResourcePackage`。
组织资源包可能被多个账号共享，不能把同一组织各账号显示的余额重复相加。
席位用完但可用资源包仍有余额时，不再仅凭席位余额将账号判定为额度耗尽。

套餐和 `RESET` 从 Qoder 用户状态接口的 `plan`、`userTag`、`nextResetAt` 同步。
没有保存套餐时显示“未获取套餐”，不会猜测为 Trial；同步失败保留上次资料。
旧账号字段 `quota` 不等同于 Credits，实际余额以上方额度明细表为准。

管理接口均需 `X-Gateway-Token`：

| 接口 | 说明 |
|------|------|
| `GET /ui/accounts/quota` | 查询启用账号的额度，同时同步套餐与重置日期 |
| `POST /ui/accounts/{uid}/refresh` | 刷新指定账号的额度、套餐与重置日期 |

更多模型、图片输入及 NewAPI 兼容说明见 [桥接兼容文档](docs/bridge-compatibility.md)。

### 第一次 API 调用 / First API Call

在控制台导入账号后：

```bash
curl http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lite",
    "messages": [{ "role": "user", "content": "Hello" }],
    "stream": false
  }'
```

## 环境变量 / Environment Variables

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `QODER_HOST` | 服务绑定地址 | `127.0.0.1` |
| `QODER_PORT` | 服务端口 | `5050` |
| `QODER_ADMIN_PASSWORD` | 管理员密码（覆盖 SQLite 存储值） | `admin` |
| `QODER_PROXY` | 出站代理地址 | 空 |
| `QODER_ENABLE_DOCUMENTS` | 是否启用文档页 | `1` |
| `QODER_ENABLE_LANDING` | 是否启用 Landing Page | `1` |
| `QODER_PAT` | 首次启动时自动导入的 PAT | 空 |

## 项目结构 / Project Structure

```
├── src/qoder2api/          # Python 后端
│   ├── app.py              # FastAPI 路由
│   ├── accounts.py         # SQLite 账号管理
│   ├── auth.py             # Qoder 鉴权与签名
│   ├── bridge.py           # OpenAI 兼容响应转换
│   ├── config.py           # 配置读写
│   ├── database.py         # SQLite schema
│   ├── env.py              # 环境变量加载
│   └── static/             # 前端构建产物
├── frontend/               # React 前端源码
│   ├── src/App.tsx         # 管理控制台
│   ├── src/docs-main.tsx   # 文档站
│   ├── src/landing-main.tsx# Landing Page
│   └── src/docs/           # 中英文 Markdown 文档
├── .env.example            # 环境变量模板
└── pyproject.toml          # 项目配置
```

## License

MIT
