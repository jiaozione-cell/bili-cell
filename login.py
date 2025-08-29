import stream_gears
import json
import qrcode  # 确保已经运行 pip install "qrcode[pil]"
import time
import os
import platform
import subprocess
from pathlib import Path

if __name__ == '__main__':
        # 获取脚本所在的目录
        script_dir = Path(__file__).resolve().parent
        print(f"脚本所在目录: {script_dir}")
        script_dir = Path(r"C:\Users\zhang\Desktop\bili")

        qrcode_path = script_dir / "qrcode.png"
        print("正在获取登录二维码...")
        # get_qrcode() 返回一个包含 URL 和 qrcode_key 的 JSON 字符串
        qrcode_data_str = stream_gears.get_qrcode(proxy=None)
        qrcode_data = json.loads(qrcode_data_str)
        
        qrcode_url = qrcode_data['data']['url']
        
        # 2. 生成二维码并保存为图片
        print("二维码已生成，正在保存为图片 qrcode.png ...")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qrcode_url)
        qr.make(fit=True)

        # 在控制台打印二维码
        print("二维码已在控制台显示，请扫描：")
        qr.print_tty()

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qrcode_path)