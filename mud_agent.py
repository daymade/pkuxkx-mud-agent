#!/usr/bin/env python3
import telnetlib
import time
import threading
import os
import sys
import signal
import atexit
import select
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler("mud_agent.log")
    ]
)
logger = logging.getLogger("mud_agent")
console = Console()

# MUD连接信息
HOST = os.getenv("MUD_HOST", "mud.pkuxkx.net")
PORT = int(os.getenv("MUD_PORT", "8081"))
USERNAME = os.getenv("MUD_USERNAME")
PASSWORD = os.getenv("MUD_PASSWORD")

if not all([HOST, PORT, USERNAME, PASSWORD]):
    logger.error("请确保设置了所有必要的环境变量。检查 .env 文件。")
    sys.exit(1)

# 文件路径
LOG_FILE = "mud_output.log"
INPUT_PIPE = "mud_input_pipe"
PID_FILE = "mud.pid"

class MudAgent:
    def __init__(self):
        self.running = True
        self.telnet_conn = None
        self.setup_files()
        self.setup_signal_handlers()

    def setup_files(self):
        """初始化必要的文件"""
        # 确保输入管道存在
        try:
            if not os.path.exists(INPUT_PIPE):
                os.mkfifo(INPUT_PIPE)
        except Exception as e:
            logger.error(f"创建管道失败: {e}")
            sys.exit(1)

        # 创建或清空日志文件
        with open(LOG_FILE, 'w') as f:
            f.write(f"====== 北大侠客行 MUD 会话开始 ({time.strftime('%Y-%m-%d %H:%M:%S')}) ======\n")

        # 保存PID
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        atexit.register(self.cleanup)

    def write_log(self, message):
        """写入日志文件"""
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(message)
        except Exception as e:
            logger.error(f"写入日志失败: {e}")

    def connect(self):
        """连接到MUD服务器并登录"""
        try:
            self.telnet_conn = telnetlib.Telnet(HOST, PORT)
            logger.info(f"已连接到 {HOST}:{PORT}")
            self.write_log(f"已连接到 {HOST}:{PORT}\n")

            # 等待服务器欢迎信息
            time.sleep(2)
            welcome = self.read_and_log()
            
            # 等待编码选择提示
            if "Input 1 for GBK, 2 for UTF8, 3 for BIG5" in welcome:
                logger.info("选择UTF-8编码...")
                self.telnet_conn.write(b'2\n')
                time.sleep(2)
                self.read_and_log()
            
            # 发送用户名并等待密码提示
            logger.info(f"发送用户名: {USERNAME}")
            self.telnet_conn.write(USERNAME.encode('utf-8') + b'\n')
            time.sleep(2)
            response = self.read_and_log()
            
            if "此ID档案已存在，请输入密码" in response:
                # 发送密码
                logger.info("发送密码...")
                self.telnet_conn.write(PASSWORD.encode('utf-8') + b'\n')
                time.sleep(2)
                response = self.read_and_log()
                
                # 检查是否需要处理重复登录
                if "您要将另一个连线中的相同人物赶出去，取而代之吗？" in response:
                    logger.info("处理重复登录...")
                    self.telnet_conn.write(b'y\n')
                    time.sleep(2)
                    self.read_and_log()

            self.write_log("登录完成！会话已在后台运行。\n")
            self.write_log("- 使用 'tail -f mud_output.log' 查看MUD输出\n")
            self.write_log("- 使用 'echo \"命令\" > mud_input_pipe' 发送命令\n")
            self.write_log(f"- 使用 'kill $(cat {PID_FILE})' 停止会话\n")

            return True
        except Exception as e:
            logger.error(f"连接错误: {e}")
            self.write_log(f"连接错误: {e}\n")
            return False

    def read_and_log(self):
        """读取并记录MUD输出"""
        try:
            data = self.telnet_conn.read_very_eager()
            if data:
                text = data.decode('utf-8', errors='replace')
                self.write_log(text)
                return text
        except Exception as e:
            logger.error(f"读取输出错误: {e}")
        return ""

    def handle_signal(self, signum, frame):
        """处理信号"""
        logger.info("\n接收到终止信号，正在关闭会话...")
        self.write_log("\n接收到终止信号，正在关闭会话...\n")
        self.running = False
        sys.exit(0)

    def cleanup(self):
        """清理资源"""
        self.running = False
        if self.telnet_conn:
            try:
                self.telnet_conn.close()
            except:
                pass
        self.write_log(f"\n====== 北大侠客行 MUD 会话结束 ({time.strftime('%Y-%m-%d %H:%M:%S')}) ======\n")
        
        # 清理文件
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except:
            pass

    def process_input(self):
        """处理输入管道"""
        pipe_fd = os.open(INPUT_PIPE, os.O_RDONLY | os.O_NONBLOCK)
        
        while self.running:
            try:
                r, _, _ = select.select([pipe_fd], [], [], 0.2)
                if r:
                    command = os.read(pipe_fd, 1024).decode('utf-8').strip()
                    if command:
                        if command.lower() in ["exit", "quit"]:
                            logger.info("接收到退出命令")
                            self.write_log("接收到退出命令，正在关闭会话...\n")
                            self.running = False
                            break

                        logger.debug(f"发送命令: {command}")
                        self.write_log(f"> {command}\n")
                        self.telnet_conn.write(command.encode('utf-8') + b'\n')
            except Exception as e:
                logger.error(f"处理输入时出错: {e}")
                time.sleep(1)

        try:
            os.close(pipe_fd)
        except:
            pass

    def read_mud_output(self):
        """持续读取MUD输出"""
        while self.running:
            try:
                data = self.telnet_conn.read_very_eager()
                if data:
                    text = data.decode('utf-8', errors='replace')
                    self.write_log(text)
            except Exception as e:
                if self.running:
                    logger.error(f"连接中断: {e}")
                    self.write_log(f"\n连接中断: {e}. 尝试重新连接...\n")
                    if self.connect():
                        logger.info("重新连接成功！")
                        self.write_log("重新连接成功！\n")
                    else:
                        logger.error("重新连接失败，退出程序。")
                        self.write_log("重新连接失败，退出程序。\n")
                        self.running = False
                        break
            time.sleep(0.1)

    def run(self):
        """运行主循环"""
        logger.info(f"北大侠客行后台客户端启动，PID: {os.getpid()}")
        console.print("[bold green]北大侠客行后台客户端启动[/bold green]")
        console.print(f"[bold]PID:[/bold] {os.getpid()}")
        console.print(f"[bold]日志文件:[/bold] {os.path.abspath(LOG_FILE)}")
        console.print(f"[bold]输入管道:[/bold] {os.path.abspath(INPUT_PIPE)}")
        console.print("\n[bold]使用方法:[/bold]")
        console.print("1. 查看输出: [cyan]tail -f mud_output.log[/cyan]")
        console.print("2. 发送命令: [cyan]echo \"命令\" > mud_input_pipe[/cyan]")
        console.print(f"3. 停止程序: [cyan]kill $(cat {PID_FILE})[/cyan]")

        if not self.connect():
            logger.error("无法连接到MUD服务器，退出。")
            return

        # 创建读取MUD输出的线程
        output_thread = threading.Thread(target=self.read_mud_output)
        output_thread.daemon = True
        output_thread.start()

        # 创建处理输入的线程
        input_thread = threading.Thread(target=self.process_input)
        input_thread.daemon = True
        input_thread.start()

        # 保持主线程运行
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("\n接收到键盘中断，正在关闭会话...")
            self.write_log("\n接收到键盘中断，正在关闭会话...\n")
        finally:
            self.running = False

def main():
    agent = MudAgent()
    agent.run()

if __name__ == "__main__":
    main() 