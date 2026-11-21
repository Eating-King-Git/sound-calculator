# 验证记录

日期：2026-11-21，对应首版 0.1.0。

## 本地已经执行

Windows x64、Python 3.10.11、Tk 8.6。新建独立 venv，从官方 PyPI 安装 Pygame 2.6.1，没有复制旧工程环境。

`python -m unittest discover -v`：**53 项测试全部通过，无跳过**。

| 模块 | 数量 | 主要检查 |
|---|---:|---|
| 计算模型 | 31 | 1+2 回归、乘除优先、连续计算、小数、符号、百分号、平方根、退格、出错恢复、数值与长度限制、局部 Decimal 上下文 |
| 音效 | 15 | 缺依赖、缺设备、缺文件、播放失败、静音开关、路径与清理行为、WAV 参数和可重复生成 |
| Tk 界面 | 7 | 实际 Tk 控件按钮回调、键盘映射、错误文字、音效开关、关闭清理 |

音频模块另使用真实 Pygame 加 dummy 音频驱动检查加载、播放调用、静音、恢复和关闭；这不代表对物理音箱的实际听感验收。

初次图形测试受本地沙箱限制，无法读取 Tcl 初始化文件；在正常 Windows 权限环境使用同一新 venv 运行全部测试通过。项目没有硬编码本机 Tcl 路径或修改系统配置。

## 窗口检查范围

已启动实际计算器窗口并捕获 README 截图，包含简单算式结果。本版没有进行完整的人工键盘／鼠标验收；计算与 Tk 回调的自动测试结果如上。

## 自动检查配置

GitHub Actions 配置 Windows / Python 3.10、Ubuntu / Python 3.12。Ubuntu 使用 Xvfb；两者均设置 `REQUIRE_GUI=1`，不能用跳过 Tk 测试代替通过。自动检查也验证依赖及音效重生成结果。

实际云端结果以 [Actions](https://github.com/Eating-King-Git/sound-calculator/actions/workflows/tests.yml) 为准。macOS 与独立打包 EXE 不在首版验证范围。
