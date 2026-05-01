# Changelog

## [1.1.0] – 2026-05-01

### Añadido
- Soporte para `.html`, `.htm` y `.xhtml`
- Incrustación de imágenes:
  - remotas (http/https)
  - locales
- Exclusión automática del HTML generado previamente
- Opciones de línea de comandos:
  - nombre del archivo de salida
  - título del documento
  - ocultar nombres de fichero
  - mostrar versión
- Ayuda detallada por `-h / --help`

### Mejorado
- Preparación para impresión:
  - salto de página por documento
  - evitar títulos huérfanos
  - evitar figuras partidas
- Separación visual clara entre documentos en pantalla
- CSS más robusto y compatible

### Mantenido
- Soporte completo de MHTML con recursos CID
- Incrustación de imágenes sueltas
- Prefijado de IDs y reescritura de enlaces
- HTML final totalmente autocontenido

---

## v1.0.1 – 2026-04-30
### Added
- Unificación de archivos MHTML en HTML autocontenido
- Incrustación de imágenes y CSS
- Reescritura de anclas y enlaces internos
- Optimización para impresión