# Convert2MD quick start

## 1. Install prerequisites

Required:

- Python 3.10 or newer;
- Pandoc for DOCX/DOC conversion.

Recommended:

- LibreOffice for safe EMF/WMF conversion;
- Inkscape or ImageMagick as vector-conversion fallbacks;
- Node.js 22.13 or newer for the graphical interface.

macOS:

```bash
brew install pandoc
brew install --cask libreoffice
```

Ubuntu/Debian:

```bash
sudo apt-get install pandoc libreoffice
```

## 2. Install Python dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Verify the CLI:

```bash
python convert2md.py --help
```

## 3. Convert documents

One PDF:

```bash
python convert2md.py convert sample.pdf
```

One DOCX:

```bash
python convert2md.py convert document.docx
```

Custom output path:

```bash
python convert2md.py convert document.docx --output result.md
```

Directory:

```bash
python convert2md.py batch ./documents --recursive
```

The output Markdown contains relative image links. Keep the generated
`picture_<document>/` directory beside the Markdown file.

## 4. Build and run the graphical interface

Build once:

```bash
cd web
npm install
npm run build
cd ..
```

Start:

```bash
venv/bin/python convert2md.py web
```

Open `http://127.0.0.1:3000`.

See [Web interface](web-interface.md).

## 5. Configure diagrams and models

Set the Gemini key through the environment:

```bash
export GEMINI_API_KEY="..."
```

Convert one diagram:

```bash
python convert2md.py diagram diagram.png
```

Inspect the model repository:

```bash
python convert2md.py models
```

Import configuration:

```bash
python convert2md.py models-import models.yaml
```

See [Model management](model-management.md).

## 6. Record historical usage

One request:

```bash
python convert2md.py usage-record \
  --model google:gemini-3.1-flash-lite \
  --input-tokens 12000 \
  --output-tokens 800
```

Import a history file:

```bash
python convert2md.py usage-import usage.csv
```

## 7. Run tests

```bash
venv/bin/python -m pytest -q
```

For the complete documentation map, see [Documentation index](index.md).
