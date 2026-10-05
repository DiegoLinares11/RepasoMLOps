"""
Convierte un script .py en formato "percent" (# %% / # %% [markdown]) a un
notebook .ipynb, lo EJECUTA y guarda las salidas.

Uso:
    python tools/build_nb.py 02-regresion-lineal/repaso.py            # genera repaso.ipynb
    python tools/build_nb.py 02-regresion-lineal/repaso.py --no-exec  # solo convierte

Así cada tema se escribe como script (fácil de versionar y leer en el
teléfono) y también queda como notebook ejecutado con gráficas.
"""
import sys, re, pathlib
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell


def parse_percent(text: str):
    cells = []
    kind, buf = None, []
    for line in text.splitlines():
        m = re.match(r"^# %%\s*(\[markdown\])?\s*$", line)
        if m:
            if kind is not None:
                cells.append((kind, "\n".join(buf).strip("\n")))
            kind = "markdown" if m.group(1) else "code"
            buf = []
        else:
            buf.append(line)
    if kind is not None:
        cells.append((kind, "\n".join(buf).strip("\n")))
    out = []
    for kind, src in cells:
        if not src.strip():
            continue
        if kind == "markdown":
            # quitar el prefijo "# " de cada línea
            src = "\n".join(re.sub(r"^# ?", "", l) for l in src.splitlines())
            out.append(new_markdown_cell(src))
        else:
            out.append(new_code_cell(src))
    return out


def main():
    src = pathlib.Path(sys.argv[1])
    execute = "--no-exec" not in sys.argv
    nb = new_notebook(cells=parse_percent(src.read_text(encoding="utf-8")))
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    if execute:
        from nbclient import NotebookClient
        client = NotebookClient(nb, timeout=1200, kernel_name="python3",
                                resources={"metadata": {"path": str(src.parent)}})
        client.execute()
    dst = src.with_suffix(".ipynb")
    nbformat.write(nb, dst)
    print("ok ->", dst)


if __name__ == "__main__":
    main()
