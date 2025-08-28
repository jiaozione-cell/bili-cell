import stream_gears
from pathlib import Path
import sys
import json
import logging
import yaml
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import time
import subprocess
import psutil

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
    required_paths = ['log_file', 'video_folder', 'cookies_file']
    for key in required_paths:
        if key not in paths_cfg:
            print(f"配置文件 'config.yaml' 的 'paths' 部分缺少设置: '{key}'")
            return None
            
    return config

def create_cover_image(date_str, script_dir):
    """根据给定的日期字符串创建一个封面图片，并返回其路径"""
    img_width, img_height = 1146, 717
    bg_color, text_color = (25, 25, 25), (255, 255, 255)
    save_path = script_dir / "cover.jpg"

    try:
        image = Image.new('RGB', (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("msyhbd.ttc", 120)
        except IOError:
            logging.warning("未找到 '微软雅黑 Bold' 字体，将使用默认字体。")
            font = ImageFont.load_default(size=100)

        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), date_str, font=font)
            text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            text_width, text_height = draw.textsize(date_str, font=font)
        
        x, y = (img_width - text_width) / 2, (img_height - text_height) / 2
        draw.text((x, y), date_str, font=font, fill=text_color)
        image.save(save_path, 'JPEG')
        logging.info(f"成功创建封面图片: {save_path}")
        return str(save_path)
    except Exception as e:
        logging.error(f"创建封面图片失败: {e}")
        return None

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
        logging.info("未找到需要上传的视频文件，程序退出。")
        return []

    logging.info("正在根据文件名末尾的数字排序...")
    try:
        video_paths.sort(key=lambda p: int(p.stem.split('_')[-1]))
    except (ValueError, IndexError):
        logging.warning("无法按数字后缀排序，将使用默认字母顺序排序。")
        video_paths.sort()

    logging.info(f"排序完成，将按以下顺序上传 {len(video_paths)} 个视频:")
    for path in video_paths:
        logging.info(f"  => {path.name}")
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

def process_upload_result(result_json_string, video_paths, cover_path, behavior_cfg):
    """处理上传结果，成功则清理文件"""
    upload_data = json.loads(result_json_string)
    if upload_data.get('code') == 0:
        logging.info("视频上传成功！")
        if 'data' in upload_data and 'bvid' in upload_data['data']:
            bvid = upload_data['data']['bvid']
            logging.info(f"视频的 BVID 是: {bvid}")
            logging.info(f"访问链接: https://www.bilibili.com/video/{bvid}")
        
        if behavior_cfg.get('delete_after_upload', False):
            logging.info("准备删除已上传的本地文件...")
            files_to_delete = video_paths + ([Path(cover_path)] if cover_path else [])
            for file_path in files_to_delete:
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logging.info(f"已删除文件: {file_path.name}")
                    except Exception as e:
                        logging.error(f"删除文件 {file_path.name} 失败: {e}")
    else:
        error_code = upload_data.get('code', 'N/A')
        error_message = upload_data.get('message', '无详细信息')
        logging.error(f"上传失败! Code: {error_code}, Message: {error_message}")
        logging.error(f"完整返回数据: {upload_data}")
        sys.exit(1)

# --- 主程序 ---

def main():
    # 1. 确定根目录 (兼容PyInstaller)
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 .exe 文件，根目录是 .exe 文件所在的目录
        script_dir = Path(sys.executable).parent

    else:
        # 如果是普通的 .py 脚本，根目录是脚本文件所在的目录
        script_dir = Path(__file__).resolve().parent

    # 2. 加载配置
    config = load_config(script_dir / "config.yaml")
    if not config:
        sys.exit(1)
    
    paths_cfg = config.get('paths', {})
    behavior_cfg = config.get('behavior', {})

    # 2. 初始化日志
    setup_logging(Path(paths_cfg['log_file']))
    logging.info(f"脚本所在目录: {script_dir}")

    # 3. 获取并排序视频文件
    video_paths = get_sorted_videos(Path(paths_cfg['video_folder']))
    if not video_paths:
        sys.exit(0)

    cookie_file = Path(paths_cfg['cookies_file'])
    if not cookie_file.exists():
        logging.error(f"错误: Cookies 文件未找到 -> {cookie_file}")
        sys.exit(1)

    # 4. 准备上传元数据
    title_from_file, date_str_for_title = extract_metadata(video_paths)
    
    cover_path = ""
    if date_str_for_title:
        final_title = f"直播回放-{title_from_file}-{date_str_for_title}"
        cover_path = create_cover_image(date_str_for_title, script_dir) or ""
    else:
        final_title = title_from_file

    # 读取是否仅自己可见的配置，默认True
    only_self = True
    if 'only_self' in config:
        only_self = bool(config['only_self'])
    elif 'upload' in config and 'only_self' in config['upload']:
        only_self = bool(config['upload']['only_self'])

    """
    上传视频稿件

    :param List[str] video_path: 视频文件路径
    :param str cookie_file: cookie文件路径
    :param str title: 视频标题
    :param int tid: 投稿分区
    :param str tag: 视频标签, 英文逗号分隔多个tag
    :param int copyright: 是否转载, 1-自制 2-转载
    :param str source: 转载来源
    :param str desc: 视频简介
    :param str dynamic: 空间动态
    :param str cover: 视频封面
    :param int dolby: 是否开启杜比音效, 0-关闭 1-开启
    :param int lossless_music: 是否开启Hi-Res, 0-关闭 1-开启
    :param int no_reprint: 是否禁止转载, 0-允许 1-禁止
    :param int open_elec: 是否开启充电, 0-关闭 1-开启
    :param bool up_close_reply: 是否禁止评论, false-关闭 true-开启
    :param bool up_selection_reply: 是否精选评论, false-关闭 true-开启
    :param bool up_close_danmu: 是否禁止弹幕, false-关闭 true-开启
    :param int limit: 单视频文件最大并发数
    :param List[Credit] desc_v2: 视频简介v2
    :param Optional[dtime] int dtime: 定时发布时间, 距离提交大于2小时小于15天, 格式为10位时间戳
    :param Optional[UploadLine] line: 上传线路
    :param Optional[ExtraFields] line: 上传额外参数
    :param Optional[str] proxy: 代理
    """
    video_info = {
        "title": final_title,       # 最终的视频标题 (例如: "游戏解说-2025-08-11")
        "tid": 17,                 # 视频分区ID (171 = 单机游戏)
        "tag": "游戏,单机游戏",     # 视频标签，多个标签用英文逗号隔开
        "copyright": 2,             # 稿件类型 (1 = 自制, 2 = 转载)
        "source": "https://live.douyin.com/439720548986",               # 转载来源 (如果是自制视频，可以留空)
        "desc": "直播回放为自动化录制上传 如有侵权 请联系删除",                 # 视频简介 (可以留空)
        "cover": cover_path,        # 封面图片路径 (如果为空，B站会自动生成)
        "limit": 3,                 # 上传并发线程数
        # B站投稿附加参数: is_only_self=1 表示 "仅自己可见"
        "extra-fields": '{\"is_only_self\":%d}' % (1 if only_self else 0)
    }
    logging.info(f"服务器返回: {video_info['extra-fields']}")

    # 5. 执行上传
    try:
        logging.info(f"开始上传，标题: '{final_title}'")
        result_json = stream_gears.upload_by_app(
            video_path=video_paths,
            cookie_file=cookie_file,
            title=video_info["title"],
            tid=video_info["tid"],
            tag=video_info["tag"],
            copyright=video_info["copyright"],
            source=video_info["source"],
            desc=video_info["desc"],
            cover=video_info["cover"],
            limit=video_info["limit"],
            extra_fields=video_info["extra-fields"]
        )
        logging.info(f"服务器返回: {result_json}")
        
        # 6. 处理结果
        process_upload_result(result_json, video_paths, cover_path, behavior_cfg)

        # 检查并重启录制软件
        recorder_cfg = config.get('recorder', {})
        recorder_process_name = recorder_cfg.get('process_name')
        recorder_exe_path = paths_cfg.get('recorder_exe_path')

        if not recorder_process_name or not recorder_exe_path:
            logging.info("配置文件中未提供 'recorder' 设置或 'recorder_exe_path'，跳过重启录制软件的步骤。")
        else:
            # 预先等待 5 秒再检查（有些录制程序还在写入/退出）
            logging.info("等待 5 秒后再检查录制软件进程状态...")
            time.sleep(5)
            # 检查进程是否在运行
            if any(p.name() == recorder_process_name for p in psutil.process_iter()):
                logging.info(f"检测到 {recorder_process_name} 正在运行，现在关闭它...")
                os.system(f'taskkill /f /im {recorder_process_name}')
                time.sleep(10)  # 等待进程完全关闭
                logging.info(f"{recorder_process_name} 已关闭。")
            else:
                logging.info(f"未检测到 {recorder_process_name} 运行。")

            # 尝试重启
            if Path(recorder_exe_path).exists():
                subprocess.Popen(['start', '', recorder_exe_path], shell=True)
                logging.info(f"{recorder_process_name} 已从路径 '{recorder_exe_path}' 重启。")
            else:
                logging.error(f"配置文件中指定的路径不存在: '{recorder_exe_path}'，无法重启。")

    except RuntimeError as e:
        logging.error(f"上传过程中发生严重错误: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"发生未知错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
