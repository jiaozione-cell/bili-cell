import stream_gears
import qrcode
import json
import time

def login():

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

        print("请使用Bilibili手机客户端扫描上方二维码。")
        print("或者，您也可以在程序同目录下找到 qrcode.png 文件进行扫描。")

        # 同时保存为图片文件
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("qrcode.png")

        # 3. 轮询等待登录结果
        print("等待扫码登录...")
        expiration_time = time.time() + 180  # 设置一个180秒的超时时间
        
        while time.time() < expiration_time:
            # 将完整的JSON字符串传给 login_by_qrcode
            is_logged_in = stream_gears.login_by_qrcode(login_info_str, proxy=None)
            
            if is_logged_in:
                print("登录成功！")
                # 解析返回的JSON字符串
                login_data = json.loads(is_logged_in)
                # 保存为cookies.json
                with open('cookies.json', 'w', encoding='utf-8') as f:
                    json.dump(login_data, f, ensure_ascii=False, indent=4)

                print("Cookie已成功提取并保存到 cookies.json")
            return False
        
    except Exception as e:
        print(f"发生错误: {e}")
        return False

if __name__ == '__main__':
    login()