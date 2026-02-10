# Monitor de Sites (USP) - Versão 2.1

Sistema robusto para monitoramento de disponibilidade de sites (Uptime Monitor) desenvolvido com Python/Flask, com foco em autenticação institucional (USP) e gestão flexível de notificações.

## 🔥 O que há de novo na v2.1?
- **Autenticação Avançada**:
  - Login via **Senha Única USP** (OAuth 1.0a) com auto-cadastro resiliente.
  - Login via **Google OAuth**.
- **Gestão de Acesso (RBAC)**:
  - Três perfis: **Admin** (total), **Operador** (gerencia sites), **Usuário** (visualização).
  - Controle granular de acesso aos relatórios e dashboard.
- **Notificações Inteligentes**:
  - Alerta por e-mail para **Novos Usuários** (Admin aprova).
  - E-mail de **Boas-vindas** e **Mudança de Papel** para usuários.
  - Alertas de **Queda/Recuperação** de sites totalmente em Português (PT-BR).
  - Configuração automática de remetente ("Monitor de Sites").
- **Melhorias de Interface**:
  - Ordenação alfabética automática dos sites.
  - Dashboard público (Status) separado do Painel Administrativo.
  - Exibição clara do nível de acesso do usuário.
- **Novas Ferramentas**:
  - **Exportação de PDF**: Relatórios de falhas em formato A4.
  - **Histórico Persistente**: Dados de falhas são mantidos mesmo após exclusão do site.
  - **Atualização Manual**: Botão para forçar verificação imediata de status.

## Funcionalidades Principais
- **Monitoramento contínuo**: Verifica URLs periodicamente (configurável para dias úteis/fim de semana).
- **Sistema de "Farol"**: Lógica de 3 estágios (Online/Atenção/Offline) para evitar falsos positivos por instabilidade momentânea.
- **Validação de Conteúdo**: Opcionalmente verifica se um texto específico existe na página (ex: "Bem-vindo") para garantir que o site carregou corretamente.
- **Relatórios**: Histórico detalhado de falhas (início, fim e duração).
- **Configurações Globais**: Painel administrativo para alterar e-mails, intervalos e timeouts sem mexer em código.

---

## 🚀 Guia de Instalação e Uso

### Pré-requisitos
- Docker e Docker Compose instalados.
- Credenciais OAuth (USP e/ou Google) e servidor SMTP (ex: IME-USP ou Gmail).

### 1. Configuração Inicial (.env)
Copie o arquivo `.env-example` para `.env` e preencha as variáveis:
```env
# Segurança
SECRET_KEY=sua-chave-secreta-aleatoria
ADMIN_PASSWORD=senha-inicial-admin

# E-mail (Exemplo IME-USP)
EMAIL_USER=usuario (sem @ime.usp.br)
EMAIL_PASSWORD=sua-senha
EMAIL_SMTP_SERVER=smtp.ime.usp.br
EMAIL_SMTP_PORT=587

# OAuth Google (Opcional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# OAuth USP (Opcional - Senha Única)
USP_CLIENT_KEY=...
USP_CLIENT_SECRET=...
USP_CALLBACK_ID=64  # Geralmente 64 para localhost, 63 para produção
```

### 2. Executando com Docker (Recomendado)
Para garantir que todas as alterações (incluindo timeouts e templates) sejam aplicadas:
```bash
# 1. Construir e subir os containers
docker-compose up --build -d

# 2. Verificar os logs (para garantir que não há erros)
docker-compose logs -f web
```
Acesse:
- **Dashboard Público**: [http://localhost:5000](http://localhost:5000)
- **Login**: [http://localhost:5000/login](http://localhost:5000/login)

### 3. Recuperação de Desastre (Banco de Dados)
O banco de dados `sites.db` fica na pasta `instance/` e é persistido via volume do Docker.
Se este arquivo for deletado acidentalmente:
1. O sistema recriará o banco vazio ao reiniciar.
2. Para restaurar o usuário admin padrão e configurações iniciais, rode:
   ```bash
   docker-compose exec web python init_db.py
   ```

---

## 🛠️ Guia de Administração (Configurações)

**Não é necessário editar código para mudar configurações de monitoramento!**

Acesse o painel administrativo (`/admin`) -> **Configurações**:

1.  **E-mail e SMTP**:
    - O sistema detecta automaticamente o domínio `@ime.usp.br` se o servidor for `smtp.ime.usp.br`.
    - O remetente será formatado como `Monitor de Sites <usuario@ime.usp.br>`.
2.  **Frequência de Monitoramento**:
    - **Dia de Semana**: Intervalo em minutos para checagem de Seg-Sex (Padrão: 60 min).
    - **Fim de Semana**: Intervalo em minutos para checagem de Sáb-Dom (Padrão: 120 min).
3.  **Sensibilidade**:
    - **Tempo para Alerta**: Quantos minutos de falha contínua antes de considerar Offline (Padrão: 15 min).

---

## 🔄 Fluxo de Atualização (Deploy)

Para atualizar o sistema em produção com novas versões do GitHub:

1.  **Baixar as alterações**:
    ```bash
    git pull origin main
    ```

2.  **Aplicar Migrações de Banco (se houver)**:
    O sistema usa Flask-Migrate. Se houver mudanças na estrutura do banco:
    ```bash
    docker-compose exec web flask db upgrade
    ```

3.  **Reconstruir o Container**:
    Sempre que houver mudança em arquivos Python ou Templates:
    ```bash
    docker-compose up --build -d
    ```

---

## 📂 Estrutura do Projeto (V2.1)

O sistema segue uma arquitetura modular (Blueprints + Factory):

- `run.py`: Ponto de entrada (Application Factory).
- `config.py`: Configurações de ambiente.
- `app/`: Código fonte.
    - `__init__.py`: Inicialização e extensões.
    - `models.py`: Tabelas (User, Site, SiteHistory, GlobalSettings).
    - `blueprints/`: Rotas (`auth`, `admin`, `main`).
    - `services/`: Lógica de negócio (`email_service`, `monitor_service`).
    - `templates/`: Interface HTML (Bootstrap 5).
- `migrations/`: Histórico de versões do banco de dados.

---

## Histórico de Versões

### Versão 2.1 (Atual)
- **SMTP IME-USP**: Suporte nativo e formatação de remetente.
- **Auto-Registration**: Cadastro resiliente via OAuth.
- **Internacionalização**: Alertas em Português.
- **UI**: Ordenação alfabética e melhorias de navegação.

### Versão 2.0
- **Refatoração Completa**: Migração para Blueprints.
- **Senha Única USP**: Implementação de OAuth 1.0a.

### Versão 1.1
- **Login Google**: Integração OAuth 2.0.
- **Gestão de Usuários**: Perfis Admin/Operador.

### Versão 1.0
- Lógica de Farol, Dashboard e Notificações Básicas.
