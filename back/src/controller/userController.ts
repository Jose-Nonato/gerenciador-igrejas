import { UserModel } from "../models/usersModel";

type ReqWithId = Request & { params: { id: string } };

export const UserController = {
  async index() {
    return Response.json(await UserModel.findAll());
  },

  async show(req: ReqWithId) {
    const user = await UserModel.findById(req.params.id);
    if (!user)
      return Response.json(
        { error: "Usuário não encontrado" },
        { status: 404 },
      );
    return Response.json(user);
  },

  async store(req: Request) {
    const { name, email } = await req.json();
    if (!name || !email) {
      return Response.json(
        { error: "name e email são obrigatórios" },
        { status: 400 },
      );
    }
    if (await UserModel.findByEmail(email)) {
      return Response.json({ error: "E-mail já cadastrado" }, { status: 409 });
    }
    return Response.json(await UserModel.create({ name, email }), {
      status: 201,
    });
  },

  async update(req: ReqWithId) {
    const { name, email } = await req.json();
    const user = await UserModel.update(req.params.id, { name, email });
    if (!user)
      return Response.json(
        { error: "Usuário não encontrado" },
        { status: 404 },
      );
    return Response.json(user);
  },

  async destroy(req: ReqWithId) {
    const deleted = await UserModel.remove(req.params.id);
    if (!deleted)
      return Response.json(
        { error: "Usuário não encontrado" },
        { status: 404 },
      );
    return new Response(null, { status: 204 });
  },
};
