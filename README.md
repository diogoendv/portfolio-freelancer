# Portfólio Freelancer — Ideias em Código

Site de portfólio e vendas para serviços de freelancer: **Conceitos/Ideias de Sites** e **Desenvolvimento de Sites Personalizados**.

## Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML5, CSS3 (Tailwind via CDN), JavaScript
- **Banco de dados:** MongoDB (leads, catálogo de ideias)

## Estrutura de pastas

```
Projeto/
├── app.py           # App Flask, rotas e validação de e-mail
├── config.py        # MONGO_URI, nome do DB e coleções
├── models/
│   ├── __init__.py
│   └── lead.py      # Modelo do documento de lead
├── templates/
│   └── index.html   # Página única (Hero, Ideias, Serviços, Contato)
├── static/
│   ├── css/
│   └── js/
└── requirements.txt
```

## Inicialização

### 1. Ambiente virtual (recomendado)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. MongoDB

- Instale o [MongoDB](https://www.mongodb.com/try/download/community) ou use um serviço em nuvem (ex.: Atlas).
- Por padrão a app usa `mongodb://localhost:27017` e o banco `portfolio_db`.
- Para alterar: defina as variáveis de ambiente `MONGO_URI` e `MONGO_DB`.

### 4. Rodar a aplicação

```bash
python app.py
```

Acesse: **http://127.0.0.1:5000**

## Funcionalidades

- **Home:** Hero com gradiente animado e frase de impacto.
- **Marketplace de Ideias:** Cards com efeito glass (backdrop-blur) e badge de categoria; dados vêm da API `/api/ideas` (MongoDB ou fallback).
- **Serviços:** Descrição dos pacotes (Conceitos e Desenvolvimento).
- **Contato/Briefing:** Formulário envia POST para `/api/contact`; o backend **valida o e-mail** (formato e domínio) antes de salvar na coleção `leads` do MongoDB.

## Notificação de novas mensagens no chat

Quando um visitante envia mensagem no chat, você pode ser avisado por e-mail ou webhook.

### Opção 1 — Gmail (grátis, recomendado)

Use o Gmail para enviar o aviso. Ative a verificação em duas etapas na conta Google e crie uma **Senha de app** em [google.com/apppasswords](https://myaccount.google.com/apppasswords). Defina no ambiente (PowerShell):

- `ADMIN_EMAIL` — e-mail que recebe o aviso
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USER=seu@gmail.com`
- `SMTP_PASSWORD=senha_de_16_caracteres`
- `SMTP_USE_TLS=1`

### Opção 2 — Webhook

1. Crie uma conta grátis no [IFTTT](https://ifttt.com).
2. Crie um Applet: **If This** → **Webhooks** → “Receive a web request” (evento ex.: `chat_message`).
3. **Then That** → **Email** → “Send me an email” (assunto e corpo podem usar os valores enviados).
4. No IFTTT, em Webhooks, copie a URL do webhook (ex.: `https://maker.ifttt.com/trigger/chat_message/with/key/SUA_KEY`).
5. Defina a variável de ambiente:
   ```bash
   set WEBHOOK_URL=https://maker.ifttt.com/trigger/chat_message/with/key/SUA_KEY
   ```
   O app envia um POST em JSON com: `event`, `session_id`, `message`, `text`.

### Opção 3 — Resend.com (e-mail por API)

1. Crie conta em [resend.com](https://resend.com) (plano gratuito).
2. Crie uma API Key e adicione/verifique um domínio (ou use o domínio de teste deles).
3. Defina no ambiente:
   ```bash
   set ADMIN_EMAIL=seu@email.com
   set RESEND_API_KEY=re_sua_chave
   ```

## Design

- Estilo minimalista high-tech.
- Fundo escuro `#0f172a`, destaques em ciano e violeta.
- Tipografia Inter, cards em glassmorphism, animações suaves e layout responsivo.
