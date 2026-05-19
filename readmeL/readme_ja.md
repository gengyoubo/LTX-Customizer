[简体中文](readme_zh_cn.md) [繁体中文](readme_zh_tw.md) [日语](readme_ja.md) [英语](readme.md) [俄语](readme_ru.md)

# LTX-Customizer

Minecraft Java モデルコード（`PartDefinition / CubeListBuilder`）を Blockbench で読み込める `.bbmodel` / `.json` に変換します。

![Image](pictures/img.png)

## 機能

- GUI モード（入力/出力ファイルを選んでワンクリック変換）
- CLI モード
- `elements`（`faces` UV 含む）と `outliner` 階層を出力
- `CubeDeformation.NONE` と `new CubeDeformation(...)` の両方に対応

## 必要環境

- Python 3.10+
- Windows / macOS / Linux（GUI は `tkinter` が必要）

## クイックスタート

```powershell
python main.py
```

GUI が開くので、入力 Java と出力 `.bbmodel`/`.json` を選んで `Convert` を押してください。

## CLI

```powershell
python main.py <input.java> [output.bbmodel/json] [model_name]
```

例：

```powershell
python main.py dark_latex_yufeng.java custom_model.bbmodel
```
