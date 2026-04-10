data_dashboard v3 generado correctamente

Archivos principales:
- base_dashboard_v3.parquet
- base_dashboard_v3.csv
- metricas_enaho_departamento_anio_v3.csv
- metricas_enaho_nacional_anio_v3.csv
- metricas_jne_departamento_anio_v3.csv
- metricas_jne_nacional_anio_v3.csv
- metricas_integradas_departamento_anio_v3.csv
- metricas_integradas_nacional_anio_v3.csv
- metricas_integradas_departamento_consolidado_v3.csv
- metric_catalog_v3.csv
- dashboard_v3_metadata.json
- departamentos_points_v3.geojson

Nuevas líneas analíticas incluidas:
1) Educación superior y universitaria como habilitadores de liderazgo femenino
2) Intensidad de cuidados (no solo presencia de niño/a <6, sino número de niños/as <6)
3) Cruce maternidad proxy x educación superior
4) Participación política femenina con datos JNE
5) Liderazgo político femenino de alto nivel (gobernaciones + alcaldías)
6) Índice de techo político de mujeres
7) Índice compuesto habilitante de liderazgo femenino (0-100)

IMPORTANTE:
- educación superior proxy = EDU_NIVEL >= 7
- educación universitaria proxy = EDU_NIVEL >= 9
- revisar codificación EDU_NIVEL si la base ENAHO específica difiere
- revisar ETHNICITY_MAP si la codificación ENAHO de etnia difiere