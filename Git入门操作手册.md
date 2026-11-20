# Git 入门操作手册

> 整理日期：2026-11-04
> 适用环境：Windows + PowerShell + VS Code + GitHub（SSH 认证）

---

## 目录

1. [核心概念](#一核心概念)
2. [第一次建仓库](#二第一次建仓库)
3. [日常循环](#三日常循环)
4. [添加文件](#四添加文件)
5. [README](#五readme)
6. [SSH 认证配置](#六ssh-认证配置)
7. [出错回退](#七出错回退)
8. [常见报错对照](#八常见报错对照)
9. [速查表](#九速查表)

---

## 一、核心概念

### 四个区域

```
工作区            暂存区            本地仓库           远程仓库
（你改的文件）  →  （add 之后）  →  （commit 之后）  →  （push 之后）
              add              commit             push
```

- 只 `add` 不 `commit` → 什么都没存
- 只 `commit` 不 `push` → 只存在本地，网页上看不到
- `push` 前必须先 `commit`

### 文件状态

```
未跟踪(untracked) --add--> 已暂存(staged) --commit--> 已提交(committed)
        ↑                                              |
        └──────────── 修改(modified) <-----------------┘
```

### Git 与 GitHub

| | Git | GitHub |
|---|---|---|
| 是什么 | 版本控制工具（装在本机） | 基于 Git 的云端托管与协作平台 |
| 作用 | 存档、分支、回退、追溯 | 备份、同步、PR 评审、CI、展示 |
| 依赖 | 不需要 GitHub 也能用 | 离不开 Git |

---

## 二、第一次建仓库

### 完整流程

```
① 装 Git、配身份
        ↓
② 建文件夹 + 放第一个文件
        ↓
③ git init
        ↓
④ add → commit
        ↓
⑤ 网页新建空仓库
        ↓
⑥ git remote add
        ↓
⑦ SSH 认证（一次性）
        ↓
⑧ git push -u origin main
```

### 命令

```powershell
# ① 准备（每台电脑只做一次）
git --version
git config --global user.name  "你的用户名"
git config --global user.email "你的邮箱"

# ② 建文件夹与第一个文件
mkdir C:\Users\你\Desktop\myproject
cd C:\Users\你\Desktop\myproject
Set-Content README.md "# myproject" -Encoding utf8

# ③ 初始化
git init

# ④ 提交
git add README.md
git commit -m "first commit"
git branch -M main

# ⑤ 网页：New repository，名字填 myproject，不要勾 README

# ⑥ 关联远程
git remote add origin git@github.com:用户名/myproject.git
git remote -v

# ⑦ 认证见第六节

# ⑧ 推送
git push -u origin main
```

### 成功标志

```
* [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

`-u` 的作用：建立跟踪关系，以后直接 `git push` / `git pull` 即可。

### 两种顺序

| 顺序 | 做法 | 适用 |
|---|---|---|
| 先本地后远程 | `git init` → 提交 → 网页建仓库 → 关联 → push | 已有现成项目 |
| 先远程后本地 | 网页建仓库 → `git clone` → 改 → push | 全新项目、多台电脑 |

---

## 三、日常循环

```powershell
git pull                      # 开工前同步（多人协作必须）
git status                    # 看改了什么
git add .                     # 加入暂存区
git commit -m "说明改了什么"   # 存档
git push                      # 上传
```

记忆口诀：**改 → 看 → 加 → 存 → 推。**

### commit message 建议

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | 修 bug |
| `docs:` | 文档 |
| `refactor:` | 重构 |
| `test:` | 测试 |
| `chore:` | 杂项（配置、依赖） |

示例：`feat: 添加登录页面表单校验`

---

## 四、添加文件

### 主线

```
放进仓库目录 → git status 确认 → git add 暂存 → commit → push
```

### 命令行

```powershell
cd C:\Users\你\Desktop\myproject

# 放文件（三选一）
New-Item notes.md -ItemType File
Set-Content notes.md "# 笔记" -Encoding utf8
Copy-Item "C:\Users\你\Desktop\某文件.pdf" -Destination .

# 看状态
git status                    # 出现在 Untracked files = 位置正确

# 暂存
git add notes.md              # 单个
git add .                     # 全部

# 提交推送
git commit -m "docs: 添加 notes.md"
git push
```

### VS Code 对应操作

| 步骤 | 操作 | 等价命令 |
|---|---|---|
| 打开仓库 | 文件 → 打开文件夹 | — |
| 看状态 | 源代码管理面板（Ctrl+Shift+G） | `git status` |
| 暂存 | 文件右边点 `+` | `git add` |
| 提交 | 输入说明 → `✓ 提交`（Ctrl+Enter） | `git commit -m` |
| 推送 | 左下角 `1↑` / 同步更改 | `git push` |
| 撤销暂存 | 文件右边点 `−` | `git restore --staged` |
| 丢弃修改 | 文件右边点 `↩`（危险） | `git restore` |

状态字母：`U` 未跟踪、`M` 已修改、`A` 已暂存、`D` 已删除。

### git add 的几种写法

| 写法 | 作用 |
|---|---|
| `git add 文件名` | 单个文件 |
| `git add 文件夹/` | 整个文件夹 |
| `git add .` | 当前目录所有改动（最常用） |
| `git add -A` | 全部，含删除和改名 |
| `git add -u` | 只加已跟踪文件的改动 |
| `git add "我的 文件.md"` | 含空格/中文要加引号 |

### 特殊场景

| 场景 | 做法 |
|---|---|
| 整个文件夹 | `git add 资料/` |
| 空文件夹 | Git 不跟踪空目录，放一个 `.gitkeep` |
| 删除文件 | 删掉 → `git add -A` → commit |
| 重命名 | `git mv 旧名 新名` |
| 不想提交 | 写进 `.gitignore` |
| 大文件 | `git lfs track "*.psd"` 后 `git add .gitattributes` |
| 已提交的文件要忽略 | 加 `.gitignore` 后 `git rm --cached 文件名` |

### 推荐 .gitignore

```gitignore
build/
install/
log/
__pycache__/
*.pyc
.vscode/
*.log
```

---

## 五、README

- 文件名必须是 `README.md`，放在**仓库根目录**
- 编码必须是 **UTF-8**
- GitHub 会自动渲染显示在仓库首页

### 写入命令

```powershell
Set-Content README.md "# 项目名`n`n一句话说明。" -Encoding utf8
git add README.md
git commit -m "docs: 添加 README"
git push
```

多行内容用 here-string：

```powershell
@"
# 项目名

一句话说明。

## 功能

- 功能一
- 功能二
"@ | Set-Content README.md -Encoding utf8
```

### 模板

```markdown
# 项目名

一句话说明这是做什么的。

## 功能

- 功能一
- 功能二

## 环境

- Windows 10/11
- Python 3.10 / ROS2 Humble

## 安装

```bash
git clone git@github.com:用户名/仓库名.git
cd 仓库名
```

## 使用

```bash
python hello.py
```

## 目录结构

```
项目名/
├── README.md
└── hello.py
```

## 更新日志

- 2026-11-04 初始化仓库
```

---

## 六、SSH 认证配置

### 原理

```
本机生成一对密钥
├─ id_ed25519      私钥  ← 留在本机，绝不外传
└─ id_ed25519.pub  公钥  ← 贴到 GitHub
```

### 步骤

```powershell
# ① 生成密钥（一路回车，密码可留空）
ssh-keygen -t ed25519 -C "你的邮箱"

# ② 复制公钥
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard

# ③ 网页：Settings → SSH and GPG keys → New SSH key
#    Title：设备名
#    Key type：Authentication Key
#    Key：粘贴公钥（ssh-ed25519 开头，一行）

# ④ 测试
ssh -T git@github.com
# 成功：Hi 用户名! You've successfully authenticated...

# ⑤ 改远程地址为 SSH
git remote set-url origin git@github.com:用户名/仓库名.git
git remote -v
```

### 22 端口不通时

新建 `C:\Users\你\.ssh\config`：

```
Host github.com
  HostName ssh.github.com
  Port 443
  User git
```

### 公钥格式自查

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... 你的邮箱
└───┬────┘ └──────────┬──────────┘ └──┬──┘
 密钥类型           base64 本体       注释
```

必须是**一行**，且只贴 `.pub` 公钥。

---

## 七、出错回退

### 决策图

```
代码出错了
├─ 还没 commit
│   └─ git restore 文件
├─ 已 add 未 commit
│   └─ git restore --staged 文件 → git restore 文件
├─ 已 commit 未 push
│   ├─ 保留改动 → git reset --soft HEAD~1
│   ├─ 改说明/补文件 → git commit --amend
│   └─ 全不要 → git reset --hard HEAD~1（先备份！）
├─ 已 push
│   ├─ 自己分支 → git revert（推荐）
│   └─ 共享分支 → 只能 git revert
├─ 合并/变基出错
│   └─ git merge --abort / git rebase --abort
└─ 提交/分支误删
    └─ git reflog → git reset --hard <哈希>
```

### 四种 reset 对比

| 参数 | 提交 | 暂存区 | 工作区文件 |
|---|---|---|---|
| `--soft` | 撤销 | 保留 | 保留 |
| `--mixed`（默认） | 撤销 | 清空 | 保留 |
| `--hard` | 撤销 | 清空 | **也丢弃** |

### 铁律

1. 破坏性操作前先 `git branch backup-xxx`
2. 已推送的共享分支只 `revert`，不 `reset`
3. 找不到东西就 `git reflog`

---

## 八、常见报错对照

| 报错 | 原因 | 解决 |
|---|---|---|
| `Recv failure: Connection was reset` | 网络被阻断/代理未配置 | 配代理或改 SSH |
| `Password authentication is not supported` | GitHub 禁用账号密码 | 用 SSH 密钥或 PAT |
| `Invalid username or token` | 用户名为邮箱、密码填了登录密码 | Username 填用户名，Password 填 token |
| `Permission denied (publickey)` | 公钥未添加或加错账号 | 重新添加公钥，`ssh -T` 测试 |
| `Repository not found` | 远程仓库未创建或地址错 | 网页建仓库，`git remote -v` 核对 |
| `src refspec main does not match any` | 本地分支不叫 main | `git branch -M main` |
| `fetch first` / `rejected` | 远程已有提交 | `git pull --rebase origin main` |
| `nothing to commit` | 只 add 没改，或忘 add | `git status` 检查 |
| `fatal: not a git repository` | 不在仓库目录 | `cd` 进仓库 |
| `detected dubious ownership` | 文件夹所有者不一致 | `git config --global --add safe.directory <路径>` |
| 中文乱码 | 文件是 UTF-16 | 用 `Set-Content -Encoding utf8` 重写 |

---

## 九、速查表

### 建仓库（一次性）

```powershell
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin git@github.com:用户名/仓库名.git
git push -u origin main
```

### 日常循环

```powershell
git pull → git add . → git commit -m "说明" → git push
```

### 常用命令

| 目的 | 命令 |
|---|---|
| 看状态 | `git status` |
| 看历史 | `git log --oneline --graph` |
| 看差异 | `git diff` |
| 暂存 | `git add .` |
| 提交 | `git commit -m "说明"` |
| 推送 | `git push` |
| 拉取 | `git pull` |
| 建分支 | `git switch -c 分支名` |
| 切分支 | `git switch 分支名` |
| 合并 | `git merge 分支名` |
| 丢弃修改 | `git restore 文件` |
| 撤销提交（保改动） | `git reset --soft HEAD~1` |
| 撤销已推送提交 | `git revert <哈希>` |
| 找回误删 | `git reflog` |
| 临时保存 | `git stash` / `git stash pop` |
| 打标签 | `git tag v1.0.0` |

### 记忆口诀

> **init 建库 → add 挑文件 → commit 存档 → remote 连远程 → push 上传。**
> **SSH 配一次，以后不输密码。**
