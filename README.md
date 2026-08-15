# Images to PPTX

Десктоп-приложение: скриншот выбранной области по горячей клавише, сохранение в `slide-1.png`, `slide-2.png`, … и сборка презентации PPTX (одно изображение — один слайд).

## Требования

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Windows или Linux (X11). На Linux Wayland глобальная клавиша `F9` может не работать — используйте кнопку «Сделать снимок».

## Запуск из исходников

```bash
git clone <url-репозитория>
cd images-to-pptx
uv sync
uv run images-to-pptx
```

Если репозиторий уже на диске:

```bash
cd images-to-pptx
uv sync
uv run images-to-pptx
```

`uv sync` создаёт `.venv` и ставит зависимости из `pyproject.toml` / `uv.lock`.

Альтернатива:

```bash
uv run python -m images_to_pptx
```



## Как пользоваться

1. Укажите папку сохранения (по умолчанию `~/Pictures/slides`).
2. При необходимости нажмите **Выбрать область** и выделите прямоугольник мышью (`Esc` или ПКМ — отмена). Без области снимается весь экран. **Сбросить область** возвращает полный экран.
3. Сделайте снимок клавишей **F9** или кнопкой **Сделать снимок**. Файлы: `slide-1.png`, `slide-2.png`, …
4. Нажмите **Собрать презентацию** и выберите путь для `.pptx`.

Закрытие окна сворачивает программу в трей. Полный выход — кнопка **Выход** в окне или пункт **Выход** в меню трея.

Настройки (папка и область) хранятся в:

- Linux: `~/.config/images-to-pptx/config.json`
- Windows: `%APPDATA%\images-to-pptx\config.json`



## Сборка бинарника

Собирать нужно на той ОС, для которой нужен файл (кросс-компиляции нет).

```bash
uv sync --group dev
uv run pyinstaller build.spec
```

Результат:

- Linux: `dist/images-to-pptx`
- Windows: `dist/images-to-pptx.exe`

Запуск собранного файла:

```bash
./dist/images-to-pptx          # Linux
dist\images-to-pptx.exe        # Windows
```

