# Como hospedar este site

O projeto usa **Flask + PostgreSQL + SocketIO** (chat em tempo real). Abaixo estão opções de hospedagem que suportam essa stack.

> **Hospedando na Hostinger?** Use o guia completo em **[HOSTINGER.md](HOSTINGER.md)** (passo a passo para VPS).

---

## Variáveis de ambiente necessárias

Configure estas variáveis no painel da plataforma (ou no `.env` em desenvolvimento):

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `DATABASE_URL` | Sim | URL do PostgreSQL, ex: `postgresql://user:senha@host:5432/nome_do_banco` |
| `SECRET_KEY` | Sim | Chave secreta para sessões (gere uma string aleatória longa) |
| `ADMIN_PASSWORD` | Sim | Senha do painel admin |
| `ADMIN_EMAIL` | Não | E-mail que recebe aviso quando alguém manda mensagem no chat |
| `SMTP_*` ou `RESEND_API_KEY` | Não | Para envio de e-mails (notificações) |

**Dica:** Para gerar uma `SECRET_KEY`: no terminal, `python -c "import secrets; print(secrets.token_hex(32))"`.

---

## Opção 1: Railway (recomendado — mais simples)

[Railway](https://railway.app) oferece PostgreSQL e app Python no mesmo lugar, com suporte a WebSockets (SocketIO).

### Passos

1. **Crie uma conta** em [railway.app](https://railway.app) (pode usar GitHub).

2. **Novo projeto** → **Deploy from GitHub repo** e selecione o repositório deste projeto.

3. **Adicione o PostgreSQL:** no projeto, clique em **+ New** → **Database** → **PostgreSQL**. Railway cria o banco e expõe a variável `DATABASE_URL` automaticamente.

4. **Vincule o banco ao app:** no serviço da sua aplicação, abra **Variables** → **Add variable** → **Add reference** e escolha `DATABASE_URL` do PostgreSQL.

5. **Defina as outras variáveis** no mesmo lugar:
   - `SECRET_KEY` = (valor gerado acima)
   - `ADMIN_PASSWORD` = sua senha do admin

6. **Configuração do serviço (Build & Deploy):**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -k eventlet -w 1 -b 0.0.0.0:$PORT app:app`
   - **Root Directory:** (deixe em branco se o código está na raiz do repo)

7. **Deploy:** após o primeiro deploy, Railway gera uma URL (ex: `seu-app.up.railway.app`). Você pode configurar um domínio próprio nas configurações.

**Custo:** há um trial com créditos; depois, plano pago (uso moderado costuma ficar em poucos dólares/mês).

---

## Opção 2: Render

[Render](https://render.com) tem plano gratuito (o app “dorme” após 15 min sem acesso) e PostgreSQL pago ou gratuito (com limitações).

### Passos

1. **Conta** em [render.com](https://render.com) (GitHub).

2. **Novo Web Service:** conecte o repositório do projeto.

3. **Configuração:**
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -k eventlet -w 1 -b 0.0.0.0:$PORT app:app`

4. **PostgreSQL:** no dashboard, **New** → **PostgreSQL**. Copie a **Internal Database URL** e crie no Web Service a variável `DATABASE_URL` com esse valor.

5. **Variáveis de ambiente:** no Web Service, **Environment** e adicione:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `ADMIN_PASSWORD`

6. **Deploy:** Render faz o build e publica. A URL será algo como `seu-app.onrender.com`.

**Observação:** no plano gratuito, o serviço “acorda” no primeiro acesso após ficar inativo; o primeiro carregamento pode demorar alguns segundos.

---

## Opção 3: VPS (DigitalOcean, Contabo, etc.)

Você tem controle total: instala Python, PostgreSQL e Nginx e sobe o app com gunicorn + eventlet.

### Resumo dos passos (Linux)

1. **Servidor:** crie um VPS (Ubuntu 22.04 é comum).

2. **Instale dependências:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx postgresql postgresql-client
   ```

3. **PostgreSQL:** crie usuário e banco, anote a `DATABASE_URL`.

4. **Clone o projeto** (ou envie os arquivos) para ex: `/var/www/portifolio`.

5. **Ambiente virtual e dependências:**
   ```bash
   cd /var/www/portifolio
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt gunicorn eventlet
   ```

6. **Variáveis de ambiente:** crie um arquivo `.env` no mesmo diretório (ou use systemd/service para definir env).

7. **Teste local:**
   ```bash
   gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 app:app
   ```

8. **Nginx:** configure um proxy reverso para o seu domínio apontando para `http://127.0.0.1:5000` e ative WebSockets (proxy para SocketIO).

9. **Systemd:** crie um serviço para rodar o gunicorn e subir com o servidor.

Se quiser, posso detalhar um exemplo de configuração do Nginx e do serviço systemd em outro arquivo.

---

## Arquivos do projeto usados no deploy

- **`requirements.txt`** — dependências Python (inclua `gunicorn` e `eventlet` em produção).
- **`Procfile`** (opcional) — usado por algumas plataformas; exemplo:  
  `web: gunicorn -k eventlet -w 1 -b 0.0.0.0:$PORT app:app`

A aplicação lê a porta pela variável **`PORT`** (Railway e Render definem automaticamente).

---

## Checklist antes de subir

- [ ] `SECRET_KEY` forte e única em produção
- [ ] `ADMIN_PASSWORD` segura
- [ ] `DATABASE_URL` apontando para o PostgreSQL de produção
- [ ] Não commitar o `.env` (ele deve estar no `.gitignore`)
- [ ] Testar o formulário de contato e o chat após o deploy

Se quiser, posso sugerir um `Procfile` e as linhas exatas para adicionar ao `requirements.txt` (gunicorn e eventlet) no seu repositório.
