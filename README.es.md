# AgentReplay

**Comprueba qué hace tu agente cuando falla una integración.**

Laboratorio local para agentes que utilizan herramientas: simula incidencias de GitHub, provoca fallos y comprueba el resultado real de sus acciones.

**Versión 0.1.0 alfa.** Python 3.10 o superior, sin dependencias de ejecución. La demo no necesita cuentas, tokens ni claves de IA. Los dos agentes incluidos son políticas programadas; todavía no se ha evaluado un modelo de IA real.

## Demo visual sin instalar

Abre `demo/index.html` con tu navegador: tres escenarios, dos políticas programadas y evidencias paso a paso. Funciona sin conexión. Puedes regenerarla con `python scripts/build_demo.py`. Los informes HTML también incluyen recomendaciones según las comprobaciones fallidas.

## Prueba inmediata

Desde la carpeta del proyecto:

```bash
python -m agentreplay demo
```

Abre estos archivos en el navegador:

- `artifacts/demo/naive/report.html`: política que escribe y reintenta sin comprobar; supera 3 de 10 escenarios.
- `artifacts/demo/cautious/report.html`: política que consulta, revisa todas las páginas y comprueba el estado antes de reintentar; supera 10 de 10.

Los informes permiten desplegar cada llamada y revisar parámetros, respuestas y errores. El caso principal provoca un timeout después de guardar una incidencia: reintentar directamente crea un duplicado y suspende la evaluación.

## Qué incluye

Diez escenarios: operación normal, timeout antes y después de guardar, límite de peticiones, permisos insuficientes, duplicados, paginación, instrucciones maliciosas en contenido, alcance por repositorio y falta de aprobación.

La evaluación comprueba el estado final, las acciones fuera de alcance, el respeto de la espera, los cambios no previstos y la exposición al fallo. Declarar «completado» no basta. En escenarios bloqueados, debe existir evidencia de la denegación.

```bash
python -m agentreplay list
python -m agentreplay run --agent cautious
python -m agentreplay replay examples/duplicate-timeout.json
python -m unittest discover -s tests -v
```

El ejemplo de replay debe fallar con código 1: reproduce el duplicado deliberadamente.

## Tu propio agente

Puedes implementar una función Python `run(call, task)` o conectar un cliente local compatible con MCP al servidor:

```bash
python -m agentreplay serve --scenario timeout-after-write --output artifacts/mcp
```

El agente consulta `get_task`, utiliza las herramientas simuladas y termina con `finish`. Consulta [la guía de conexión](docs/AGENTS.md). El protocolo implementado es MCP stdio `2025-06-18`, con un conjunto mínimo de herramientas. Se ha probado mediante un cliente de pruebas por subproceso; falta comprobar clientes y modelos externos.

## Estado del proyecto

Código ejecutable, informes HTML/JSON, pruebas automatizadas y configuración de GitHub Actions preparados. Todavía no publicado en PyPI. La compatibilidad con varias versiones de Python se comprobará en GitHub Actions; la verificación local se ha realizado con Python 3.12.

Este laboratorio no certifica la seguridad de un agente ni implementa toda la API de GitHub. Usa un cliente dedicado con estas herramientas simuladas y datos ficticios. Los adaptadores Python ejecutan código local de confianza y deben limitar sus propias llamadas al modelo. Los informes incluyen el contenido completo de las llamadas.

Siguientes pasos: validar un agente real, añadir adaptadores de modelos y límites de ejecución, permitir escenarios declarativos y ampliar las integraciones simuladas.

Licencia MIT. [Documentación completa en inglés](README.md).
