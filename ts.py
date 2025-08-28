import stream_gears
from pathlib import Path
import sys
import json
import logging
import yaml
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import os
import time
import subprocess
import psutil
import argparse

# --- 功能函数 ---

def load_config(config_path):
    """加载完整的配置文件并验证"""
    if not config_path.exists():
        print(f"错误: 配置文件未找到 -> {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"配置文件格式错误: {e}")
            return None
    
    paths_cfg = config.get('paths', {})
    required_paths = ['video_folder', 'log_file1']
    for key in required_paths:
        if key not in paths_cfg:
            print(f"配置文件 'config.yaml' 的 'paths' 部分缺少设置: '{key}'")
            return None
            
    return config

def setup_logging(log_file_path):
    """配置日志系统"""
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"日志系统初始化完成，日志将记录到: {log_file_path}")

def get_sorted_videos(video_folder):
    """扫描并排序视频文件"""
    logging.info(f"正在扫描文件夹: {video_folder}")
    logging.info(f"完整绝对路径为: {video_folder.resolve()}")
    video_paths = list(video_folder.glob('*.ts')) + list(video_folder.glob('*.mp4')) + list(video_folder.glob('*.flv'))

    if not video_paths:
        logging.info("未找到需要的视频文件，程序退出。")
        return []
    return video_paths

def extract_metadata(video_paths):
    """从文件名解析标题和日期"""
    title, date = "默认标题", ""
    first_part_video = next((p for p in video_paths if p.stem.endswith('_000')), None)

    if first_part_video:
        logging.info(f"找到起始视频: {first_part_video.name}，将从中解析标题和日期。")
        try:
            parts = first_part_video.stem.split('_')
            if len(parts) >= 2:
                title, date = parts[0], parts[1]
                logging.info(f"成功解析 -> 标题: '{title}', 日期: '{date}'")
            else:
                logging.warning("文件名格式不符合 '标题_日期_...' 规范，将使用默认标题。")
        except (ValueError, IndexError) as e:
            logging.error(f"解析文件名时出错: {e}，将使用默认标题。")
    else:
        logging.warning("未找到以 '_000' 结尾的视频，将使用默认标题。")
    return title, date

# --- 主程序 ---
def main():
    # 1. 确定根目录 (兼容PyInstaller)
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 .exe 文件，根目录是 .exe 文件所在的目录
        script_dir = Path(sys.executable).parent

    else:
        # 如果是普通的 .py 脚本，根目录是脚本文件所在的目录
        script_dir = Path(__file__).resolve().parent

    config = load_config(script_dir / "config.yaml")
    if not config:
        sys.exit(1)
    paths_cfg = config.get('paths', {})

    # setup_logging(Path(paths_cfg['log_file1'])) # 日志已在启动时初始化
    logging.info(f"脚本所在目录: {script_dir}")

    video_paths = get_sorted_videos(Path(paths_cfg['video_folder']))
    if not video_paths:
        return

    title_from_file, _ = extract_metadata(video_paths)
    logging.info(f"从文件中提取到的标题: {title_from_file}")
    logging.info(f"配置文件中指定的标题: {paths_cfg.get('name')}")
    if title_from_file == paths_cfg.get('name'):
        logging.info("标题匹配成功")
        logging.info(paths_cfg.get('run_path'))
        logging.info("上传程序已启动")
        logging.info("----------------------------------------------------------")
        subprocess.run([paths_cfg.get('run_path')])
        
        
def _parse_time_str(tstr: str):
    """解析 HH:MM 字符串为 (hour, minute)"""
    try:
        parts = tstr.split(':')
        if len(parts) != 2:
            raise ValueError
        h = int(parts[0]); m = int(parts[1])
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        return h, m
    except ValueError:
        raise argparse.ArgumentTypeError('时间格式必须为 HH:MM 且合法，例如 03:00')


def run_daily(target_h: int, target_m: int):
    """保持常驻, 每天指定时间执行 main() 一次。

    逻辑:
      1. 计算下一次执行的目标时间 (今天的 target, 若已过则 +1 天)
      2. 睡眠到目标时间前, 期间每隔一段输出心跳日志
      3. 到点后执行 main()
    """
    logging.info(f"[调度] 已启动每日定时模式: 每天 {target_h:02d}:{target_m:02d} 执行")
    while True:
        now = datetime.now()
        target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        if now >= target:
            target = target + timedelta(days=1)
        wait_sec = (target - now).total_seconds()
        heartbeat = 300  # 心跳间隔秒
        logging.info(f"[调度] 下次执行时间: {target} (剩余 {wait_sec/3600:.2f} 小时)")
        slept = 0
        while slept < wait_sec:
            slice_sec = min(heartbeat, wait_sec - slept)
            time.sleep(slice_sec)
            slept += slice_sec
            remain = wait_sec - slept
            if remain > 0:
                logging.info(f"[调度] 仍在等待: 剩余 {remain/60:.1f} 分钟")
        start_ts = datetime.now()
        logging.info(f"[调度] 开始执行 main() @ {start_ts}")
        try:
            main()
        except Exception as e:
            logging.exception(f"[调度] main() 执行异常: {e}")
        end_ts = datetime.now()
        logging.info(f"[调度] 本次执行结束, 耗时 {(end_ts-start_ts).total_seconds():.1f}s, 等待下一次...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ts.py 脚本 (支持每日定时执行)')
    parser.add_argument('--daily', action='store_true', help='进入常驻模式, 每天固定时间执行一次')
    parser.add_argument('--time', default='03:00', help='每日执行时间 HH:MM, 默认 03:00')
    args = parser.parse_args()

    # --- 日志初始化 ---
    # 提前加载配置以获取日志路径
    if getattr(sys, 'frozen', False):
        script_dir_for_log = Path(sys.executable).parent
    else:
        script_dir_for_log = Path(__file__).resolve().parent
    
    config_for_log = load_config(script_dir_for_log / "config.yaml")
    if not config_for_log:
        # 如果配置加载失败，至少保证控制台有输出
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error("无法加载配置, 日志仅输出到控制台。")
        sys.exit(1)
    
    log_path_str = config_for_log.get('paths', {}).get('log_file1')
    if log_path_str:
        setup_logging(Path(log_path_str))
    else:
        # 如果日志路径未在配置中定义，也保证控制台输出
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.warning("配置文件中未找到 log_file1 路径, 日志仅输出到控制台。")
    # --- 日志初始化结束 ---

    if args.daily:
        hour, minute = _parse_time_str(args.time)
        run_daily(hour, minute)
    else:
        main()