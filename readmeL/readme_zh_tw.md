[简体中文](readme_zh_cn.md) [繁体中文](readme_zh_tw.md) [日语](readme_ja.md) [英语](readme.md) [俄语](readme_ru.md)

# LTX-Customizer

將 Minecraft Java 模型程式碼（`PartDefinition / CubeListBuilder`）轉換為 Blockbench 可匯入的 `.bbmodel` / `.json`。

![Image](pictures/img.png)

## 功能

- 支援 GUI 互動模式（選擇輸入/輸出檔案，一鍵轉換）
- 支援命令列模式
- 輸出包含 `elements`（含 `faces` UV）與 `outliner` 分層結構
- 相容 `CubeDeformation.NONE` 與 `new CubeDeformation(...)`

## 環境需求

- Python 3.10+
- Windows / macOS / Linux（GUI 依賴 `tkinter`）

## 快速開始

```powershell
python main.py
```

會開啟圖形介面，選擇輸入 Java 與輸出 `.bbmodel`/`.json` 後點擊 `Convert`。

## 命令列

```powershell
python main.py <input.java> [output.bbmodel/json] [model_name]
```

範例：

```powershell
python main.py dark_latex_yufeng.java custom_model.bbmodel
```
