[简体中文](readme_zh_cn.md) [繁体中文](readme_zh_tw.md) [日语](readme_ja.md) [英语](readme.md) [俄语](readme_ru.md)

# LTX-Customizer

将 Minecraft Java 模型代码（`PartDefinition / CubeListBuilder`）转换为 Blockbench 可导入的 `.bbmodel` / `.json`。

![Image](pictures/img.png)

## 功能

- 支持 GUI 交互模式（选择输入/输出文件，一键转换）
- 支持命令行模式
- 输出包含 `elements`（含 `faces` UV）和 `outliner` 分层结构
- 兼容 `CubeDeformation.NONE` 与 `new CubeDeformation(...)`

## 环境要求

- Python 3.10+
- Windows / macOS / Linux（GUI 依赖 `tkinter`）

## 快速开始

```powershell
python main.py
```

会打开图形界面，选择输入 Java 和输出 `.bbmodel`/`.json` 后点击 `Convert`。

## 命令行

```powershell
python main.py <input.java> [output.bbmodel/json] [model_name]
```

示例：

```powershell
python main.py dark_latex_yufeng.java custom_model.bbmodel
```

## 打包 EXE

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name LTX-Customizer main.py
```

输出：

- `dist/LTX-Customizer.exe`
