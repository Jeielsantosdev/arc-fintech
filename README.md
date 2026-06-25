# Arc Fintech Platform

Plataforma Fintech para cobrança e movimentação financeira em **USDC** na blockchain **Arc** (Circle).

---

## O que é este projeto?

Uma API backend completa que permite a qualquer empresa:

- Criar carteiras digitais para seus usuários na Arc
- Cobrar clientes em USDC via invoice + checkout
- Configurar assinaturas recorrentes
- Dividir pagamentos entre parceiros (split)
- Pagar funcionários internacionalmente em lote (payroll)

O projeto usa a biblioteca **arc-devkit** como camada de integração com a blockchain Arc.

---

## Por que arc-devkit?

A Arc é uma blockchain EVM-compatível criada pela Circle, onde o USDC é o token nativo de gas. Interagir com ela diretamente exigiria lidar com Web3, assinatura de transações, polling de receipts, monitoramento de eventos on-chain e estimativa de gas — tudo do zero.

O **arc-devkit** encapsula toda essa complexidade e expõe uma API Python de alto nível específica para o ecossistema Arc. Em vez de 80 linhas de código Web3, uma chamada como `PaymentAgent.execute(token="usdc", enviar=True)` cuida de assinar, fazer broadcast, estimar gas e aguardar a confirmação on-chain.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Blockchain | Arc Testnet (EVM, Chain ID 5042002) |
| Integração blockchain | **arc-devkit 0.4.1** |
| Backend | Python 3.11 + FastAPI |
| Banco de dados | PostgreSQL + SQLAlchemy |
| Cache / Idempotência | Redis |
| Migrações | Alembic |
| Segurança de chaves | Fernet (AES-128) |
| Assinatura de webhooks | HMAC-SHA256 |
| Containers | Docker + Docker Compose |

---

## Arquitetura

O projeto segue **Clean Architecture + DDD + Repository Pattern**. O arc-devkit vive exclusivamente na camada de infraestrutura — o domínio e os casos de uso não o conhecem diretamente.

```
src/
├── domain/            # Entidades puras (Wallet, Invoice, Subscription, Split, Employee, Transaction)
│                      # Sem nenhuma dependência externa. Zero arc-devkit aqui.
│
├── application/       # Casos de uso (CreateWallet, ProcessPayment, RunPayroll…)
│                      # Orquestram entidades e chamam serviços via interfaces.
│                      # Também sem arc-devkit direto.
│
├── infrastructure/
│   ├── blockchain/    # ← AQUI ESTÁ TODO O arc-devkit
│   │   ├── wallet_service.py    # create_wallet, get_balance, USDCToken, PortfolioAnalyzer
│   │   ├── payment_service.py   # PaymentAgent.execute / execute_batch
│   │   └── monitor_service.py   # MonitorAgent
│   ├── database/      # SQLAlchemy models + repositórios concretos
│   ├── cache/         # Redis — idempotência e distributed lock
│   └── webhooks/      # Dispatcher HMAC-SHA256
│
└── api/v1/            # FastAPI routers + Pydantic schemas
```

---

## Uso do arc-devkit — Detalhado

Esta seção documenta cada ponto do projeto onde o arc-devkit é chamado, qual função é usada e por que ela foi escolhida.

---

### 1. Criação de Carteira

**Arquivo:** [src/infrastructure/blockchain/wallet_service.py](src/infrastructure/blockchain/wallet_service.py)
**Ativado por:** `POST /api/v1/wallet/create`

```python
from arc_devkit.core.wallet import create_wallet

raw = create_wallet()
# Retorna: {"address": "0x...", "private_key": "0x..."}
```

**Por que arc-devkit aqui?**
O `create_wallet()` usa `eth_account.Account.create()` internamente, com o padrão correto de derivação de chave para o ecossistema Arc. Ele garante que o endereço gerado é um endereço EVM válido compatível com a rede Arc. Após receber o resultado, o projeto criptografa a `private_key` com Fernet antes de salvar no banco — a chave nunca é armazenada em texto puro.

---

### 2. Consulta de Saldo Nativo (ARC)

**Arquivo:** [src/infrastructure/blockchain/wallet_service.py](src/infrastructure/blockchain/wallet_service.py)
**Ativado por:** `GET /api/v1/wallet/{address}/balance`

```python
from arc_devkit.core.wallet import get_balance

resultado = get_balance("0xEndereço...")
# Retorna: {"address": "0x...", "balance_wei": "...", "balance_usdc": Decimal("100")}
```

**Por que arc-devkit aqui?**
Na Arc, o saldo nativo da rede é denominado em USDC (não ETH). O `get_balance()` do arc-devkit já faz a conversão de wei para a representação humana correta para a Arc, injetando o middleware PoA necessário para compatibilidade com o testnet da Circle.

---

### 3. Consulta de Saldo USDC (ERC-20)

**Arquivo:** [src/infrastructure/blockchain/wallet_service.py](src/infrastructure/blockchain/wallet_service.py)
**Ativado por:** `GET /api/v1/wallet/{address}/balance`

```python
from arc_devkit.usdc.token import USDCToken

usdc = USDCToken(contract_address=settings.usdc_contract_address)
saldo = usdc.balance("0xEndereço...")
# Retorna: Decimal("99.500000")
```

**Por que arc-devkit aqui?**
O `USDCToken` encapsula o ABI ERC-20 mínimo necessário para interagir com o contrato USDC na Arc, converte automaticamente de atomic units (6 casas decimais) para `Decimal` legível, e reutiliza a conexão Web3 já configurada pelo arc-devkit com o RPC correto da Arc. Escrever isso manualmente exigiria definir o ABI, instanciar o contrato e fazer a conversão de decimais manualmente.

---

### 4. Envio de USDC — Pagamento Individual

**Arquivo:** [src/infrastructure/blockchain/payment_service.py](src/infrastructure/blockchain/payment_service.py)
**Ativado por:** `POST /api/v1/checkout` → `ProcessPaymentUseCase`

```python
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key=chave_privada, rpc_url=settings.arc_rpc_url)

resultado = agent.execute(
    to="0xDestinatário...",
    amount_usdc=99.99,
    enviar=True,        # broadcast para a rede
    wait_receipt=True,  # aguarda confirmação on-chain
    token="usdc",       # ERC-20, não nativo
)
# Retorna: {"status": "confirmed", "tx_hash": "0x...", "receipt": {...}, "gas_usado": 65000}
```

**Por que arc-devkit aqui?**
O `PaymentAgent` é o componente central do projeto. Ele:
- Busca o nonce atual da carteira
- Estima o gas via `eth_estimateGas`
- Assina a transação ERC-20 com a chave privada
- Faz broadcast via `eth_sendRawTransaction`
- Aguarda a confirmação fazendo polling de `eth_getTransactionReceipt`
- Chama callbacks `on_success` / `on_failure` quando a transação é confirmada ou falha

Implementar tudo isso corretamente, com segurança e sem condições de corrida, levaria centenas de linhas. Com o arc-devkit, é uma chamada.

---

### 5. Pagamento em Lote — Folha de Pagamento e Split

**Arquivo:** [src/infrastructure/blockchain/payment_service.py](src/infrastructure/blockchain/payment_service.py)
**Ativado por:**
- `POST /api/v1/payroll/run` → `RunPayrollUseCase`
- `POST /api/v1/split` → `ExecuteSplitUseCase`

```python
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key=chave_privada, rpc_url=settings.arc_rpc_url)

pagamentos = [
    {"to": "0xFuncionario1...", "amount_usdc": 2000.0, "enviar": True},
    {"to": "0xFuncionario2...", "amount_usdc": 3500.0, "enviar": True},
    {"to": "0xFuncionario3...", "amount_usdc": 1800.0, "enviar": True},
]

resultados = agent.execute_batch(pagamentos)
# Retorna lista com status/tx_hash de cada transferência
```

**Por que arc-devkit aqui?**
O `execute_batch()` busca o nonce atual uma única vez e incrementa sequencialmente para cada transação do lote. Isso é crítico: se cada pagamento buscasse o nonce de forma independente, todas receberiam o mesmo valor e apenas a primeira seria confirmada na rede (as demais seriam rejeitadas por nonce duplicado). O arc-devkit resolve esse problema de forma transparente. Este mesmo método é reutilizado tanto no payroll (salários) quanto no split (divisão de receita entre plataforma e merchant).

---

### 6. Monitoramento de Endereços e Eventos USDC

**Arquivo:** [src/infrastructure/blockchain/monitor_service.py](src/infrastructure/blockchain/monitor_service.py)
**Ativado por:** internamente após pagamentos, ou via configuração de watch

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

agent = MonitorAgent(
    watched_address="0xRecebedor...",
    interval_seconds=10,
    usdc_contract_address=settings.usdc_contract_address,
    webhook_url="https://seusite.com/webhook/arc",
)

agent.execute(callback=meu_callback, max_iterations=60)
```

**Por que arc-devkit aqui?**
O `MonitorAgent` combina dois tipos de monitoramento simultaneamente:
1. **Polling de saldo nativo** — detecta qualquer mudança de saldo acima do threshold configurado
2. **Scan de eventos ERC-20 Transfer** — usa `eth_getLogs` para capturar transferências USDC diretamente no contrato, sem depender de WebSockets

Além disso, ele entrega o payload automaticamente para o `webhook_url` via HTTP POST, com estado persistido em JSON para sobreviver a reinicializações. Isso é exatamente o que precisamos para notificar o cliente (SaaS brasileira) quando um pagamento USDC é confirmado na Arc.

---

### 7. Histórico de Transações On-Chain

**Arquivo:** [src/infrastructure/blockchain/wallet_service.py](src/infrastructure/blockchain/wallet_service.py)
**Ativado por:** `GET /api/v1/transactions?address=0x...`

```python
from arc_devkit.analytics.portfolio import PortfolioAnalyzer

analyzer = PortfolioAnalyzer(usdc_contract=settings.usdc_contract_address)
snapshot = analyzer.analyze("0xEndereço...", scan_blocks=50)

# snapshot contém:
# - native_balance, usdc_balance
# - nonce (total de txs enviadas)
# - recent_txs (últimas N transações)
# - activity_score ("high" | "medium" | "low" | "inactive")
```

**Por que arc-devkit aqui?**
O `PortfolioAnalyzer` varre os últimos N blocos, filtra transações que envolvem o endereço, busca os receipts para determinar status de sucesso/falha, e computa um score de atividade. O resultado complementa o histórico indexado no PostgreSQL do projeto — enquanto o banco tem os dados das transações geradas pela própria plataforma, o PortfolioAnalyzer captura qualquer movimentação on-chain, independente da origem.

---

### 8. Verificação de Conectividade com a Arc

**Arquivo:** [src/api/v1/routers/health.py](src/api/v1/routers/health.py)
**Ativado por:** `GET /api/v1/health/blockchain`

```python
from arc_devkit.core.connection import check_connection

conectado = check_connection()
# Verifica is_connected(), block_number e chain_id
```

**Por que arc-devkit aqui?**
O `check_connection()` usa a mesma instância Web3 configurada pelo arc-devkit (com middleware PoA injetado) para validar que o RPC da Arc está acessível. É o health check canônico para o ambiente Arc — retorna `True` somente se a conexão, o bloco atual e o chain_id estiverem todos respondendo.

---

## Resumo de Integração

```
Endpoint                         arc-devkit usado
────────────────────────────────────────────────────────────────────
POST /api/v1/wallet/create    →  core.wallet.create_wallet()
GET  /api/v1/wallet/.../balance → core.wallet.get_balance()
                                  usdc.token.USDCToken.balance()
GET  /api/v1/transactions     →  analytics.portfolio.PortfolioAnalyzer
POST /api/v1/checkout         →  agents.payment_agent.PaymentAgent.execute()
POST /api/v1/split            →  agents.payment_agent.PaymentAgent.execute_batch()
POST /api/v1/payroll/run      →  agents.payment_agent.PaymentAgent.execute_batch()
(subscription worker)         →  agents.payment_agent.PaymentAgent.execute()
(monitor background)          →  agents.monitor_agent.MonitorAgent
GET  /api/v1/health/blockchain → core.connection.check_connection()
```

O que **não** usa arc-devkit: criação de invoices, subscriptions, employees — são operações puramente de banco de dados. Idempotência (Redis) e webhooks (HMAC+httpx) também são implementados diretamente, sem arc-devkit.

---

## Fluxo do Produto — SaaS Brasileira

```
1. SaaS cria invoice
   POST /api/v1/invoice
   └─ Salva no PostgreSQL, retorna checkout_url + qr_data

2. Cliente paga
   POST /api/v1/checkout
   └─ PaymentAgent.execute(token="usdc", enviar=True)
      └─ Arc Blockchain: USDC transferido e confirmado

3. Plataforma reage à confirmação
   ├─ Invoice.status = "paid"
   ├─ PaymentAgent.execute_batch()  ← Split: 10% plataforma / 90% merchant
   ├─ Subscription.renew()          ← Avança próximo vencimento
   └─ Webhook → SaaS Co             ← Notifica sistema do cliente
```

---

## Instalação e Execução

### Pré-requisitos

```bash
python --version   # 3.11+
docker --version   # Para PostgreSQL e Redis
```

### Configuração

```bash
cd arc-fintech
cp .env.example .env
```

Edite o `.env`. Variáveis obrigatórias:

```bash
# Arc
ARC_RPC_URL=https://rpc.arc.testnet.circle.com
ARC_PRIVATE_KEY=0x_chave_privada_da_hot_wallet

# Exigido pelo arc-devkit (AI Copilot interno)
ANTHROPIC_API_KEY=sk-ant-...

# Banco e Cache
DATABASE_URL=postgresql://fintech:fintech_pass@localhost:5432/arc_fintech
REDIS_URL=redis://localhost:6379/0

# Segurança — gere com o comando abaixo
KEY_ENCRYPTION_SECRET=...
WEBHOOK_SECRET=...
```

Gerar `KEY_ENCRYPTION_SECRET`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Subir banco e cache

```bash
docker-compose up -d db redis
```

### Instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Rodar a API

```bash
uvicorn src.main:app --reload --port 8000
```

- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Compose completo

```bash
docker-compose up --build
```

Sobe API + PostgreSQL + Redis + subscription worker.

---

## Testes

```bash
# Unitários — sem infra externa, arc-devkit mockado
pytest tests/unit/ -v

# Integração — SQLite in-memory + arc-devkit mockado
pytest tests/integration/ -v

# Tudo
pytest -v
```

---

## Exemplos de Uso

### Criar carteira

```bash
curl -X POST http://localhost:8000/api/v1/wallet/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "cliente-42"}'
```

```json
{
  "wallet_id": "uuid",
  "user_id": "cliente-42",
  "address": "0x...",
  "status": "active"
}
```

### Consultar saldo

```bash
curl http://localhost:8000/api/v1/wallet/0xABC.../balance
```

```json
{
  "address": "0x...",
  "native_balance": "0.5",
  "usdc_balance": "100.000000"
}
```

### Criar invoice

```bash
curl -X POST http://localhost:8000/api/v1/invoice \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: inv-junho-2026-cliente-42" \
  -d '{
    "amount_usdc": "99.99",
    "recipient_address": "0xMerchantWallet...",
    "description": "Pro Plan - Junho 2026"
  }'
```

```json
{
  "invoice_id": "uuid",
  "status": "pending",
  "amount_usdc": "99.99",
  "checkout_url": "/api/v1/checkout/uuid",
  "qr_data": "arc:pay?invoice=uuid&amount=99.99&to=0x..."
}
```

### Processar pagamento (checkout)

```bash
curl -X POST http://localhost:8000/api/v1/checkout \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: checkout-junho-2026-cliente-42" \
  -d '{
    "invoice_id": "uuid-da-invoice",
    "webhook_url": "https://seusite.com/webhook/arc"
  }'
```

```json
{
  "status": "paid",
  "invoice_id": "uuid",
  "tx_hash": "0x...",
  "amount_usdc": "99.99"
}
```

### Split de pagamento

```bash
curl -X POST http://localhost:8000/api/v1/split \
  -H "Content-Type: application/json" \
  -d '{
    "name": "revenue-split",
    "total_amount_usdc": "100.00",
    "recipients": [
      {"address": "0xPlataforma...", "percentage": "10", "label": "platform"},
      {"address": "0xMerchant...",   "percentage": "90", "label": "merchant"}
    ]
  }'
```

```json
{
  "status": "done",
  "tx_hashes": ["0x...", "0x..."],
  "breakdown": [
    {"label": "platform", "percentage": "10", "amount_usdc": "10.000000"},
    {"label": "merchant", "percentage": "90", "amount_usdc": "90.000000"}
  ]
}
```

### Registrar funcionário e rodar folha

```bash
# Cadastrar
curl -X POST http://localhost:8000/api/v1/payroll/employee \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "wallet_address": "0xJoao...",
    "salary_usdc": "2000.00",
    "department": "Engineering"
  }'

# Rodar folha de todos os ativos
curl -X POST http://localhost:8000/api/v1/payroll/run \
  -H "Content-Type: application/json" \
  -d '{"description": "Folha Junho 2026", "broadcast": true}'
```

```json
{
  "run_id": "uuid",
  "status": "done",
  "total_employees": 5,
  "confirmed": 5,
  "failed": 0,
  "total_amount_usdc": "10000.00"
}
```

### Exemplo Python completo

```python
import httpx

BASE = "http://localhost:8000/api/v1"

# 1. Carteira
wallet = httpx.post(f"{BASE}/wallet/create", json={"user_id": "user-1"}).json()

# 2. Invoice
invoice = httpx.post(
    f"{BASE}/invoice",
    json={"amount_usdc": "99.99", "recipient_address": wallet["address"]},
    headers={"Idempotency-Key": "inv-001"},
).json()

# 3. Checkout
checkout = httpx.post(
    f"{BASE}/checkout",
    json={"invoice_id": invoice["invoice_id"], "webhook_url": "https://meusite.com/hook"},
    headers={"Idempotency-Key": "checkout-001"},
).json()

print(f"Pago! TX: {checkout['tx_hash']}")
```

---

## Segurança

| Mecanismo | Implementação |
|---|---|
| Chaves privadas | Fernet (AES-128-CBC + HMAC) — nunca armazenadas em texto puro |
| Idempotência | Redis SETNX com TTL 24h — evita pagamento duplicado |
| Lock distribuído | Redis NX+EX — evita race condition em requests concorrentes |
| Assinatura de webhooks | HMAC-SHA256 formato `t={ts},v1={hex}` |
| Verificação de replay | Timestamp no payload + comparação constante em tempo |
| Auditoria | Tabela `transactions` imutável com todo tx_hash registrado |

### Verificar assinatura do webhook (receptor)

```python
from src.infrastructure.webhooks.dispatcher import WebhookDispatcher

# No seu endpoint que recebe webhooks da plataforma
is_valid = WebhookDispatcher.verify_signature(
    payload_body=request.body,
    signature_header=request.headers["X-Arc-Signature"],
    secret="seu_WEBHOOK_SECRET",
)
```

---

## Migrações de Banco

```bash
# Criar migração após mudar models
alembic revision --autogenerate -m "descricao"

# Aplicar
alembic upgrade head

# Reverter
alembic downgrade -1
```

---

## Deploy em Produção

### Checklist

- [ ] `ARC_PRIVATE_KEY` em AWS KMS ou HashiCorp Vault (não em `.env`)
- [ ] `KEY_ENCRYPTION_SECRET` rotacionada e em Secrets Manager
- [ ] PostgreSQL com SSL (`?sslmode=require`)
- [ ] Redis com AUTH e TLS
- [ ] `APP_ENV=production` (desliga SQL echo)
- [ ] CORS restrito ao domínio real
- [ ] `USDC_CONTRACT_ADDRESS` atualizado para o endereço oficial da Circle quando publicado

### Infraestrutura recomendada

```
Load Balancer
├── API (2+ réplicas) — uvicorn
├── Worker — subscription_worker.py (1 réplica)
├── PostgreSQL — RDS Multi-AZ
└── Redis — ElastiCache
```

---

## Roadmap

### v1.1
- Account Abstraction (ERC-4337) — wallets sem necessidade de gas pré-carregado
- Endereço USDC oficial na Arc quando Circle publicar
- Rate limiting por API key
- QR Code com imagem (biblioteca `qrcode`)

### v1.2
- Multi-currency via CCTP (EURC)
- Portal do cliente em React
- Reembolsos automáticos

### v2.0
- Smart contracts de split on-chain (sem hot wallet)
- Plugin para WooCommerce / Shopify
- KYC/AML integrado
