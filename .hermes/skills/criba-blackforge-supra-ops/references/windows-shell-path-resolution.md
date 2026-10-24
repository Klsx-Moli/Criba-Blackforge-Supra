# Windows shell & path resolution (MSYS/git-bash)

## Shell
- `terminal` tool corre **bash (git-bash/MSYS)**, NO PowerShell/cmd.exe.
- Sintaxis POSIX: `ls`, `$HOME`, `&&`, `|`, single-quoted strings.
- PowerShell builtins (`Get-ChildItem`, `$env:FOO`) NO funcionan — usa POSIX
  equivalents (`ls`, `$FOO`).

## Path conversion — HAY DOS MUNDOS
1. **MSYS paths** (`/c/Users/...`, `/c/astra_work/...`): funcionan para builtins
   bash (`cd`, `ls`). `cwd` reportado como `C:\\...` es nomralizado por git.
2. **Native Windows paths** (`C:/Users/...`, `C:\Users\...`): son los que
   necesitan herramientas NATIVAS (git, rg, node, python).

## Pitfall crítico: `git -C` y paths
`-C` es un builtin de git que cambia cwd. **MSYS path conversion está
DESHABILITADA** en este entorno, así que:
- `git -C /c/Users/x` → FALLA: "cannot change to" / "No such file or directory"
- `node /tmp/a.js` → FALLA: "not found" aunque `cd /c/Users/x` (bash builtin)
  funcione.
- **Fix:** pasa paths nativos con forward-slash `C:/Users/x/...` a herramientas
  nativas. Nunca uses `/c/...` con `git -C`, `node`, `rg`, etc.

## Variables de entorno
- `$TMPDIR` → `C:\Users\KLSX\AppData\Local\hermes\cache\scratch` (scratch dir
  propio de Hermes). Escribe temporales allí, NUNCA bajo system temp.
- `$LOCALAPPDATA/Temp` también usable para herramientas nativas.
- `$HOME` → `C:\Users\KLSX` (no el hostname).

## Python
- `python3` NO existe; `python` → 3.14.7 (sistema) o `.venv/Scripts/python.exe`.
- `pip` → `python3.11`; `uv` está instalado.
- venv: activa una vez por sesión (`source .venv/Scripts/activate`), no por
  comando. Siempre usa `.venv/Scripts/python.exe` para ejecutar pytest.
