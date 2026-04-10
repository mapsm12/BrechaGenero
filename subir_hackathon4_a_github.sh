#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/datos/proyectos/Hackathon4"
REPO_URL="https://github.com/mapsm12/BrechaGenero.git"
BRANCH="hackathon4-import-$(date +%Y%m%d-%H%M%S)"

cd "$PROJ"

echo "========================================"
echo "Proyecto origen:"
echo "$PROJ"
echo "========================================"
pwd
ls

# ------------------------------------------------------------
# Config Git
# ------------------------------------------------------------
git config --global user.name "miguel"
git config --global user.email "mandrade@igp.gob.pe"

# ------------------------------------------------------------
# Inicializar repo git local si no existe
# ------------------------------------------------------------
if [ ! -d ".git" ]; then
    git init -b main
fi

# ------------------------------------------------------------
# .gitignore básico
# ------------------------------------------------------------
touch .gitignore

append_if_missing() {
    local line="$1"
    grep -qxF "$line" .gitignore || echo "$line" >> .gitignore
}

append_if_missing "__pycache__/"
append_if_missing ".ipynb_checkpoints/"
append_if_missing "*.pyc"
append_if_missing "*.pyo"
append_if_missing ".DS_Store"
append_if_missing ".env"
append_if_missing ".venv/"
append_if_missing "venv/"
append_if_missing "env/"
append_if_missing "*.log"
append_if_missing "data_dashboard.zip"

# ------------------------------------------------------------
# Quitar del índice cosas que no quieres versionar
# ------------------------------------------------------------
git rm -r --cached --ignore-unmatch __pycache__ .ipynb_checkpoints >/dev/null 2>&1 || true
git rm --cached --ignore-unmatch data_dashboard.zip >/dev/null 2>&1 || true

# ------------------------------------------------------------
# Mostrar archivos grandes antes de agregar todo
# ------------------------------------------------------------
echo
echo "========================================"
echo "Archivos > 45 MiB"
echo "========================================"
find . -type f -size +45M -not -path './.git/*' -exec ls -lh {} \; || true

echo
echo "Si arriba aparecen archivos demasiado grandes, considera excluirlos antes del push."
echo

# ------------------------------------------------------------
# Agregar y commit
# ------------------------------------------------------------
git add .
git status

if ! git diff --cached --quiet; then
    git commit -m "Importo proyecto completo desde Hackathon4"
else
    echo "No hay cambios nuevos para commit."
fi

# ------------------------------------------------------------
# Configurar remoto correcto
# ------------------------------------------------------------
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git remote -v

# ------------------------------------------------------------
# Traer remoto
# ------------------------------------------------------------
git fetch origin || true

# ------------------------------------------------------------
# Crear rama nueva local
# ------------------------------------------------------------
git switch -C "$BRANCH"

# ------------------------------------------------------------
# Pedir PAT sin mostrarlo
# ------------------------------------------------------------
read -s -p "Pega tu GitHub PAT: " GITHUB_PAT
echo

ASKPASS_SCRIPT="$(mktemp)"
cat > "$ASKPASS_SCRIPT" <<'EOF'
#!/usr/bin/env sh
case "$1" in
  *Username*) printf "%s\n" "mapsm12" ;;
  *Password*) printf "%s\n" "$GITHUB_PAT" ;;
  *) printf "\n" ;;
esac
EOF
chmod 700 "$ASKPASS_SCRIPT"

export GITHUB_PAT
export GIT_ASKPASS="$ASKPASS_SCRIPT"
export GIT_TERMINAL_PROMPT=0

# ------------------------------------------------------------
# Push a la rama nueva
# ------------------------------------------------------------
git push -u origin "$BRANCH"

# ------------------------------------------------------------
# Limpieza
# ------------------------------------------------------------
rm -f "$ASKPASS_SCRIPT"
unset GITHUB_PAT GIT_ASKPASS GIT_TERMINAL_PROMPT

echo
echo "========================================"
echo "LISTO"
echo "========================================"
echo "Se subió la rama:"
echo "  $BRANCH"
echo
echo "Ahora entra a GitHub y crea un Pull Request hacia main."
