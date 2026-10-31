# Frontend

React + TypeScript + Vite. Consome a API em `../back`.

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # checagem de tipos + build de produção
npm run lint
```

A URL da API vem de `VITE_API_URL` (padrão em `.env.development`; modelo em `.env.example`).
A porta 3000 é a `FRONTEND_URL` padrão do backend: links de e-mail e CORS dependem dela.

## Estrutura
- `src/api/`: cliente HTTP (renova o token sozinho ao receber 401), tipos e endpoints
- `src/auth/`: `AuthProvider`, `useAuth` e `RequireAuth` (rotas protegidas por login e perfil)
- `src/pages/`: login, recuperação e redefinição de senha, troca de senha, início e rol de membros
- `src/components/`: layout e campos de formulário
