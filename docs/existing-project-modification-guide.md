# cccagents 历史项目修改指南

本文档用于说明：当一个项目已经在 cccagents 中启动过、已有 workspace/产物/日志/任务记录时，后续要修改这个历史项目应该怎么操作。

## 1. 先确认 project_id

历史项目必须继续使用原来的 `project_id`，不能随便新建一个项目目录替代。

默认位置：

```text
/home/ubuntu/cccagents/workspaces/<project_id>/repo
/home/ubuntu/cccagents/projects/<project_id>/
```

如果不确定 `project_id`，先在 Linux 上查看：

```bash
ls /home/ubuntu/cccagents/projects
ls /home/ubuntu/cccagents/workspaces
```

确认目标项目后：

```bash
PROJECT_ID=<existing-project-id>
```

## 2. 检查历史项目状态

```bash
PROJECT_ID=<existing-project-id>

test -d /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
test -d /home/ubuntu/cccagents/projects/$PROJECT_ID/08-logs
ls -la /home/ubuntu/cccagents/projects/$PROJECT_ID
ls -la /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
```

如果项目 repo 是 Git 仓库：

```bash
cd /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
git status --short --branch
git log --oneline -5
```

原则：

- 不要覆盖历史 workspace。
- 不要删除历史产物。
- 不要复用别的项目目录。
- 修改前先看当前状态和最近提交。

## 3. 通过飞书让 PM 发起变更

用户应该在飞书里对 PM 说明这是历史项目变更，而不是新项目。

示例：

```text
修改历史项目 <project_id>。
变更目标：把 xxx 功能改成 yyy。
请先读取该项目现有需求、技术方案、测试用例和最近日志，评估影响范围。
需要 PDM 澄清需求，ARCH/DEV 更新技术方案，TEST 并行更新测试用例。
技术方案和测试用例仍然分开保存，Markdown 和 Excel 都要。
```

PM 应先做：

```text
1. 确认 project_id 存在。
2. 读取历史需求、方案、测试用例、日志。
3. 判断是需求变更、缺陷修复、技术优化还是紧急修复。
4. 让 PDM 澄清变更边界。
5. 让 ARCH/DEV 和 TEST 并行更新各自产物。
6. 汇总影响范围给用户审批。
7. 审批后再让 DEV 修改代码。
```

## 4. 历史项目变更推荐目录

不要覆盖旧文件，优先新增版本化变更记录。

建议：

```text
/home/ubuntu/cccagents/projects/<project_id>/02-requirements/change-YYYYMMDD-<topic>.md
/home/ubuntu/cccagents/projects/<project_id>/03-architecture/change-YYYYMMDD-<topic>-technical-design.md
/home/ubuntu/cccagents/projects/<project_id>/03-architecture/change-YYYYMMDD-<topic>-technical-design.xlsx
/home/ubuntu/cccagents/projects/<project_id>/04-test-cases/change-YYYYMMDD-<topic>-test-cases.md
/home/ubuntu/cccagents/projects/<project_id>/04-test-cases/change-YYYYMMDD-<topic>-test-cases.xlsx
/home/ubuntu/cccagents/projects/<project_id>/08-logs/hermes-runs/<run_id>/
```

命令日志继续追加到：

```text
/home/ubuntu/cccagents/projects/<project_id>/08-logs/command-log.jsonl
```

## 5. 修改代码前的 Git 规则

在历史项目 repo 中操作：

```bash
cd /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
git status --short --branch
```

如果工作区干净，建议为变更新建分支：

```bash
git checkout -b change/<short-topic>
```

如果工作区不干净：

1. 不要直接覆盖。
2. 先让 PM 汇报未提交变更。
3. 判断这些变更属于谁、是否需要保留。
4. 获得用户确认后再继续。

危险操作必须审批：

```text
git reset --hard
git clean -fd
git checkout -- .
rm -rf
force push
```

## 6. 技术方案和测试用例仍然并行

历史项目修改也必须保持：

- ARCH/DEV 更新技术方案。
- TEST 更新测试用例。
- 两边并行。
- 中间不互相沟通。
- 有需求问题各自找 PDM。
- 本地产物分开。
- Markdown 和 Excel 都要。

修改前应先做影响分析：

```text
1. 需求变化是什么？
2. 哪些现有功能会受影响？
3. 哪些接口、数据、流程、权限会变？
4. 有没有兼容性风险？
5. 哪些测试用例需要新增或更新？
6. 是否需要用户审批后才能开发？
```

## 7. 历史项目代码修改流程

推荐流程：

```text
用户 -> 飞书 -> PM
PM -> PDM 澄清变更需求
PM -> ARCH/DEV 读取历史方案并更新技术方案
PM -> TEST 读取历史测试用例并更新测试用例
PM -> 汇总影响范围和执行计划给用户
用户审批
PM -> DEV 执行代码修改
PM -> TEST 执行验证
PM -> SEC 做必要安全审查
PM -> 用户通知结果
```

DEV 执行时仍然限制在项目 workspace：

```text
/home/ubuntu/cccagents/workspaces/<project_id>/repo
```

产物和日志仍然限制在：

```text
/home/ubuntu/cccagents/projects/<project_id>/
```

## 8. 修改后的验证

在项目 repo 内运行项目自己的测试命令。

示例：

```bash
cd /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
# 按项目类型选择：
npm test
pytest -q
go test ./...
cargo test
```

如果修改了 cccagents 自身，则运行：

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/pytest -q tests
```

验证结果要保存到：

```text
/home/ubuntu/cccagents/projects/<project_id>/08-logs/hermes-runs/<run_id>/
```

## 9. 修改后的用户通知

PM 通知用户时应包含：

```text
1. 修改了什么。
2. 哪些文件/模块受影响。
3. 测试是否通过。
4. 是否有未解决风险。
5. 是否需要用户进一步审批，例如部署、推送、合并 PR。
```

通知前必须脱敏：

- API Key
- Feishu secret
- token
- Authorization/Bearer
- 真实用户敏感信息

## 10. 历史项目常见场景

### 10.1 小 bug 修复

```text
飞书消息示例：
修改历史项目 <project_id>：修复 xxx bug。
请先复现问题，再让 DEV 修复，让 TEST 验证回归。
```

注意：先复现，再修复；不要猜测式修改。

### 10.2 新增功能

```text
飞书消息示例：
修改历史项目 <project_id>：新增 xxx 功能。
请 PDM 澄清需求，ARCH/DEV 写技术方案，TEST 并行写测试用例，等我审批后再开发。
```

注意：功能变更需要方案和测试用例。

### 10.3 改接口或数据结构

```text
飞书消息示例：
修改历史项目 <project_id>：调整 xxx 接口/数据结构。
请做影响范围分析，重点看调用链、返回数据、保存逻辑和测试覆盖。
```

注意：从行为变化判断影响，不只按字段 grep 判断。

### 10.4 生产紧急问题

```text
飞书消息示例：
修改历史项目 <project_id>：线上紧急问题 xxx。
请先定位根因和影响范围，不要直接改代码。需要我审批高风险操作。
```

注意：紧急问题也要先找根因，不能随机试修。

## 11. 不要做的事

- 不要新建 project_id 来修改旧项目。
- 不要覆盖旧技术方案和测试用例。
- 不要删除历史日志。
- 不要跳过 PDM 需求澄清。
- 不要让 TEST 直接参考 ARCH/DEV 未审批的中间方案。
- 不要在未审批时执行部署、删除、force push、服务器 reboot。
- 不要把真实密钥写入变更记录、日志、飞书消息或 Git。

## 12. 相关文档

新项目启动：

```text
docs/new-project-startup-guide.md
```

项目总说明：

```text
docs/project-overview-and-operations-guide.md
```

新服务器部署：

```text
docs/final-new-server-deployment-guide.md
```
