import { routes } from "./routes";

const server = Bun.serve({
  port: 3000,
  routes,
  fetch: () => Response.json({ error: "Rota não encontrada" }, { status: 404 }),
});

console.log(`API rodando em ${server.url}`);
console.log(`Documentação em ${server.url}docs`);
