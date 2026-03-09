# Configurar MongoDB Atlas no projeto

Siga estes passos para conectar o formulário de contato e o chat ao MongoDB Atlas.

---

## 1. Criar conta e cluster no Atlas

1. Acesse **https://www.mongodb.com/cloud/atlas** e clique em **Try Free**.
2. Crie uma conta (pode usar Google ou e-mail).
3. Crie uma **organização** e um **projeto** (pode usar os nomes sugeridos).
4. Em **Deploy a database**:
   - Escolha **M0 FREE** (plano gratuito).
   - Região: escolha a mais próxima (ex.: São Paulo).
   - Clique em **Create**.

---

## 2. Criar usuário do banco

1. Na tela **Security Quickstart**, em **Authentication**:
   - Clique em **Create Database User**.
   - **Username:** ex. `portfolio_app`
   - **Password:** crie uma senha forte e **guarde** (você vai usar na URI).
   - Método: **Password**.
   - Clique em **Create User**.

---

## 3. Liberar acesso pela internet

1. Em **Where would you like to connect from?**:
   - Clique em **Add My Current IP Address** (recomendado), **ou**
   - Clique em **Allow Access from Anywhere** e use `0.0.0.0/0` (menos seguro, mas funciona de qualquer rede).
2. Clique em **Finish and Close**.

---

## 4. Pegar a Connection String (URI)

1. No painel do cluster, clique em **Connect**.
2. Escolha **Drivers** (ou **Connect your application**).
3. Copie a **connection string**. Ela será parecida com:
   ```text
   mongodb+srv://portfolio_app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
4. **Substitua `<password>`** pela senha real do usuário que você criou.
   - Se a senha tiver caracteres especiais (ex.: `@`, `#`, `%`), eles precisam ser codificados em URL. Exemplo: `@` vira `%40`. Ou crie uma senha só com letras e números para evitar isso.

---

## 5. Colocar a URI no projeto

1. Abra o arquivo **`.env`** na raiz do projeto (pasta onde está o `config.py`).
2. Na linha **MONGO_URI**, substitua `COLE_SUA_URI_DO_ATLAS_AQUI` pela string que você copiou (já com a senha no lugar de `<password>`).

Exemplo no `.env`:

```env
MONGO_URI=mongodb+srv://portfolio_app:MinHaSenhA123@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB=portfolio_db
```

3. Salve o arquivo.
4. Reinicie a aplicação Flask (pare e rode de novo `python app.py` ou o comando que você usa).

---

## 6. Testar

- Envie o formulário de contato no site.
- Se aparecer **"Mensagem enviada com sucesso!"**, a conexão com o Atlas está funcionando.

No Atlas, em **Database** → **Browse Collections**, o banco `portfolio_db` será criado automaticamente na primeira gravação (leads, eventos, chat, etc.).

---

## Problemas comuns

| Problema | Solução |
|----------|--------|
| "Serviço temporariamente indisponível" | Confira se a URI está certa no `.env`, se a senha está no lugar de `<password>` e se o IP foi liberado no Atlas (passo 3). |
| Senha com caracteres especiais | Use uma senha só com letras e números ou codifique os especiais (ex.: `@` → `%40`). |
| Timeout / conexão lenta | Escolha uma região do cluster perto de você (ex.: São Paulo). |
