# PKUXKX MUD 客户端使用说明

## 启动客户端

在终端中执行以下命令启动客户端：
```bash
python3 mud_agent.py &
```
注意：末尾的 `&` 表示在后台运行。

## 重要文件位置

- 日志文件：`/Users/tiansheng/Workspace/python/mud/mud_output.log`
- 输入管道：`/Users/tiansheng/Workspace/python/mud/mud_input_pipe`
- PID文件：`mud.pid`

## 基本操作

1. 查看游戏输出：
```bash
tail -f mud_output.log
```

2. 发送游戏命令：
```bash
echo "命令" > mud_input_pipe
```

3. 停止客户端：
```bash
kill $(cat mud.pid)
```

## 连接信息

- 服务器：`mud.pkuxkx.net:8081`
- 用户名：`daymade`

## 常用游戏命令

1. 基础命令：
- `look` - 查看当前环境
- `hp` - 查看角色状态（生命值、精力等）
- `score` - 查看角色详细信息
- `help` - 查看帮助系统
- `help newbie` - 查看新手指南
- `help faq` - 查看常见问题

2. 任务相关：
- `jq` 或 `jobquery` - 查询当前任务进度

3. 求助系统：
- `helpme ask <问题>` - 向高手提问

4. 帮助系统操作：
- 空格或回车 - 继续查看下一页
- `q` - 退出查看
- `b` - 查看上一页

## 注意事项

1. 确保在运行客户端前已安装所有必要的依赖
2. 客户端会自动记录所有游戏输出到日志文件
3. 使用管道发送命令时不需要额外的换行符
4. 停止客户端时建议使用 PID 文件而不是直接 kill 进程 