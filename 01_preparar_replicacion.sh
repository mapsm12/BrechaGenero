#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_DIR="$HOME/datos/proyectos/Hackathon5"
REPO_ORIG_URL="https://github.com/mapsm12/BrechaGenero.git"

# Carpeta del repo original clonado solo como referencia
REPO_ORIG_DIR="$BASE_DIR/BrechaGenero_origen"

# Carpeta vacía donde construirás la réplica paso a paso
REPLICA_DIR="$BASE_DIR/BrechaGenero_replica"

# ============================================================
# CREAR ESTRUCTURA BASE
# ============================================================
mkdir -p "$BASE_DIR"
cd "$BASE_DIR"

echo "========================================"
echo "1. Clonando repo original como referencia"
echo "========================================"
if [ ! -d "$REPO_ORIG_DIR/.git" ]; then
    git clone "$REPO_ORIG_URL" "$REPO_ORIG_DIR"
else
    echo "El repo original ya existe en: $REPO_ORIG_DIR"
fi

echo "========================================"
echo "2. Creando carpeta vacía para la réplica"
echo "========================================"
mkdir -p "$REPLICA_DIR"/{app,scripts,data/raw,data/processed,data/external,docs,notebooks,outputs}

# Archivos para que Git mantenga carpetas vacías
touch "$REPLICA_DIR"/data/raw/.gitkeep
touch "$REPLICA_DIR"/data/processed/.gitkeep
touch "$REPLICA_DIR"/data/external/.gitkeep
touch "$REPLICA_DIR"/app/.gitkeep
touch "$REPLICA_DIR"/scripts/.gitkeep
touch "$REPLICA_DIR"/docs/.gitkeep
touch "$REPLICA_DIR"/notebooks/.gitkeep
touch "$REPLICA_DIR"/outputs/.gitkeep

echo "========================================"
echo "3. Creando README inicial"
echo "========================================"
cat > "$REPLICA_DIR/README.md" << 'EOF'
# BrechaGenero_replica

Estructura inicial vacía para replicar el proyecto paso a paso.

## Estructura
- app/            -> app/dashboard
- scripts/        -> scripts de procesamiento
- data/raw/       -> datos originales descargados
- data/processed/ -> datos procesados para dashboard
- data/external/  -> fuentes adicionales
- docs/           -> documentación
- notebooks/      -> pruebas y exploración
- outputs/        -> salidas temporales o figuras

## Flujo sugerido
1. Revisar el repo original clonado como referencia.
2. Copiar solo los scripts necesarios a esta réplica.
3. Descargar y organizar las bases de datos en data/raw/.
4. Procesar datos hacia data/processed/.
5. Incorporar la app en app/.
6. Versionar con Git y subir al remoto.
EOF

echo "========================================"
echo "4. Creando .gitignore"
echo "========================================"
cat > "$REPLICA_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Entornos
.venv/
venv/
env/
.env

# Jupyter
.ipynb_checkpoints/

# Mac / Linux
.DS_Store

# Salidas pesadas
outputs/*
!outputs/.gitkeep

# Datos crudos/procesados grandes
data/raw/*
!data/raw/.gitkeep

data/processed/*
!data/processed/.gitkeep

data/external/*
!data/external/.gitkeep
EOF

echo "========================================"
echo "5. Inicializando git en la réplica vacía"
echo "========================================"
cd "$REPLICA_DIR"

if [ ! -d ".git" ]; then
    git init -b main
else
    echo "La réplica ya tenía git inicializado."
fi

git add .
echo "Estructura lista. Si quieres, puedes hacer el primer commit con:"
echo "git commit -m 'Estructura inicial vacía para réplica'"

echo
echo "========================================"
echo "RUTAS IMPORTANTES"
echo "========================================"
echo "Repo original: $REPO_ORIG_DIR"
echo "Réplica vacía: $REPLICA_DIR"

echo
echo "========================================"
echo "LISTADO BÁSICO"
echo "========================================"
find "$REPLICA_DIR" -maxdepth 3 | sort
