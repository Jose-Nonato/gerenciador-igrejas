import { users, type Users } from "../data/users.data";

export const UserModel = {
  async findAll() {
    return users;
  },

  async findById(id: string) {
    return users.find((u) => u.id === id) ?? null;
  },

  async findByEmail(email: string) {
    return users.find((u) => u.email === email) ?? null;
  },

  async create(data: Omit<Users, "id">) {
    const user = { id: crypto.randomUUID(), ...data };
    users.push(user);
    return user;
  },

  async update(id: string, data: Partial<Omit<Users, "id">>) {
    const user = users.find((u) => u.id === id);
    if (!user) return null;
    Object.assign(user, data);
    return user;
  },

  async remove(id: string) {
    const index = users.findIndex((u) => u.id === id);
    if (index === -1) return false;
    users.splice(index, 1);
    return true;
  },
};
