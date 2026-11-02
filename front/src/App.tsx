import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import { Layout } from './components/Layout'
import { EditarMembroPage } from './pages/EditarMembroPage'
import { FichaMembroPage } from './pages/FichaMembroPage'
import { EsqueciSenhaPage } from './pages/EsqueciSenhaPage'
import { InicioPage } from './pages/InicioPage'
import { LoginPage } from './pages/LoginPage'
import { MembrosPage } from './pages/MembrosPage'
import { NovoMembroPage } from './pages/NovoMembroPage'
import { RedefinirSenhaPage } from './pages/RedefinirSenhaPage'
import { ReuniaoPage } from './pages/ReuniaoPage'
import { SociedadePage } from './pages/SociedadePage'
import { SociedadesPage } from './pages/SociedadesPage'
import { TrocarSenhaPage } from './pages/TrocarSenhaPage'
import { UsuariosPage } from './pages/UsuariosPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/esqueci-senha" element={<EsqueciSenhaPage />} />
          <Route path="/redefinir-senha" element={<RedefinirSenhaPage />} />

          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route index element={<InicioPage />} />
              <Route path="trocar-senha" element={<TrocarSenhaPage />} />
              <Route element={<RequireAuth perfis={['admin', 'pastor', 'presbitero']} />}>
                <Route path="membros" element={<MembrosPage />} />
                <Route path="membros/novo" element={<NovoMembroPage />} />
                <Route path="membros/:id" element={<FichaMembroPage />} />
                <Route path="membros/:id/editar" element={<EditarMembroPage />} />
                <Route path="usuarios" element={<UsuariosPage />} />
              </Route>
              {/* Sociedades internas: só admin e pastor (o backend também exige) */}
              <Route element={<RequireAuth perfis={['admin', 'pastor']} />}>
                <Route path="sociedades" element={<SociedadesPage />} />
                <Route path="sociedades/:id" element={<SociedadePage />} />
                <Route path="sociedades/:id/reunioes/nova" element={<ReuniaoPage />} />
                <Route path="sociedades/:id/reunioes/:reuniaoId" element={<ReuniaoPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
