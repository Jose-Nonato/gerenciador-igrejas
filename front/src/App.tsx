import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import { Layout } from './components/Layout'
import { AgendaPage } from './pages/AgendaPage'
import { ComunicadoFormPage } from './pages/ComunicadoFormPage'
import { ComunicadosPage } from './pages/ComunicadosPage'
import { EditarMembroPage } from './pages/EditarMembroPage'
import { FichaMembroPage } from './pages/FichaMembroPage'
import { EsqueciSenhaPage } from './pages/EsqueciSenhaPage'
import { GerenciarComunicadosPage } from './pages/GerenciarComunicadosPage'
import { InicioPage } from './pages/InicioPage'
import { LoginPage } from './pages/LoginPage'
import { MembrosPage } from './pages/MembrosPage'
import { NovoMembroPage } from './pages/NovoMembroPage'
import { RedefinirSenhaPage } from './pages/RedefinirSenhaPage'
import { ReuniaoPage } from './pages/ReuniaoPage'
import { SociedadePage } from './pages/SociedadePage'
import { EbdAulaPage } from './pages/EbdAulaPage'
import { EbdClassePage } from './pages/EbdClassePage'
import { EbdPage } from './pages/EbdPage'
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
              {/* Mural: todo usuário lê o que foi publicado para o seu público. Quem escreve é
                  decidido pelo backend (admin, pastor e liderança da própria sociedade). */}
              <Route path="comunicados" element={<ComunicadosPage />} />
              <Route path="comunicados/gerenciar" element={<GerenciarComunicadosPage />} />
              <Route path="comunicados/novo" element={<ComunicadoFormPage />} />
              <Route path="comunicados/:id/editar" element={<ComunicadoFormPage />} />
              {/* Agenda de conversas: membro com conta pede horário; pastor e presbíteros respondem. */}
              <Route path="agenda" element={<AgendaPage />} />
              <Route path="trocar-senha" element={<TrocarSenhaPage />} />
              <Route element={<RequireAuth perfis={['admin', 'pastor', 'presbitero']} />}>
                <Route path="membros" element={<MembrosPage />} />
                <Route path="membros/novo" element={<NovoMembroPage />} />
                <Route path="membros/:id" element={<FichaMembroPage />} />
                <Route path="membros/:id/editar" element={<EditarMembroPage />} />
                <Route path="usuarios" element={<UsuariosPage />} />
              </Route>
              {/* Sociedades: admin e pastor veem todas; quem está na diretoria vê só a sua.
                  O backend decide por sociedade; a lista já vem filtrada. */}
              {/* EBD: admin e pastor veem todas as classes; o professor vê só a sua. */}
              <Route path="ebd" element={<EbdPage />} />
              <Route path="ebd/:id" element={<EbdClassePage />} />
              <Route path="ebd/:id/aulas/nova" element={<EbdAulaPage />} />
              <Route path="ebd/:id/aulas/:aulaId" element={<EbdAulaPage />} />
              <Route path="sociedades" element={<SociedadesPage />} />
              <Route path="sociedades/:id" element={<SociedadePage />} />
              <Route path="sociedades/:id/reunioes/nova" element={<ReuniaoPage />} />
              <Route path="sociedades/:id/reunioes/:reuniaoId" element={<ReuniaoPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
