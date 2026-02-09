# Monitor de Sites IME-USP (Versão 2.0)

Sistema simples para monitoramento de sites e serviços web, com dashboard de status e notificações por e-mail.

**Novidade da Versão 2.0**: Arquitetura modular profissional (Blueprints + Application Factory), facilitando a manutenção e escalabilidade.

## Funcionalidades
<... keeping existing features ...>

## Estrutura do Projeto (v2.0)

O sistema agora segue uma arquitetura modular:

- `run.py`: Ponto de entrada da aplicação via `Flask Application Factory`.
- `config.py`: Configurações de ambiente.
- `app/`: Pacote principal.
    - `__init__.py`: Inicialização e registro de extensões.
    - `models.py`: Modelos do Banco de Dados.
    - `extensions.py`: Instâncias do SQLAlchemy, Migrate, OAuth, etc.
    - `blueprints/`: Rotas organizadas por contexto (`auth`, `admin`, `main`).
    - `services/`: Regras de negócio (`monitor_service`, `email_service`).
    - `templates/`: Arquivos HTML.
- `migrations/`: Histórico de alterações do banco de dados.

## Guia de Configuração (Interface Gráfica)

- Dashboard público com status (Online/Atenção/Offline).
- Sistema de "Farol" para evitar falsos positivos (intermitência).
- Verificação de "Texto Esperado" para garantir que o site carregou corretamente.
- **[NOVO] Agendamento Dinâmico**: Intervalos diferentes para dias de semana (ex: 60 min) e fim de semana (ex: 120 min).
- **[NOVO] Notificação de Recuperação**: Avisa por e-mail quando o site volta ao ar.
- **[NOVO] Relatórios**: Histórico detalhado de falhas (início, fim e duração).
- **[NOVO] Configurações Globais**: Painel administrativo para alterar e-mails e intervalos sem mexer em código.
- **[NOVO V1.1] Gestão de Usuários**:
    - Níveis de acesso: **Admin** (Gerencia tudo) e **Operador** (Apenas visualiza e gerencia sites).
    - Cadastro de múltiplos usuários com Nome e E-mail.
- **[NOVO V1.1] Login com Google**: Suporte a OAuth 2.0 para login seguro.
- **[NOVO V2.0] Login Senha Única USP**: Integração com OAuth 1.0a para autenticação institucional.
- **[NOVO V1.1] Perfil de Usuário**: Alteração de senha obrigatória no primeiro acesso e edição de dados próprios.
- Interface administrativa para adicionar/editar/remover sites.
- Deploy simplificado com Docker.

## Lógica de Monitoramento (Sistema de Farol)

Para evitar que qualquer oscilação na rede envie e-mails desnecessários, o sistema utiliza uma lógica de 3 estágios:

1.  **🟢 Online (Verde)**:
    - O site respondeu com status 200 (OK) E (opcionalmente) contém o texto esperado.

2.  **🟠 Atenção (Laranja)**:
    - O site falhou na verificação.
    - O sistema registra o horário da primeira falha.
    - **Nenhum e-mail é enviado ainda.** O sistema aguarda para ver se é apenas uma instabilidade passageira.

3.  **🔴 Offline (Vermelho)**:
    - O site continua falhando consecutivamente.
    - Se o tempo desde a primeira falha for maior que **15 minutos**, o status muda para Offline.
    - **E-mail de Alerta é enviado** para **todos os usuários configurados para receber notificações**.

4.  **🟢 Recuperação (Volta ao Verde)**:
    - Se o site estava Offline e volta a responder com sucesso.
    - **E-mail de Recuperação é enviado** avisando que o serviço normalizou.

*Resumo: O sistema verifica a cada 1 hora. Se falhar, você será avisado na próxima checagem (se continuar falhando).*

## Verificação de "Texto Esperado"

Muitas vezes, quando um sistema cai, o servidor web (Nginx/Apache) continua no ar entregando uma página de erro genérica ("502 Bad Gateway" ou "Service Unavailable"). Para um monitoramento simples, isso parece "Online" (o servidor respondeu).

O campo **Texto Esperado** resolve isso.

- **Como funciona**: O sistema busca por uma palavra ou frase específica dentro da página do site.
- **O que escrever**: Escolha algo único que sempre aparece quando o site está funcionando.
    - Exemplo (Sistema de Login): `Senha` ou `Esqueci minha senha`.
    - Exemplo (Portal): `Bem-vindo ao Sistema`.
    - Exemplo (API): `{"status": "ok"}`.
- **Configuração**: Ao adicionar ou editar um site no Admin, preencha este campo. Se deixar em branco, o sistema validará apenas o código HTTP 200.

## Como Rodar

### Pré-requisitos

- Docker e Docker Compose instalados.
- (Opcional) Conta Google Cloud para ativar o Login com Google.

### Passo a Passo

1.  **Configuração de E-mail e Google (Opcional)**
    - Copie o arquivo `.env-example` para `.env`:
    - `EMAIL_USER`: Seu e-mail do Gmail.
    - `EMAIL_PASSWORD`: Senha de App do Google.
    - `EMAIL_PASSWORD`: Senha de App do Google.
    - `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`: Credenciais OAuth 2.0 (Para login com Google).
    - `USP_CLIENT_KEY` e `USP_CLIENT_SECRET`: Credenciais OAuth 1.0a (Para Senha Única).
    - `USP_CALLBACK_ID`: ID do callback (Geralmente 63 para produção / 64 para localhost).
    
    *Nota: A lista de e-mails para notificação agora é gerenciada dentro do sistema, no cadastro de Usuários.*


2.  **Subir o Sistema**
    Execute o comando na raiz do projeto:
    ```bash
    docker-compose up -d --build
    ```

3.  **Acessar**
    - **Dashboard**: [http://localhost:5000](http://localhost:5000)
    - **Admin**: [http://localhost:5000/login](http://localhost:5000/login)
    - **Login Padrão**:
        - Usuário: `admin`
        - Senha: `admin`

## Desenvolvimento Local (Sem Docker)

1.  Crie um ambiente virtual:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
3.  Defina as variáveis de ambiente (Crie um arquivo `.env`):
    ```env
    SECRET_KEY=dev-key
    EMAIL_USER=...
    ```
4.  Rode a aplicação:
    ```bash
    python run.py
    ```

## 🏢 Trabalhando de Outro Computador (Home Office)

Para continuar o trabalho em casa (ex: fim de semana):

1.  **Clone o Repositório**:
    ```bash
    git clone https://github.com/luiscarlosdesouza/status_sistemas.git
    cd status_sistemas
    ```

2.  **Configurar Credenciais (.env)**:
    ⚠️ **Importante**: O arquivo `.env` contendo senhas não vai para o GitHub por segurança.
    - Você precisará criar um arquivo `.env` na pasta do projeto.
    - Opção A: Copie o conteúdo do `.env` do servidor de produção e leve num arquivo de texto seguro (ou USB).
    - Opção B: Crie um novo usando o `.env-example` e preencha as chaves (USP/Google/Email).

3.  **Rodar com Docker (Recomendado)**:
    ```bash
    docker-compose up -d --build
    ```
    O sistema estará disponível em [http://localhost:5000](http://localhost:5000).

4.  **Banco de Dados**:
    - Ao rodar em um novo computador, o banco começará **vazio** (apenas com o usuário admin padrão), pois o banco do servidor não é sincronizado pelo Git.
    - Se precisar dos dados reais, você terá que copiar manualmente o arquivo `instance/sites.db` do servidor para o seu computador.

## Deploy em Servidor de Produção

Se você quer levar **este sistema exato** (com o banco de dados já preenchido e suas configurações) para outro servidor:

1.  **Compactar o Projeto**:
    No terminal, dentro da pasta `/sistemas`, execute:
    ```bash
    tar -czvf monitora_sites.tar.gz monitora_sites/
    ```

2.  **Enviar para o Servidor**:
    Use o comando `scp` para copiar o arquivo:
    ```bash
    scp monitora_sites.tar.gz usuario@seu-servidor.com:/caminho/destino/
    ```

3.  **No Servidor de Produção**:
    Acesse o servidor e descompacte:
    ```bash
    tar -xzvf monitora_sites.tar.gz
    cd monitora_sites
    ```

4.  **Iniciar**:
    Como o arquivo `.env` e o banco de dados `instance/sites.db` foram junto no pacote, basta rodar:
    ```bash
    sudo docker compose up -d --build
    ```

## Estrutura do Projeto

- `app.py`: Lógica principal (Flask, Banco de Dados, Scheduler).
- `templates/`: Arquivos HTML (Bootstrap).
- `sites.db`: Banco de dados SQLite (gerado automaticamente).

## Guia de Configuração (Interface Gráfica)

**Não é mais necessário editar código para mudar configurações!**

Acesse o painel administrativo (`/admin`) e clique no botão **Configurações**. Lá você pode alterar:

1.  **E-mail e SMTP**:
    - Alterar remetente, senha de app, servidores SMTP e lista de destinatários.
2.  **Frequência de Monitoramento**:
    - **Dia de Semana**: Intervalo em minutos para checagem de Seg-Sex (Padrão: 60 min).
    - **Fim de Semana**: Intervalo em minutos para checagem de Sáb-Dom (Padrão: 120 min).
    - **Tempo para Alerta**: Quantos minutos de falha contínua antes de considerar Offline (Padrão: 15 min).

---

## Guia do Desenvolvedor (Técnico)

### Variáveis de Ambiente (.env)
O sistema lê as configurações iniciais do arquivo `.env` apenas na primeira execução para preencher o banco de dados. Depois disso, as configurações valem o que estiver no banco (editável pela interface).

Arquivo `.env` (Use o `.env-example` como base):
```env
SECRET_KEY=sua-chave-secreta
ADMIN_PASSWORD=senha-admin
EMAIL_USER=seu-email@gmail.com
EMAIL_PASSWORD=sua-senha-app
EMAIL_TO=destino1@usp.br,destino2@usp.br
```

## GitHub

Para subir no GitHub:
1.  Crie um repositório vazio no GitHub.
2.  Execute:
    ```bash
    git init
    git add .
    git commit -m "Primeiro commit - Monitor de Sites"
    git branch -M main
    git remote add origin <SEU_REPO_URL>
    git push -u origin main
    ```

## Como Atualizar (Fluxo de Trabalho)

Se você fez alterações no código e quer atualizar seu servidor de produção:

1.  **No seu computador (Desenvolvimento)**:
    ```bash
    git add .
    git commit -m "Descrição da atualização"
    git push
    ```

2.  **No Servidor de Produção**:
    Entre na pasta do projeto e rode:
    ```bash
    # Baixar as novidades do GitHub
    git pull
    
    # Recriar o container com o novo código
    sudo docker-compose up -d --build
    ```
    *Nota: Isso atualiza o código, mas mantém seu banco de dados e configurações intactos.*

## Atualizações de Banco de Dados (Migrações)

Se a atualização envolver mudanças na estrutura do banco (ex: novos campos), siga este fluxo:

1.  **No Desenvolvimento (Local)**:
    ```bash
    # Se você alterou o models.py, gere a migração:
    sudo docker-compose exec web flask db migrate -m "Descreva a mudança"
    
    # Commit o arquivo criado na pasta migrations/
    git add migrations/
    git commit -m "DB Migration"
    git push
    ```

2.  **No Servidor de Produção**:
    ```bash
    git pull
    sudo docker-compose up -d --build
    
    sudo docker-compose exec web flask db upgrade
    ```

## Histórico de Versões

### Versão 2.0 (Atual)
- **Refatoração Completa**: Migração de `app.py` monolítico para arquitetura de **Blueprints**.
- **Senha Única USP**: Implementação de login OAuth 1.0a com suporte a configuração dinâmica de callback.
- **Services Pattern**: Lógica de monitoramento desacoplada das rotas.
- **Factory Pattern**: Uso de `create_app` para melhor gerenciamento de contexto e testes.

### Versão 1.1
- **Gestão de Usuários**: Perfis Admin/Operador e edição de perfil.
- **Login Google**: Integração OAuth 2.0.
- **Migrações**: Implementação do Flask-Migrate.

### Versão 1.0
- Lógica de Farol, Dashboard, Notificações por E-mail e Relatórios Básicos.
