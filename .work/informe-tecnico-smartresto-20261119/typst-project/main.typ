// Informe técnico APF3 SmartResto. Proyecto local con tema nativo de informe.
#import "report-theme.typ": report-accent, report-theme

#show: report-theme.with(
  title: "SmartResto: tecnologías, módulos y estado del proyecto",
  author: "Equipo SmartResto",
  rhythm: "report",
  body-size: 11pt,
  first-line-indent: 0.5in,
  paragraph-spacing: 11pt,
  running-header: false,
)

// Numeración continua en la esquina superior derecha conforme a la guía.
#set page(
  numbering: none,
  header: context {
    set text(font: "Arial", size: 11pt, fill: rgb("#333333"))
    align(right)[#counter(page).display("1")]
  },
)
#show figure: set block(breakable: true)

// Portada: imagen auténtica del repositorio, no arte promocional.
#page(margin: (top: 1.3cm, bottom: 1.3cm, x: 2.54cm), numbering: none)[
  #set par(justify: false, first-line-indent: 0pt, spacing: 0pt)
  #align(center)[
    #text(size: 12pt, weight: 700, fill: report-accent)[INFORME DE AVANCE DE PROYECTO FINAL 3]
    #v(0.35em)
    #text(size: 24pt, weight: 700, fill: rgb("#25272B"))[SMARTRESTO]
    #v(0.25em)
    #text(size: 14pt, fill: rgb("#4D5054"))[Tecnologías, módulos, evidencias visuales y plan de trabajo]
    #v(0.7em)
    #image("assets/login-1440-dark.png", width: 100%)
    #v(0.35em)
    #text(size: 8.5pt, fill: rgb("#62666A"))[Captura de QA conservada en el repositorio; su fecha, navegador y commit de origen no están documentados. Se incluye como evidencia visual histórica, no como verificación de funcionamiento actual.]
    #v(0.55em)
    #text(size: 10pt, weight: 600)[Curso: Innovación y Transformación Digital]
    #v(0.15em)
    #text(size: 9pt)[Facultad de Ingeniería · Ingeniería de Sistemas · Sede Trujillo · Ciclo 2026-1 · Sección 40802]
    #v(0.25em)
    #text(size: 8.5pt)[Integrantes trasladados del APF2, pendientes de confirmación para esta entrega:]
    #text(size: 8.5pt)[Cabanillas Llontop, Diego Rodrigo · Lujan Zavaleta, Wilmer Enrique · Paredes Azabache, Miguel Alejandro · Sandoval Chacón, Nancy Elizabeth]
    #text(size: 8.5pt)[Docente consignado en APF2: Blancas Nuñez, Mitchell Paulo · 19 de noviembre de 2026]
  ]
]

#pagebreak()
#outline(title: [Contenido], indent: 1.3em)
#pagebreak()

#include "chapters/01_mejoras_apf2.typ"
#include "chapters/02_seleccion_tecnologias.typ"
#include "chapters/03_justificacion_tecnica.typ"
#include "chapters/04_plan_trabajo.typ"
#include "chapters/05_desarrollo_preliminar.typ"
#include "chapters/06_impacto.typ"
#include "chapters/07_conclusiones.typ"
#include "chapters/08_referencias.typ"
#include "chapters/09_anexos.typ"
