# Сборка автономного Intel macOS .app для Convert2MD

Эта инструкция предназначена для создания полноценного standalone `.app` пакета под архитектуру Intel (x86_64) на macOS.

> Рекомендуемый вариант: выполнять сборку на реальном Intel Mac или на x86_64 CI runner.

## 1. Подготовка рабочей директории

Откройте терминал в корне проекта:

```bash
cd /Volumes/Work/MyProject/Convert2MD
```

## 2. Создание x86_64 виртуального окружения

```bash
python3 -m venv .venv_x86
source .venv_x86/bin/activate
```

## 3. Установка зависимостей

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt pyinstaller
```

Если в `requirements.txt` есть пакеты с нативными расширениями, убедитесь, что они устанавливаются для x86_64. При необходимости используйте пакетный менеджер для установки dev-библиотек.

## 4. Сборка Intel `.app`

```bash
MACOSX_DEPLOYMENT_TARGET=11.7 python -m PyInstaller --onedir --windowed --target-arch x86_64 --name Convert2MDi convert2md.py --noconfirm
```

После сборки результат должен появиться в:

```bash
dist/Convert2MDi.app
```

## 5. Проверка результата

Проверьте архитектуру исполняемого файла:

```bash
file dist/Convert2MDi.app/Contents/MacOS/Convert2MDi
```

Проверить работу CLI:

```bash
./dist/Convert2MDi.app/Contents/MacOS/Convert2MDi --help
```

Или запустить через `open`:

```bash
open dist/Convert2MDi.app --args convert /path/to/document.docx
```

## 6. Распространённые ошибки и их причины

### `ModuleNotFoundError: No module named 'typer'`

Это означает, что PyInstaller собрал пакет без одной из зависимостей. Убедитесь, что `typer`, `rich` и остальные необходимые модули установлены в `.venv_x86`.

### `IncompatibleBinaryArchError`

Если PyInstaller жалуется на несовместимый native-модуль, например `PIL/_avif.cpython-39-darwin.so`, значит в окружении есть пакет, собранный под arm64. В таком случае:

1. Соберите проект на Intel-машине, чтобы зависимости пришли в правильной архитектуре.
2. Или переустановите проблемный пакет под x86_64 вручную:

```bash
pip uninstall pillow
pip install --no-binary :all: pillow
```

3. Очистите предыдущие артефакты и соберите заново:

```bash
rm -rf build dist *.spec
MACOSX_DEPLOYMENT_TARGET=11.7 python -m PyInstaller --onedir --windowed --target-arch x86_64 --name Convert2MDi convert2md.py --noconfirm
```

## 7. Полезные команды для диагностики

```bash
find .venv_x86/lib/python3.9/site-packages -name "*.so" -o -name "*.dylib"
lipo -info path/to/library.dylib
```

## 8. Рекомендации по использованию

- `--onedir` рекомендуется для отладки и проверки. Если нужно создать единый bundle, можно перейти на `--onefile`, но это усложняет отладку.
- Для конечного распространения лучше подготовить два отдельных пакета:
  - `dist/Convert2MD.app` для Apple Silicon
  - `dist/Convert2MDi.app` для Intel

## 9. Что делать, если нужен universal2-билд

Universal2 возможен только при наличии универсальных (fat) бинарных расширений для всех зависимостей. Если вы хотите universal-билд, сначала убедитесь, что все нативные пакеты установлены как universal, затем запускайте:

```bash
MACOSX_DEPLOYMENT_TARGET=11.7 python -m PyInstaller --onedir --windowed --target-arch universal2 --name Convert2MD convert2md.py --noconfirm
```

Если при этом появляется `IncompatibleBinaryArchError`, значит один из модулей всё ещё одноплатформенный.

---

Если потребуется, могу также добавить в этот файл инструкцию по подписи и нотариации macOS `.app`.