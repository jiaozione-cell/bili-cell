# 自动化直播录制上传工具

本项目是一个围绕 `DouyinLiveRecorder` 构建的自动化直播录制和视频上传工具链。录制组件来源： https://github.com/ihmily/DouyinLiveRecorder

> 底层上传功能依赖开源库 stream_gears：项目源码仓库地址（biliup-rs 子模块）  
> https://github.com/biliup/biliup-rs/tree/master/crates/stream-gears

## 文件说明

- **`up.py` / `up.exe`**: 核心上传脚本（基于 `stream_gears` 库实现）。读取 `config.yaml`，自动发现和排序录制视频，生成封面与标题并上传 B 站；可选删除本地文件并重启录制软件。
- **`ts.py` / `ts.exe`**: 定时备用触发脚本。用于在每天固定时间调用 `up.exe`，以防 `DouyinLiveRecorder` 录制完成后未成功触发上传。
- **`log.py` / `log.exe`** (或 `app.py / app.exe`): 日志 Web 查看器，基于 Flask，将 `.log` 文件内容通过网页展示。
- **`config.yaml`**: 全局配置文件，统一管理路径、行为、上传及录制关联配置。
- **`templates/index.html`**: 日志查看页面模板。
- **`*.bat`**: 批处理脚本（如定时调用、便捷启动）。
- **`*.log`**: 运行日志文件。





## up.exe 使用说明

`up.exe` 为核心上传程序；基于 `stream_gears` 实现上传逻辑。当前版本不接受命令行参数，所有行为通过 `config.yaml` 配置。启动方式：

```powershell
# 方式1：直接双击运行（推荐放同目录日志可在 log.exe 中查看）
./up.exe

# 方式2：由 ts.exe / 计划任务 / 录制软件结束回调触发
```

### 处理流程简述
1. 读取 `config.yaml` 验证必要路径。  
2. 扫描 `paths.video_folder` 下的 `*.ts|*.mp4|*.flv`。  
3. 按文件名末尾数字排序（如: `标题_日期_000.ts`）。  
4. 解析首段文件名得到 标题 + 日期；如存在日期则生成封面 `cover.jpg`。  
5. 组合投稿元数据并调用 `stream_gears.upload_by_app` 上传。  
6. 上传成功（code=0）时可选删除源文件与封面。  
7. 可按配置关闭并重启录制软件。  

### 文件命名要求（建议）
`标题_日期_序号.ext` 例如：`Jiaozi_2025-08-29_000.ts`  
序号应为递增且固定宽度（如 000,001,...）。  
若未检测到 `_000` 结尾文件则使用默认标题且不生成日期封面。

### config.yaml 关键字段
| 路径 | 说明 | 必填 | 示例 |
| ---- | ---- | ---- | ---- |
| `paths.video_folder` | 待上传视频所在目录 | 是 | `C:/..../downloads/抖音直播/Jiaozi` |
| `paths.cookies_file` | B 站登录 cookies JSON | 是 | `C:/.../cookies.json` |
| `paths.log_file` | 主上传日志文件 | 是 | `C:/.../upload.log` |
| `paths.log_file1` | ts.exe日志 | 是 | `C:/.../upload1.log` |
| `paths.recorder_exe_path` | 录制软件 exe 路径，用于重启 | 是 | `C:/.../DouyinLiveRecorder.exe` |
| `paths.name` | 视频文件 是否这个名字（供ts.exe引用） | 是 | `小枫灬游戏解说` |
| `paths.run_path` | `up.exe` 路径（供ts.exe引用） | 是 | `C:/.../up.exe` |
| `recorder.process_name` | 录制软件进程名，用于检测是否在运行 | 是 | `DouyinLiveRecorder.exe` |
| `behavior.delete_after_upload` | 上传成功后是否删除本地文件 | 是 | `true` |
| `upload.only_self` 或顶层 `only_self` | 是否仅自己可见 | 是 | `false` |

优先级：脚本会优先读取顶层 `only_self`；若无则读取 `upload.only_self`。

### Cookies 获取方式

有两种方式可以获取 `cookies.json` 文件：

**方法一：使用 biliup.exe**

`paths.cookies_file` 指向的 cookies JSON 建议通过 `biliup.exe login` 生成：

```powershell
./biliup.exe login
```

获取 `biliup.exe`：

1. 前往发布页面下载对应系统版本： https://github.com/biliup/biliup-rs/releases  
2. 解压后将可执行文件放入任意工具目录（建议与本项目同级）。  
3. 首次运行前可重命名为 `biliup.exe`（若名称带版本号）。  
4. 执行 `./biliup.exe login` 。
5. 程序会生成一个二维码图片 `qrcode.png`，并尝试在命令行中显示。
6. 使用手机 Bilibili App 扫描二维码进行登录。
7. 登录成功后，`cookies.json` 文件会自动在程序根目录下生成
8. 在 `config.yaml` 中配置好 `paths.cookies_file` 指向这个文件即可。

**方法二：使用项目自带的 login.exe**

本项目提供了一个独立的登录程序 `login.exe`，可以通过扫码登录来生成 `cookies.json` 文件。

1. 直接双击运行 `login.exe`。
2. 程序会生成一个二维码图片 `qrcode.png`，并尝试在命令行中显示。
3. 使用手机 Bilibili App 扫描二维码进行登录。
4. 登录成功后，`cookies.json` 文件会自动在程序根目录下生成。
5. 在 `config.yaml` 中配置好 `paths.cookies_file` 指向这个文件即可。




### 上传可见性
`only_self=true` -> 投稿设置为“仅自己可见”（extra-fields 中 `is_only_self:1`），调试阶段建议开启；上线后改为 `false`。

### 删除策略
当 `behavior.delete_after_upload=true`：成功上传后依次删除：
1. 各视频分段文件  
2. 生成的封面 `cover.jpg`（若存在）

## ts.exe 使用说明

`ts.exe` 主要用于“兜底”式定时上传：如果录制进程结束时未能自动执行上传，则在每天的设定时间主动运行 `up.exe` 进行上传。

### 使用概要与命令

工作流程：
- 首选：录制结束自动触发 `up.exe` 上传。
- 兜底：`ts.exe` 在每日设定时间主动调用 `up.exe`，防止漏传。

常用命令：
```powershell
# 每天 03:00 定时（默认）
./ts.exe --daily

# 自定义时间 01:45
./ts.exe --daily --time 01:45

# 立即执行一次（不驻留）
./ts.exe
```

## log.exe 使用说明

`log.exe`  为日志 Web 查看工具，使用 Flask 提供一个简单页面在线查看项目日志文件内容。

### 功能概览
- 列出指定日志目录中的 `.log` 文件
- 选择某个文件后按行展示，带颜色区分级别（INFO/ERROR 等）
- 运行中刷新页面即可看到新追加的日志（简单轮询 / 手动刷新）

### 启动方式
```powershell
./log.exe
```
启动后控制台会显示访问地址（默认 `http://127.0.0.1:5000/`）。

### 页面使用
1. 打开浏览器访问首页
2. 下拉列表选择一个 `.log` 文件
3. 页面展示对应内容；再次刷新获取最新内容

### 日志目录来源
程序内部会读取 `config.yaml`：
```
paths.log_file    -> 主日志所在目录
paths.log_file1   -> ts日志
```
页面会列出这两个日志所在目录下的所有 `.log` 文件。















