/**
 * @openapi
 * components:
 *   schemas:
 *     User:
 *       type: object
 *       properties:
 *         id: { type: string, example: "1" }
 *         name: { type: string, example: "Ana Souza" }
 *         email: { type: string, example: "ana@email.com" }
 *     UserInput:
 *       type: object
 *       required: [name, email]
 *       properties:
 *         name: { type: string, example: "Daniel Rocha" }
 *         email: { type: string, example: "daniel@email.com" }
 *   parameters:
 *     UserId:
 *       in: path
 *       name: id
 *       required: true
 *       schema: { type: string }
 */

/**
 * @openapi
 * /users:
 *   get:
 *     tags: [Users]
 *     summary: Lista todos os usuários
 *     responses:
 *       200:
 *         description: Lista de usuários
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items: { $ref: "#/components/schemas/User" }
 *   post:
 *     tags: [Users]
 *     summary: Cria um usuário
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema: { $ref: "#/components/schemas/UserInput" }
 *     responses:
 *       201: { description: Usuário criado }
 *       400: { description: Dados inválidos }
 *       409: { description: E-mail já cadastrado }
 */

/**
 * @openapi
 * /users/{id}:
 *   get:
 *     tags: [Users]
 *     summary: Busca um usuário pelo ID
 *     parameters: [{ $ref: "#/components/parameters/UserId" }]
 *     responses:
 *       200:
 *         description: Usuário encontrado
 *         content:
 *           application/json:
 *             schema: { $ref: "#/components/schemas/User" }
 *       404: { description: Usuário não encontrado }
 *   put:
 *     tags: [Users]
 *     summary: Atualiza um usuário
 *     parameters: [{ $ref: "#/components/parameters/UserId" }]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema: { $ref: "#/components/schemas/UserInput" }
 *     responses:
 *       200: { description: Usuário atualizado }
 *       404: { description: Usuário não encontrado }
 *   delete:
 *     tags: [Users]
 *     summary: Remove um usuário
 *     parameters: [{ $ref: "#/components/parameters/UserId" }]
 *     responses:
 *       204: { description: Usuário removido }
 *       404: { description: Usuário não encontrado }
 */
export {};
