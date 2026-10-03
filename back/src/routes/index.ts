import { UserController } from "../controller/userController";
import { swaggerSpec, swaggerHtml } from "../config/swagger";

export const routes = {
  "/users": {
    GET: UserController.index,
    POST: UserController.store,
  },
  "/users/:id": {
    GET: UserController.show,
    PUT: UserController.update,
    DELETE: UserController.destroy,
  },

  "/docs": new Response(swaggerHtml, {
    headers: { "Content-Type": "text/html" },
  }),
  "/docs/openapi.json": Response.json(swaggerSpec),
};
