# 账号备注实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

[English](2026-09-09-account-remark.en.md) | 中文

**目标：** 在账号池末列提供持久化、可编辑的账号备注，同时隐藏可见 UID 列并保留全部 UID 内部行为。

**架构：** SQLite 新增 `remark` 列，管理 API 提供单字段更新。React 账号表维护行内编辑状态，保存后用接口返回值更新本地账号对象；所有账号导入路径都保留已有备注。

**技术栈：** Python 3、SQLite、FastAPI、unittest、React 19、TypeScript、Vite。

---

### 任务 1：备注存储与管理接口

**文件：**
- 修改：`src/qoder2api/database.py`
- 修改：`src/qoder2api/app.py`
- 新建：`tests/test_account_remarks.py`

- [ ] 先写失败测试：验证 `init_db()` 两次后存在 `remark` 列；验证 `PATCH /ui/accounts/{uid}/remark` 的鉴权、保存、清空、200 字限制、类型检查与不存在账号的 404。
- [ ] 运行 `uv run python -m unittest tests.test_account_remarks -v`，确认因字段和接口尚不存在而失败。
- [ ] 在 `init_db()` 中加入幂等迁移：

```python
try:
    conn.execute("ALTER TABLE accounts ADD COLUMN remark TEXT")
except sqlite3.OperationalError:
    pass
```

- [ ] 新增接口，严格验证 `remark` 为字符串、去除首尾空白且长度不超过 200，并执行参数化 SQL：

```python
UPDATE accounts SET remark = ? WHERE uid = ?
```

- [ ] 重跑目标测试并确认通过。

### 任务 2：账号重新导入时保留备注

**文件：**
- 修改：`src/qoder2api/accounts.py`
- 修改：`src/qoder2api/app.py`
- 修改：`tests/test_account_remarks.py`

- [ ] 先补失败测试：已有账号备注为 `主账号` 时，批量重新导入同一 UID 后备注仍为 `主账号`。
- [ ] 运行目标测试并确认当前 `INSERT OR REPLACE` 会清空备注。
- [ ] 将四处账号写入改为 SQLite UPSERT，冲突时只更新认证资料与账号状态，不修改 `remark`：

```sql
INSERT INTO accounts (...) VALUES (...)
ON CONFLICT(uid) DO UPDATE SET
    name = excluded.name,
    security_oauth_token = excluded.security_oauth_token,
    refresh_token = excluded.refresh_token,
    machine_id = excluded.machine_id
```

- [ ] 重跑备注测试和完整后端测试。

### 任务 3：账号表行内编辑

**文件：**
- 修改：`frontend/src/App.tsx`

- [ ] 给 `Account` 增加 `remark: string | null`，增加当前编辑 UID、草稿值和保存中 UID 状态。
- [ ] 新增保存函数，调用 `PATCH /ui/accounts/{uid}/remark`，成功后只替换对应账号的 `remark`，失败时保留编辑状态并显示中英文错误提示。
- [ ] 表头移除 UID，将 `Actions` 后的最后一列改为 `备注 / Remark`；同步空表 `colSpan`。
- [ ] 备注单元格提供文本态、编辑框、保存和取消按钮，并处理 Enter 与 Escape。
- [ ] 搜索表达式加入 `(acc.remark || '').toLowerCase().includes(...)`，UID 搜索保持不变。
- [ ] 运行 TypeScript 检查和 `npm run build`。

### 任务 4：双语文档、部署和验收

**文件：**
- 修改：`frontend/src/docs/account-pool.md`
- 修改：`frontend/src/docs/account-pool.zh.md`
- 修改：`frontend/src/docs/api-reference.md`
- 修改：`frontend/src/docs/api-reference.zh.md`

- [ ] 同步更新中英文账号池和 API 文档，说明备注保存接口、长度和搜索行为。
- [ ] 运行完整后端测试、TypeScript 检查、前端生产构建和 `git diff --check`。
- [ ] 备份服务器相关文件，上传后端、前端静态资源和文档，重启 `qoder2api`。
- [ ] 在服务器上验证接口保存与清空，并在浏览器中验证备注位于最右侧、可以编辑、刷新后仍保留。
- [ ] 提交变更并推送至 `zhaoboy9692/QoderGateway` 的 `main` 分支。

