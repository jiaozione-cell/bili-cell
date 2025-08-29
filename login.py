import stream_gears
import qrcode
import json
import time
import logging
import sys
import yaml
from pathlib import Path

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

def login():

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

    setup_logging(Path(paths_cfg['log_file2']))
    logging.info(f"脚本所在目录: {script_dir}")

    """
    使用 stream_gears 进行扫码登录
    """
    try:
        # 1. 获取二维码数据
        # 注意：这里的 proxy 参数是可选的，如果不需要代理可以设为 None
        login_info_str = stream_gears.get_qrcode(proxy=None)
        ("获取二维码成功...")
        
        # 2. 解析URL并生成二维码
        login_info = json.loads(login_info_str)
        qr_url = login_info['data']['url']
        
        # 在终端显示二维码
        qr = qrcode.QRCode()
        qr.add_data(qr_url)
        qr.make(fit=True)
        # invert=True 可以让它在深色背景的终端上正确显示
        qr.print_ascii(invert=True) 
        
        logging.info("请使用Bilibili手机客户端扫描上方二维码。")
        logging.info("或者，您也可以在程序同目录下找到 qrcode.png 文件进行扫描。")

        # 同时保存为图片文件
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("qrcode.png")

        # 3. 轮询等待登录结果
        logging.info("等待扫码登录...")
        expiration_time = time.time() + 180  # 设置一个180秒的超时时间
        
        while time.time() < expiration_time:
            # 将完整的JSON字符串传给 login_by_qrcode
            is_logged_in = stream_gears.login_by_qrcode(login_info_str, proxy=None)
            
            if is_logged_in:
                logging.info("登录成功！")
                # 解析返回的JSON字符串
                login_data = json.loads(is_logged_in)
                # 保存为cookies.json
                with open('cookies.json', 'w', encoding='utf-8') as f:
                    json.dump(login_data, f, ensure_ascii=False, indent=4)

                logging.info("Cookie已成功提取并保存到 cookies.json")
            return False
        
    except Exception as e:
        logging.error(f"发生错误: {e}")
        return False

if __name__ == '__main__':
    login()