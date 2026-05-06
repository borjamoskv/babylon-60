---
title: "MCP dejó de ser Enchufar y Rezar"
date: 2026-05-06
author: CORTEX Research Lab
tags: [mcp, seguridad, agentes-ia, api, actualidad]
description: "El Model Context Protocol ya no puede tratarse como una comodidad de integración: autorización, scope, transporte y tool boundaries son parte del diseño."
slug: mcp-dejo-de-ser-enchufar-y-rezar
---

# MCP dejó de ser Enchufar y Rezar

MCP empezó como una idea muy atractiva: conectar modelos con herramientas,
repositorios, bases de datos y APIs de una forma estándar. La promesa sigue siendo
buena. El problema es que, en 2026, ya no se puede tratar como una manguera
inocente de contexto.

Un servidor MCP no es un plugin decorativo. Es una frontera de autoridad.

## La integración ahora es seguridad

Cuando un agente descubre herramientas, también descubre posibilidades de abuso:

- leer más contexto del necesario;
- ejecutar operaciones fuera de intención;
- mezclar scopes;
- reutilizar tokens;
- confiar en descripciones de herramientas maliciosas;
- convertir texto no confiable en acción.

Por eso el diseño actual de MCP tiene que hablar de OAuth, transporte seguro,
validación de redirect URIs y separación entre cliente, servidor MCP y recursos
protegidos.

## El error de producto

El error clásico es vender MCP como "conecta tus herramientas en cinco minutos".
Sí, puedes. Pero lo difícil no es que conecte. Lo difícil es que conecte con
límites.

Antes de añadir un servidor MCP, pregunta:

1. ¿qué usuario autoriza esta acción?
2. ¿qué recurso exacto puede tocar?
3. ¿qué scopes se conceden?
4. ¿qué logs se emiten?
5. ¿qué pasa si el agente interpreta mal la intención?
6. ¿cómo se revoca?

Si no puedes responder, no tienes integración. Tienes exposición.

## MCP para CORTEX

En una arquitectura de memoria persistente, MCP debería entrar como superficie
no confiable hasta demostrar lo contrario. Las respuestas de herramientas pueden
informar al agente, pero no deberían convertirse automáticamente en hechos
persistidos.

La ruta sana:

```text
MCP tool result -> validation -> redaction -> confidence -> scoped persistence
```

## La tesis

MCP es útil precisamente porque abre puertas. Pero cada puerta necesita cerradura,
registro y razón de apertura.

El futuro no es "más herramientas".

Es herramientas con identidad, intención y límites.

## Fuentes consultadas

- [MCP Authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)
- [OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/)
