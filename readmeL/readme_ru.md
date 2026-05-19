[简体中文](readme_zh_cn.md) [繁体中文](readme_zh_tw.md) [日语](readme_ja.md) [英语](readme.md) [俄语](readme_ru.md)

# LTX-Customizer

Преобразует Java-код модели Minecraft (`PartDefinition / CubeListBuilder`) в `.bbmodel` / `.json`, импортируемые в Blockbench.

![Image](pictures/img.png)

## Возможности

- GUI-режим (выбор входного/выходного файла и конвертация в один клик)
- CLI-режим
- Вывод включает `elements` (с UV в `faces`) и иерархию `outliner`
- Поддержка `CubeDeformation.NONE` и `new CubeDeformation(...)`

## Требования

- Python 3.10+
- Windows / macOS / Linux (`tkinter` нужен для GUI)

## Быстрый старт

```powershell
python main.py
```

Откроется GUI: выберите входной Java и выходной `.bbmodel`/`.json`, затем нажмите `Convert`.

## CLI

```powershell
python main.py <input.java> [output.bbmodel/json] [model_name]
```

Пример:

```powershell
python main.py dark_latex_yufeng.java custom_model.bbmodel
```
