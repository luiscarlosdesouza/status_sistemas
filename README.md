# Monitor de Sites IME-USP

Sistema simples para monitoramento de sites e serviços web, com dashboard de status e notificações por e-mail.

## Funcionalidades

- Dashboard público com status (Online/Atenção/Offline).
- Sistema de "Farol" para evitar falsos positivos (intermitência).
- Verificação de "Texto Esperado" para garantir que o site carregou corretamente.
- Verificação automática a cada 60 minutos (configurável).
- Notificação por e-mail apenas se o site ficar offline por mais de 15 minutos.
- Interface administrativa para adicionar/editar/remover sites.
- Login seguro para área administrativa.
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
    - **E-mail de Alerta é enviado** para a lista de contatos.

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

## Guia de Configuração (Desenvolvedores)

Se você precisa alterar os intervalos de tempo padrão, edite o arquivo `app.py`:

### 1. Alterar Intervalo de Checagem
Procure o final do arquivo `app.py`:
```python
# Start Scheduler
scheduler = BackgroundScheduler()
# Altere 'minutes=60' para o valor desejado (ex: minutes=5)
scheduler.add_job(func=check_sites, trigger="interval", minutes=60)
```

### 2. Alterar Tempo de Espera para Alerta (15 min)
Procure a função `check_sites` e o bloco de verificação de tempo:
```python
# Altere '900' (segundos) para o valor desejado (ex: 300 para 5 minutos)
if time_diff.total_seconds() >= 900: # 15 minutes
```
*Nota: Lembre-se de alterar este valor em dois lugares dentro da função `check_sites` (no bloco `else` e no bloco `except`).*

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
