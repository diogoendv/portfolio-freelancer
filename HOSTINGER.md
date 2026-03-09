# Hospedar o site na Hostinger (VPS)

Na Hostinger, aplicações **Flask** só podem ser hospedadas em um **VPS** (não em hospedagem compartilhada). Este guia mostra o passo a passo para subir seu portfólio (Flask + PostgreSQL + SocketIO) em um VPS Hostinger.

---

## O que você precisa

- Conta Hostinger com **plano VPS** (qualquer um que dê acesso root/SSH).
- Domínio apontando para o IP do VPS (ou use o IP fornecido pela Hostinger para testar).
- Acesso **SSH** ao servidor (a Hostinger informa usuário, IP e senha no painel do VPS).

---

## Passo 1: Conectar no VPS por SSH

No painel da Hostinger, abra o VPS e anote:
- **IP do servidor**
- **Usuário** (geralmente `root`)
- **Senha** (ou chave SSH, se configurou)

No seu computador (PowerShell ou terminal):

```bash
ssh root@SEU_IP_DO_VPS
```

Digite a senha quando pedido. Você estará dentro do servidor Linux.

---

## Passo 2: Atualizar o sistema e instalar dependências

Execute no servidor (Ubuntu/Debian):

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-client git
```

---

## Passo 3: Configurar o PostgreSQL

1. Entre no PostgreSQL como superusuário:

```bash
sudo -u postgres psql
```

2. Crie usuário e banco (troque `portfolio_user` e `SuaSenhaSegura123` pelos seus):

```sql
CREATE USER portfolio_user WITH PASSWORD 'SuaSenhaSegura123';
CREATE DATABASE portfolio_db OWNER portfolio_user;
\q
```

3. Anote a **URL de conexão** (você vai usar no `.env`):

```
postgresql://portfolio_user:SuaSenhaSegura123@localhost:5432/portfolio_db
```

---

## Passo 4: Colocar o projeto no servidor

**Opção A — Usando Git (recomendado)**

Se o projeto está no GitHub/GitLab:

```bash
cd /var/www
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git portfolio
cd portfolio
```

**Opção B — Enviando os arquivos**

Use FileZilla, WinSCP ou o Gerenciador de Arquivos da Hostinger para enviar a pasta do projeto para `/var/www/portfolio` (crie a pasta se precisar).

---

## Passo 5: Ambiente virtual e dependências

```bash
cd /var/www/portfolio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Se der erro em `psycopg2-binary`, instale antes: `apt install -y libpq-dev python3-dev` e rode o `pip install` de novo.

---

## Passo 6: Arquivo .env no servidor

Crie o arquivo de variáveis de ambiente (não use o mesmo `.env` do seu PC em produção):

```bash
nano .env
```

Coloque (ajuste os valores):

```env
DATABASE_URL="postgresql://portfolio_user:SuaSenhaSegura123@localhost:5432/portfolio_db"
SECRET_KEY="uma-chave-bem-longa-e-aleatoria-aqui"
ADMIN_PASSWORD="sua-senha-do-painel-admin"
```

Para gerar uma `SECRET_KEY` forte no seu PC:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado e use no `.env`. Salve com **Ctrl+O**, Enter, e saia com **Ctrl+X**.

---

## Passo 7: Testar a aplicação

Ainda com o ambiente ativado (`source venv/bin/activate`):

```bash
gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 app:app
```

Abra no navegador: `http://SEU_IP_DO_VPS:5000`. Se a página carregar, pare o servidor com **Ctrl+C**.

---

## Passo 8: Serviço systemd (subir o app sozinho ao reiniciar o VPS)

Crie o arquivo de serviço:

```bash
nano /etc/systemd/system/portfolio.service
```

Cole (ajuste o caminho se sua pasta for outra):

```ini
[Unit]
Description=Portfolio Flask App
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/var/www/portfolio
Environment="PATH=/var/www/portfolio/venv/bin"
ExecStart=/var/www/portfolio/venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Salve e saia. Depois:

```bash
systemctl daemon-reload
systemctl enable portfolio
systemctl start portfolio
systemctl status portfolio
```

Se aparecer **active (running)**, o app está rodando na porta 5000 **só dentro do servidor** (127.0.0.1). O Nginx vai encaminhar o tráfego para ela.

---

## Passo 9: Nginx (site público e WebSockets para o chat)

Crie o arquivo de configuração do site:

```bash
nano /etc/nginx/sites-available/portfolio
```

Cole (substitua **SEU_DOMINIO** pelo seu domínio ou use o IP do VPS):

```nginx
server {
    listen 80;
    server_name SEU_DOMINIO www.SEU_DOMINIO;
    # Se for só por IP: server_name SEU_IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Ative o site e recarregue o Nginx:

```bash
ln -sf /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

---

## Passo 10: HTTPS com certificado gratuito (Let's Encrypt)

Se você está usando **domínio** (ex: `meusite.com.br`):

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d SEU_DOMINIO -d www.SEU_DOMINIO
```

Siga as perguntas (e-mail, aceitar termos). O Certbot configura o HTTPS no Nginx. Para renovar automaticamente: `certbot renew` já vem em cron.

---

## Resumo rápido

| O quê | Onde / Comando |
|-------|-----------------|
| Código do site | `/var/www/portfolio` |
| Banco de dados | PostgreSQL em `localhost:5432`, banco `portfolio_db` |
| Variáveis (senhas, etc.) | `/var/www/portfolio/.env` |
| Iniciar/parar o app | `systemctl start portfolio` / `systemctl stop portfolio` |
| Ver logs do app | `journalctl -u portfolio -f` |
| Reiniciar Nginx | `systemctl reload nginx` |

---

## Atualizar o site depois de mudanças

Se você alterar o código (no PC) e subir de novo (Git ou upload):

```bash
cd /var/www/portfolio
git pull   # se usou Git
source venv/bin/activate
pip install -r requirements.txt
systemctl restart portfolio
```

---

## Problemas comuns

- **Site não abre:** confira se o firewall libera as portas 80 e 443: `ufw allow 80 && ufw allow 443 && ufw reload`.
- **Erro 502:** o app não está rodando. Veja: `systemctl status portfolio` e `journalctl -u portfolio -n 50`.
- **Chat não conecta:** confira se o bloco `location /socket.io` está igual ao do passo 9 e se reiniciou o Nginx após editar.
- **Erro de conexão com o banco:** confira o `.env` (usuário, senha, nome do banco) e se o PostgreSQL está ativo: `systemctl status postgresql`.

Se quiser, na próxima mensagem você pode dizer em que passo parou (por exemplo: “já criei o VPS e conectei no SSH”) e seguimos a partir daí.
