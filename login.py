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

        # 3. 轮询等待扫描和登录
        qrcode_key = qrcode_data['data']['qrcode_key']
        cookies_file_path = script_dir / "cookies.json"

        print("请使用B站手机客户端扫描二维码...")

        while True:
            # get_cookies 会轮询二维码状态，登录成功后返回包含 cookies 的 JSON 字符串
            # 它会阻塞直到登录成功、二维码过期或发生错误
            try:
                cookies_info_str = stream_gears.get_cookies(qrcode_key, proxy=None)
                cookies_info = json.loads(cookies_info_str)

                # 根据返回的 code 判断状态
                # code: 0 - 成功
                # code: 86038 - 二维码已失效
                # code: 86090 - 二维码已扫码未确认
                # code: 86101 - 未扫码
                
                code = cookies_info.get('data', {}).get('code')

                if code == 0:
                    print("登录成功！")
                    # 保存到 cookies.json
                    with open(cookies_file_path, 'w', encoding='utf-8') as f:
                        # stream_gears 返回的已经是只包含 cookie 的 dict
                        json.dump(cookies_info['data'], f, ensure_ascii=False, indent=4)
                    
                    print(f"Cookies 已成功保存到 {cookies_file_path}")
                    break
                elif code == 86038:
                    print("二维码已过期，请重新运行脚本。")
                    break
                elif code == 86090:
                    print("已扫描，请在手机上确认登录...")
                elif code == 86101:
                    print("等待扫描...")
                else:
                    print(f"未知状态: {cookies_info}")

                time.sleep(3) # 每3秒查询一次状态

            except Exception as e:
                print(f"轮询过程中发生错误: {e}")
                break

