# 运维

[English](operations.md) | [中文](operations.zh.md)

## 启动与更新

前端或网页文档修改后重新构建，再启动网关：

```bash
cd frontend
npm ci
npm run build
cd ..
nohup uv run qoder2api >>nohup.out 2>&1 &
```

后端或模型目录修改后需要重启正在运行的网关。先停止原进程，再启动，避免同一端口重复监听。只修改静态页面时刷新浏览器即可。

## SQLite 与备份

运行数据位于 `~/.qoder/qoder2api.db`，包含账号凭据、API Key 与设置。停止服务后复制数据库，例如：

```bash
cp ~/.qoder/qoder2api.db ~/.qoder/qoder2api.db.backup
```

Windows PowerShell：

```powershell
Copy-Item "$env:USERPROFILE\.qoder\qoder2api.db" "$env:USERPROFILE\Desktop\qoder2api.db.backup"
```

备份 `.env` 和私有模型目录时也应保护凭据。不要为了重置管理员密码而删除整个账号数据库。

## 管理员密码

设置 `QODER_ADMIN_PASSWORD` 会覆盖 SQLite 中 `settings.gateway_token`。如忘记密码，可修改 `.env` 中的该变量并重启，或更新已备份数据库中的对应设置。

## Token 刷新

启动命令会开启每 6 小时一次的启用账号 Token 刷新。也可在账号池手动点击**刷新 Token**。设备刷新凭据使用 `deviceToken/refresh`，作业刷新凭据使用 `jobToken/refresh`。

## 常见问题

### 401 未授权

管理接口检查 `X-Gateway-Token`；外部 API 检查 `Authorization: Bearer <key>`。二者不能混用。

### 没有可用会话

导入网关主机上的已有 Qoder 登录会话、添加 PAT，或导入账号 JSON。本地自动导入失败时检查对应登录文件是否存在；推理本身不依赖运行 CLI。

### 额度看似没刷新

账号池默认自动加载额度。再次查询会显示动画、完成时间和结果提示；返回数值相同表示上游余额未变化。检查订阅席位和资源包两部分，避免仅凭席位为零判断整个账号已耗尽。

### 套餐或重置日期未知

点击该账号的**刷新**，同步上游 `plan`、`userTag`、`nextResetAt`。查询失败保留上次资料；上游未提供的日期不会被猜测。

### 模型列表或映射

调试对话会从 `GET /ui/models` 自动加载模型名称和 ID。编辑私有目录后重启网关，再点击**刷新模型**。未知模型 ID 会被拒绝；列表不保证上游实时可用。

### NewAPI 测试没有正文

某些推理模型可能用完很小的输出预算后仍未产生回答。给渠道测试设置足够的 `max_tokens`，并检查实际回答，不能只检查 HTTP 状态。具体配置见仓库的桥接兼容文档。
