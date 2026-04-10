<div align="center">

# 🌸 BrechaGenero

### Dashboard interactivo sobre brechas de género, maternidad, cuidados y participación de las mujeres en el Perú

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Dash](https://img.shields.io/badge/Dash-Interactive%20Dashboard-6E40C9?logo=plotly)
![Plotly](https://img.shields.io/badge/Plotly-Visualizaci%C3%B3n-3F4F75?logo=plotly)
![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-success)
![Tema](https://img.shields.io/badge/Tema-Brecha%20de%20g%C3%A9nero-ff69b4)

</div>

---

## ✨ Descripción general

Este proyecto desarrolla un **dashboard interactivo** orientado a visibilizar y analizar la **brecha de género** en el Perú, poniendo especial énfasis en la **maternidad**, la **penalización asociada al cuidado**, la **autonomía económica femenina** y la **participación política de las mujeres**.

La propuesta parte de una idea central: la desigualdad no se expresa únicamente en ingresos o empleo, sino también en el tiempo disponible, la distribución del trabajo de cuidados, la posibilidad de desarrollar una trayectoria profesional sostenida y el acceso real a espacios de representación y liderazgo.

En ese sentido, la **maternidad** no se aborda como una condición individual aislada, sino como una dimensión estructural que influye en las oportunidades laborales, económicas y públicas de las mujeres. Por ello, el proyecto busca mostrar cómo las brechas en empleo, ingresos, pobreza, educación, cuidados y liderazgo político pueden observarse de manera integrada y comprensible mediante herramientas de ciencia de datos y visualización interactiva.

---

## 🎯 Objetivo

Construir una herramienta accesible, visual e interpretable que permita explorar la relación entre:

- la situación socioeconómica de las mujeres,
- la penalización de la maternidad,
- la carga de cuidados,
- y la participación y liderazgo político femenino en el Perú.

El objetivo final es **transformar datos en evidencia útil** para apoyar la discusión pública y el diseño de políticas orientadas a la igualdad de género.

---

## 👩‍👧‍👦 ¿Por qué resaltar la maternidad?

La maternidad ocupa un lugar central en este proyecto porque muchas de las desigualdades que enfrentan las mujeres en el mercado laboral y en la vida pública no provienen únicamente de normas formales, sino de una distribución desigual del trabajo doméstico y de cuidados.

Cuando el cuidado de niñas, niños y otras personas dependientes recae principalmente sobre las mujeres, se reduce su tiempo disponible, se interrumpen trayectorias laborales, disminuyen sus ingresos y se debilitan sus oportunidades de acceder a espacios de decisión. Así, la **penalización de la maternidad** no solo impacta el empleo, sino también la autonomía, la visibilidad y el liderazgo.

Este dashboard busca hacer visible esa relación mediante indicadores comparables, series temporales y visualizaciones que permitan entender que la desigualdad política y económica también se conecta con la organización social del cuidado.

---

## 📊 ¿Qué muestra el dashboard?

El dashboard integra dimensiones clave para el análisis de la brecha de género:

- **Participación política femenina**
- **Liderazgo ejecutivo de las mujeres**
- **Indicadores socioeconómicos de la población femenina**
- **Brechas en empleo e ingresos**
- **Pobreza y educación**
- **Penalización de la maternidad**
- **Relación entre cuidados, autonomía económica y liderazgo**

A través de gráficos, mapas, comparaciones temporales y visualizaciones territoriales, la herramienta permite identificar patrones, desigualdades persistentes y contrastes entre departamentos.

---

## 🧩 Principales componentes del proyecto

- `app.py` → aplicación principal del dashboard.
- `app2.py` → versión alternativa o complementaria de la aplicación.
- `data_dashboard/` → datos procesados y archivos auxiliares usados por el dashboard.
- `deploy_space_v4/` → archivos preparados para despliegue en Hugging Face Spaces.
- `readme` → documentación previa del proyecto.
- `Untitled.ipynb` → notebook de pruebas o exploración.

---

## 🗂️ Estructura del repositorio

```bash
BrechaGenero/
├── app.py
├── app2.py
├── data_dashboard/
├── deploy_space_v4/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── data_dashboard/
├── readme
├── Untitled.ipynb
└── README.md
```

---

## 🛠️ Tecnologías utilizadas

- **Python** para procesamiento y análisis de datos.
- **Pandas** y **NumPy** para manipulación de tablas e indicadores.
- **Plotly** para visualizaciones interactivas.
- **Dash** para la construcción del dashboard web.
- **GeoJSON / archivos territoriales** para visualización espacial.
- **Hugging Face Spaces** para despliegue público.

---

## 📁 Fuentes de datos

El proyecto integra fuentes abiertas y procesadas para analizar la situación de las mujeres en el Perú. Entre ellas destacan:

- indicadores socioeconómicos construidos a partir de encuestas de hogares;
- métricas de representación y participación política femenina;
- capas territoriales y archivos auxiliares para análisis departamental.

La lógica del proyecto busca unir dos planos que normalmente se estudian por separado: la **situación material de las mujeres** y su **presencia en espacios de decisión**.

---

## 🚀 Ejecución local

### Opción 1: ejecutar la app principal

```bash
python app.py
```

### Opción 2: ejecutar la versión alternativa

```bash
python app2.py
```

Si el entorno requiere instalación de dependencias, pueden utilizarse los paquetes definidos en la carpeta de despliegue o instalar manualmente librerías como `dash`, `plotly`, `pandas` y `pyarrow`.

---

## 🌐 Despliegue

El dashboard puede desplegarse públicamente mediante Hugging Face Spaces. En este proyecto se preparó una versión específica de despliegue dentro de:

```bash
deploy_space_v4/
```

Espacio desplegado:

- https://huggingface.co/spaces/mapsm12/BrechaGeneroV4

Repositorio del proyecto:

- https://github.com/mapsm12/BrechaGenero

---

## 💡 Valor del proyecto

Más que un tablero de indicadores, este proyecto propone una narrativa basada en evidencia: la desigualdad de género no puede comprenderse únicamente desde la representación numérica ni solo desde los ingresos. La experiencia de las mujeres, y en especial la experiencia de la maternidad y del cuidado, atraviesa múltiples dimensiones que se refuerzan entre sí.

Por ello, el dashboard busca ser una herramienta útil para:

- investigación aplicada,
- comunicación pública de datos,
- diseño y monitoreo de políticas públicas,
- y discusión sobre igualdad de oportunidades, corresponsabilidad y democracia paritaria.

---

## 🤝 Equipo

- Miguel Octavio Andrade Pereira
- Alizon Rodriguez Navia
- Adan Ríos Delgado
- Yamina Silva Vidal

---

## 📌 Nota final

Este repositorio busca mantener una lógica de **transparencia, accesibilidad y replicabilidad**, permitiendo revisar tanto el código como la estructura general del dashboard. La finalidad del proyecto es aportar evidencia para comprender mejor la brecha de género en el Perú, con énfasis en la maternidad, los cuidados y el liderazgo de las mujeres.

<div align="center">

### 💜 Datos para comprender. Evidencia para transformar.

</div>
