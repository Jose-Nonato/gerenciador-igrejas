import swaggerJSDoc from "swagger-jsdoc";

export const swaggerSpec = swaggerJSDoc({
  definition: {
    openapi: "3.0.0",
    info: {
      title: "Gerenciador de Igrejas",
      version: "1.0.0",
      description: "Teste de criação de API utilizando bun.",
    },
    servers: [{ url: "http://localhost:3000" }],
  },
  apis: ["./src/docs/*.ts"],
});

export const swaggerHtml = `<!DOCTYPE html>
<html>
<head>
  <title>Minha API - Docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>SwaggerUIBundle({ url: "/docs/openapi.json", dom_id: "#swagger-ui" });</script>
</body>
</html>`;
