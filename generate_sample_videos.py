import os
from pathlib import Path
import yaml

SAMPLE_NAMES = [
    "小枫灬游戏解说_2025-09-05_20-08-57_000.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_001.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_002.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_003.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_004.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_005.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_006.ts",
    "小枫灬游戏解说_2025-09-05_20-08-57_007.ts",
]


def load_video_folder():
    cfg_path = Path(__file__).parent / 'config.yaml'
    with open(cfg_path,'r',encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    video_folder = Path(cfg['paths']['video_folder'])
    return video_folder


def main():
    video_folder = load_video_folder()
    video_folder.mkdir(parents=True, exist_ok=True)
    # 先删除旧的占位文件（规则：文件名匹配模式且文件体积很小 < 2KB）
    import re
    pattern = re.compile(r".+_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d{3}\.ts$")
    removed = []
    for f in video_folder.glob('*.ts'):
        try:
            if pattern.match(f.name) and f.stat().st_size <= 2048:
                f.unlink()
                removed.append(f.name)
        except Exception:
            pass
    created = []
    skipped = []
    for name in SAMPLE_NAMES:
        p = video_folder / name
        if p.exists():
            skipped.append(p.name)
            continue
        # 创建一个极小的占位文件（注意：不是合法的ts视频，仅用于排序测试）
        with open(p, 'wb') as f:
            f.write(b'\x00')
        created.append(p.name)
    print(f"目标目录: {video_folder}")
    if removed:
        print(f"已删除旧占位文件 {len(removed)} 个: {removed}")
    print(f"新建 {len(created)} 个文件: {created}")
    if skipped:
        print(f"跳过已存在 {len(skipped)} 个: {skipped}")
    print("完成。注意: 这些只是占位文件，上传会失败，如需真实测试请用 ffmpeg 生成真实片段。")

if __name__ == '__main__':
    main()
