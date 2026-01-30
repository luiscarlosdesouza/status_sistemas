# Monitor de Sites IME-USP

Sistema simples para monitoramento de sites e serviços web, com dashboard de status e notificações por e-mail.

## Funcionalidades

- Dashboard público com status (Online/Offline) e tempo de resposta.
- Verificação automática a cada 5 minutos.
- Notificação por e-mail quando um site sai do ar.
- Interface administrativa para adicionar/remover sites.
- Login seguro para área administrativa.
- Deploy simplificado com Docker.

## Como Rodar

### Pré-requisitos

- Docker e Docker Compose instalados.

### Passo a Passo

1.  **Configuração de E-mail (Opcional)**
    - Para receber alertas por e-mail, edite o arquivo `docker-compose.yml`.
    - `EMAIL_USER`: Seu e-mail do Gmail.
    - `EMAIL_PASSWORD`: Senha de App do Google (Não é sua senha normal).
    - `EMAIL_TO`: O e-mail que receberá os alertas. Para múltiplos e-mails, separe por vírgula (ex: `email1@usp.br, email2@usp.br`).

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
    python app.py
    ```

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
