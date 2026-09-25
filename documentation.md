# Edital Tracker — Documentação Técnica

> Última atualização: 2026-09-25  
> Versão: 0.6  
> Repositório: `cadeteafya/edital-tracker` — frontend Next.js + scraper Python

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Stack tecnológico](#3-stack-tecnológico)
4. [Estrutura de diretórios](#4-estrutura-de-diretórios)
5. [Modelo de dados](#5-modelo-de-dados)
6. [Scraper Python](#6-scraper-python)
7. [Frontend Next.js](#7-frontend-nextjs)
8. [Fluxo de dados completo](#8-fluxo-de-dados-completo)
9. [Notificações Microsoft Teams](#9-notificações-microsoft-teams)
10. [Configuração e variáveis de ambiente](#10-configuração-e-variáveis-de-ambiente)
11. [Como rodar localmente](#11-como-rodar-localmente)
12. [Deploy (Vercel + GitHub Actions)](#12-deploy-vercel--github-actions)
13. [Decisões de design e trade-offs](#13-decisões-de-design-e-trade-offs)
14. [Limitações conhecidas e próximos passos](#14-limitações-conhecidas-e-próximos-passos)

---

## 1. Visão geral

O **Edital Tracker** monitora continuamente o portal [med.estrategia.com](https://med.estrategia.com/portal/?s=edital) em busca de lançamentos de editais de **residência médica** e **provas de título**. Para cada edital detectado, o sistema:

1. Extrai o cronograma estruturado (tabela de datas) e a taxa de inscrição.
2. Detecta o link para o site oficial do processo seletivo.
3. Limpa o título com regras fixas de texto (ex.: remove "confira o edital"). Não há IA no projeto.
4. Persiste tudo em `data/editals.json`, commitado no repositório.
5. Exibe os dados em uma página web moderna com busca e paginação.
6. Aciona o sistema `alerta-editais` (repo separado) que envia cartões estruturados ao Microsoft Teams.

**O que é monitorado:**
- Notícias com padrão de lançamento de edital: "divulga edital", "publica edital", "abre inscrições", "vagas para residência médica", etc.
- Duas fontes simultâneas: busca HTML (`?s=edital`) + feed RSS (`/category/noticias/feed/`).
- Retificações/atualizações de editais já no banco (atualizam o registro existente).

**O que é excluído:**
- `category-concursos` — concursos públicos municipais/estaduais para cargos médicos.
- Artigos classificados como `concurso_publico` pelo regex classifier (ex.: "vagas para médicos", "Prefeitura de X", "perito médico").
- Artigos sem padrão reconhecível de lançamento de edital.

---

## 2. Arquitetura

```
┌─────────────────────────────────────────┐
│           med.estrategia.com            │
│   WordPress — listagem HTML + RSS feed  │
└───────────────┬─────────────────────────┘
                │ HTTP (httpx + cache 30min)
                ▼
┌─────────────────────────────────────────┐
│           scraper/  (Python)            │
│  fetch → classify → extract →           │
│  identify → rewrite → store             │
└───────────────┬─────────────────────────┘
                │ grava
                ▼
┌─────────────────────────────────────────┐
│         data/editals.json               │
│   { lastSyncedAt, editals: [...] }      │
└───────────────┬─────────────────────────┘
                │ git commit + push
                ▼
┌─────────────────────────────────────────┐   ┌──────────────────────────────┐
│      Vercel (edital-tracker-woad)       │   │   alerta-editais (repo sep.) │
│   Next.js SSR force-dynamic             │◄──│   monitora o site publicado  │
│   page.tsx → loadEditals → EditalCards  │   │   envia cartão ao Teams      │
└─────────────────────────────────────────┘   └──────────────────────────────┘
```

A comunicação entre scraper e frontend é **desacoplada via arquivo JSON** — não há banco de dados, não há API. O arquivo é commitado no repo e dispara o redeploy da Vercel automaticamente.

---

## 3. Stack tecnológico

### Frontend

| Tecnologia | Versão | Papel |
|---|---|---|
| Next.js | 16.2.6 | Framework React (App Router, SSR com `force-dynamic`) |
| React | 19.2.4 | Componentes de UI |
| Tailwind CSS | ^4 | Estilização (CSS-first, sem tailwind.config.js) |
| TypeScript | ^5 | Tipagem estática em toda a camada frontend |
| Geist (font) | via `next/font` | Tipografia — sans e mono |
| Node.js | 24 | Runtime |

### Scraper

| Tecnologia | Versão | Papel |
|---|---|---|
| Python | 3.13+ | Runtime do scraper |
| httpx | >=0.27 | HTTP client com suporte a redirects e timeout |
| BeautifulSoup4 | >=4.12 | Parse HTML dos artigos |
| PyMuPDF | >=1.24 | Leitura do PDF do edital (fallback da taxa) |
| anthropic SDK | >=0.40 | Instalado, mas **não usado** (ver seção 13 — "Título sem IA") |

---

## 4. Estrutura de diretórios

```
edital-tracker/
│
├── data/
│   └── editals.json          # Banco de dados — lido pelo Next.js, escrito pelo scraper
│
├── scraper/                  # Módulo Python — roda com: python -m scraper
│   ├── __init__.py
│   ├── __main__.py           # Orquestrador principal (entry point)
│   ├── fetch.py              # HTTP client com cache em disco (30 min TTL)
│   ├── classify.py           # Classifica artigos: edital_launch / update / concurso / skip
│   ├── extract.py            # Parseia HTML do artigo → timeline, URL oficial, taxa, data
│   ├── pdf_fee.py            # Fallback: taxa lida do PDF do edital (em memória, PyMuPDF)
│   ├── identify.py           # Detecta fonte (instituição) e ano do exame
│   ├── rewrite.py            # Limpa o título com regras fixas (regex)
│   ├── store.py              # Estrutura Edital, merge, load/save JSON
│   ├── requirements.txt
│   └── .gitignore            # Exclui .cache/ do versionamento
│
├── src/
│   ├── app/
│   │   ├── layout.tsx        # Layout raiz: metadados, fontes, html lang="pt-BR"
│   │   ├── page.tsx          # Página principal: filtro, ordenação, paginação, render
│   │   └── globals.css       # CSS global: variáveis de tema, body com gradients
│   │
│   ├── components/
│   │   ├── EditalCard.tsx    # Card individual — banner, taxa, cronograma, CTA
│   │   ├── SiteHeader.tsx    # Header sticky com logo, contador, última sincronização
│   │   ├── PageIntro.tsx     # Seção hero com título e contagem de editais
│   │   ├── SearchBar.tsx     # Input de busca (client component) com URL params debounced
│   │   └── Pagination.tsx    # Navegação de páginas via <Link> (SSR-friendly)
│   │
│   ├── lib/
│   │   ├── dates.ts          # findNextMilestone, isNewEdital, formatRelativeDays
│   │   └── loadEditals.ts    # Lê e deserializa data/editals.json no servidor
│   │
│   └── types/
│       └── edital.ts         # Tipos TypeScript: Edital, TimelineEntry
│
├── .github/
│   └── workflows/
│       └── scrape.yml        # Cron GitHub Actions — roda o scraper automaticamente
│
├── .gitignore
├── documentation.md          # Este arquivo
├── CLAUDE.md → AGENTS.md
├── next.config.ts
├── tsconfig.json
└── package.json
```

---

## 5. Modelo de dados

### `Edital` (TypeScript — `src/types/edital.ts`)

```typescript
type TimelineEntry = {
  label: string;       // ex.: "Período de Inscrições"
  date: string;        // ex.: "05/06 a 26/07/2026" ou "27/09/2026"
  isRange?: boolean;   // true quando date contém " a "
};

type Edital = {
  id: string;                    // slug da URL do artigo (gerado pelo scraper)
  source: {
    name: string;                // Nome completo da instituição
    shortName: string;           // Nome curto para exibição no card
    accentColor: string;         // Hex — cor do banner do card
  };
  originalTitle: string;         // Título original do artigo na Estratégia MED
  rewrittenTitle: string;        // Título limpo por regras fixas — faz parte da chave de dedup do Teams
  examYear: number;              // Ano do processo (extraído do título)
  originalUrl: string;           // URL do artigo na Estratégia MED
  officialUrl?: string | null;   // URL do site oficial do processo seletivo
  scrapedAt?: string;            // ISO 8601 — quando o scraper viu pela 1ª vez (IMUTÁVEL)
  publishedAt: string;           // ISO date — data de publicação do artigo
  updatedAt: string;             // ISO date — data da última atualização
  timeline: TimelineEntry[];     // Cronograma. Pode ser [] se não extraível.
  warningNote?: string | null;   // Nota de atenção (mantida no JSON, não exibida no card)
  fee?: string | null;           // Taxa de inscrição ex.: "R$ 800" — null/ausente = "Confirmar"
};
```

> **`fee` ausente vs. `null`**: ambos renderizam "Confirmar" no card. O scraper grava `null` quando não encontra o valor; registros anteriores à adição do campo simplesmente não têm a chave.

### `data/editals.json` (schema)

```json
{
  "lastSyncedAt": "2026-09-22T14:00:00+00:00",
  "editals": [
    {
      "id": "string (slug)",
      "source": { "name": "", "shortName": "", "accentColor": "#hex" },
      "originalTitle": "",
      "rewrittenTitle": "",
      "examYear": 2027,
      "originalUrl": "https://med.estrategia.com/...",
      "officialUrl": "https://...",
      "scrapedAt": "2026-09-22T14:00:00+00:00",
      "publishedAt": "2026-09-22",
      "updatedAt": "2026-09-22",
      "timeline": [
        { "label": "", "date": "", "isRange": false }
      ],
      "warningNote": null,
      "fee": "R$ 800",
      "revisions": []
    }
  ]
}
```

> **`scrapedAt` é imutável** — gravado na primeira inserção pelo `store.merge()` e nunca sobrescrito. Usado para calcular se o badge "SAIU O EDITAL" deve aparecer (expira em 2 dias).

---

## 6. Scraper Python

### Entry point

```bash
python -m scraper              # usa cache (30 min TTL)
python -m scraper --no-cache   # força re-fetch de todas as páginas
python -m scraper --limit 5    # processa apenas os 5 primeiros itens
```

### Fontes de dados (dupla)

O scraper consulta duas fontes em paralelo e deduplica por URL:

| Fonte | URL | Característica |
|---|---|---|
| Busca HTML | `?s=edital` | Cobertura ampla, sujeita a cache de horas no servidor |
| RSS feed | `/category/noticias/feed/` | Sem cache — detecta artigos recém-publicados imediatamente |

### Pipeline de execução (`__main__.py`)

```
1. fetch(?s=edital) + fetch(RSS feed)
       ↓ deduplica por URL
2. parse_listing() + parse_rss_listing() → list[ListingItem]
       ↓
3. [purge] Remove do banco registros que o classificador atual rejeitaria
       ↓
4. Para cada ListingItem:
   a. classify(title, excerpt, categories) → Classification
      ├── "concurso"      → skip
      ├── "skip"          → skip
      ├── "edital_launch" → processar artigo (passo 5)
      └── "update"        → processar artigo (passo 5) → aplicar como retificação
   b. Se já no banco com timeline e não é "update" → skip (não re-dispara alertas)
       ↓
5. fetch(item.url)
       ↓
6. parse_article() → ArticleData
   ├── extrai timeline (table > ul > fallback vazio)
   ├── extrai officialUrl (_is_official_candidate())
   ├── extrai fee (_extract_fee())
   ├── localiza o PDF do edital (find_edital_pdf())
   └── extrai publishedAt (meta OG > li.meta-date)
       ↓
6b. Sem fee + edital novo no banco + 1 edital → pdf_fee.fee_from_pdf()
       ↓
7. rewrite_title() → str (regras fixas; mesmo título original = mesmo resultado)
       ↓
8. detect_source(), detect_exam_year()
       ↓
9. store.build_record() + store.merge(db, record)
       ↓
10. store.save(db) → data/editals.json
```

### Classificação (`classify.py`)

Quatro passes em ordem — primeira regra que bate vence:

| Passe | Tipo | Exemplos de padrões |
|---|---|---|
| 1 | `concurso` | categoria `category-concursos` sem `category-noticias` |
| 2 | `concurso_publico` | "concurso público", "vagas para médicos", "prefeitura", "perito médico", "auditor médico", "processo seletivo simplificado" |
| 3 | `edital_launch` | "divulga edital", "publica edital", "saiu o edital", "abre inscrições", "edital publicado", "vagas para residência médica", "prazo de inscrições", "inscrições abertas/começam" |
| 4 | `update` (retificação) | "retificação do edital", "edital retificado", "adiamento", "confirma data" |
| 5 | `skip` | nenhum padrão reconhecido |

> **Segurança:** os padrões `concurso_publico` (passe 2) rodam **antes** dos padrões de lançamento (passe 3), garantindo que concursos municipais/estaduais nunca sejam capturados mesmo que o título contenha palavras como "residência".

### Extração de taxa (`extract.py — _extract_fee`)

```python
_FEE_PATTERN = re.compile(
    r"taxa\b.{0,80}?(R\$\s*[\d.,]+)"   # "taxa de R$ 800"
    r"|"
    r"(R\$\s*[\d.,]+).{0,40}?\btaxa\b", # "R$ 800 de taxa"
    re.I,
)
```

- Busca no texto completo do `div.entry-content`.
- Ignora ocorrências cujo contexto indica outra taxa (treineiro, recurso, desconto, cotista, bolsa, emissão de título…) — `REJECT_CTX` de `pdf_fee.py`.
- Remove pontuação final de frase (ex.: "R$ 600." → "R$ 600").
- Retorna `None` se não encontrado → entra o fallback via PDF (abaixo); se ainda assim `None`, o frontend exibe "Confirmar".

### Fallback da taxa via PDF do edital (`pdf_fee.py`)

Quando o artigo não informa a taxa, o scraper lê o PDF do edital linkado no botão do artigo.

**Quando roda** (`__main__.py`) — todas as condições:
- artigo **sem** taxa no texto;
- edital **novo** no banco (registros existentes nunca são alterados por este fallback — não há retroativo);
- não é retificação (`kind != "update"`);
- a página tem **exatamente um** botão de edital (`find_edital_pdf`).

**Botão de edital** = `a.wp-block-button__link` apontando para `.pdf` cujo texto contém "edital". Botões de retificação, errata, cronograma, comunicado, quadro de vagas, resultado e gabarito são ignorados. **Dois ou mais editais** (ex.: acesso direto + R+) → não busca, fica "Confirmar".

**Leitura:** PDF baixado e lido **somente em memória** com PyMuPDF (nada é gravado em disco), primeiras 30 páginas, limite de 25 MB, timeout 45 s. Qualquer falha → `None`.

**Busca, em níveis** (usa o mais forte que encontrar):

| Nível | Padrões |
|---|---|
| forte | "taxa de inscrição … R$ X", "inscrição … no valor de R$ X", "valor da inscrição R$ X" |
| tabela | cabeçalho "Taxa de Insc." + valores `600,00 03 anos` (padrão CONSESP) |
| fraco | "taxa … R$ X", "R$ X … taxa" |

**Regras conservadoras — na dúvida, `None` ("Confirmar"):**
- valores diferentes no mesmo nível (ex.: R$ 650 e R$ 900 por programa);
- outro valor logo em seguida ("1. R$ 500 para X; 2. R$ 750 para Y"), exceto detalhamento do total ("sendo um depósito de R$ 612");
- menção a sócio / associado / membro (taxas por categoria em provas de título);
- PDF sem texto (escaneado).

Validação (set/2026, 66 PDFs da base): 38 acertos, 0 valores errados, 11 taxas novas preenchidas onde o artigo não tinha.

### Extração de URL oficial (`extract.py — _is_official_candidate`)

Rejeita automaticamente domínios da Estratégia, redes sociais (facebook, instagram, telegram, etc.) e paths de política/privacidade.

Prioriza (ordem):
1. Link no bloco "atenção" com `_is_official_candidate`
2. `<a>` com texto-âncora indicativo: "inscrição", "acesse", "edital", "portal", "candidato"
3. Primeiro link externo genérico válido no `entry-content`
4. PDF (`wp-content/uploads/*.pdf`) como último recurso

### Extração de cronograma (`extract.py`)

Tenta em ordem:
1. `<table>` com ≥ 3 linhas contendo tokens de data → `TimelineEntry[]`
2. `<ul><li>` com formato "Label: data" e ≥ 3 itens
3. Retorna `[]` — artigo é aceito mesmo sem cronograma (card exibe aviso)

### Merge e retificações (`store.py`)

- **Nova inserção**: `scrapedAt` = agora (UTC ISO). Nunca mais alterado.
- **Atualização** (`merge`): se `timeline` ou `warningNote` mudarem, o estado anterior vai para `revisions[]`. `scrapedAt` é **preservado**.
- **Retificação** (`apply_revision`): artigos classificados como `update` buscam o registro pai pelo `shortName`. Se encontrado, atualiza `timeline`, `warningNote`, `officialUrl` e arquiva em `revisions`.
- **Purga retroativa**: ao fim de cada execução, registros que o classificador atual rejeitaria são removidos do banco.

---

## 7. Frontend Next.js

### `src/app/page.tsx` — Página principal

Server Component com `export const dynamic = "force-dynamic"` (re-renderiza a cada request, sempre reflete o JSON mais recente sem rebuild).

```
await searchParams → query + page
loadEditalsSnapshot() → Edital[]
filter(query) → sort(updatedAt desc) → paginate(PAGE_SIZE=9)
render: SiteHeader + PageIntro + SearchBar + grid[EditalCard] + Pagination
```

### `src/lib/loadEditals.ts`

Lê `data/editals.json` e mapeia campo a campo para o tipo TypeScript `Edital`. **Importante:** cada novo campo do JSON deve ser adicionado explicitamente ao mapeamento aqui — campos ausentes são silenciosamente descartados.

```typescript
const editals: Edital[] = raw.editals.map((e) => ({
  id: e.id,
  // ... outros campos ...
  warningNote: e.warningNote,
  fee: e.fee,   // ← obrigatório para o campo chegar ao EditalCard
}));
```

### `src/components/EditalCard.tsx`

Props: `{ edital: Edital; isNew: boolean }`

Seções do card (de cima para baixo):
1. **Banner** (112px): gradiente `accentColor → accentColor + #0f172a`. Badges: "SAIU O EDITAL" (se `isNew`) + `shortName` + `examYear`.
2. **Título reescrito** + metadados (`source.name` · data de publicação).
3. **Próximo marco**: próxima data futura na timeline. Exibe label, data e contagem relativa.
4. **Taxa**: linha com label "TAXA" e valor `fee` (ou "Confirmar" se `fee` for null/undefined).
5. **Cronograma**: `<ol>` com linhas. A linha do próximo marco recebe destaque na cor do card. Se `timeline=[]`, exibe aviso.
6. **CTA**: botão "Site oficial" linkando para `officialUrl`.

### `src/components/SearchBar.tsx` (Client Component)

- `useTransition` + `useRouter.push` — atualiza URL params sem bloquear a UI.
- Debounce de 300ms.
- Busca por: `source.name`, `source.shortName`, `rewrittenTitle`, `originalTitle`.

### `src/lib/dates.ts`

| Função | Descrição |
|---|---|
| `findNextMilestone(timeline)` | Retorna o próximo `TimelineEntry` com data futura e `daysUntil` |
| `isNewEdital(scrapedAt?, publishedAt?, days=2)` | `true` se `scrapedAt` ≤ 2 dias atrás |
| `formatRelativeDays(days)` | "hoje", "amanhã", "em N dias", "em N meses", "em mais de 1 ano" |

---

## 8. Fluxo de dados completo

```
[GitHub Actions cron — a cada 30min, Seg-Sex 07h-18h30 BRT]
      │
      ▼
python -m scraper --no-cache
      │
      ├── GET ?s=edital (HTML) + GET /category/noticias/feed/ (RSS)
      │   deduplica por URL → lista unificada
      │
      ├── Para cada item:
      │   ├── classify() → skip? continua.
      │   ├── GET {article_url}
      │   ├── parse_article() → timeline[], officialUrl, fee, publishedAt
      │   ├── rewrite_title() → regras fixas (regex)
      │   ├── detect_source() / detect_exam_year()
      │   └── store.merge() → atualiza ou insere
      │
      └── store.save() → data/editals.json
                │
                ▼
          git commit + push (se editals.json mudou)
                │
                ▼
          Vercel auto-deploy (trigger via push)
                │
                ▼
     Next.js (SSR force-dynamic) — edital-tracker-woad.vercel.app
          │
          └── EditalCards com timeline, taxa, próximo marco
                │
                ▼
     alerta-editais (cron independente — ver seção 9)
          └── Cartão Adaptive Card no Microsoft Teams
```

---

## 9. Notificações Microsoft Teams

As notificações são gerenciadas pelo repositório **`cadeteafya/alerta-editais`** — um sistema independente que monitora o Edital Tracker publicado e envia cartões ao Teams via Power Automate.

### Funcionamento

1. GitHub Actions do `alerta-editais` roda em cron (mesmo horário que o scraper).
2. `scraper.py` faz GET na homepage do Edital Tracker e extrai todos os `<article>` via XPath.
3. Compara com `data/last_seen.json` (chave: `"Título | Data de Publicação"`).
4. Para cada edital novo, `notifier.py` envia um Adaptive Card via webhook.
5. O estado é commitado de volta ao repo do `alerta-editais`.

### Campos extraídos do HTML do Edital Tracker

| Campo | XPath (resumido) |
|---|---|
| Título | `//h3/text()` |
| Instituição | Span no div com `linear-gradient` |
| Ano | Span com classes `font-mono text-white` |
| Tag de status | Span com `tracking-wider` |
| Data de publicação | `//header/p/span//text()` |
| Próximo Marco | Div `bg-[var(--surface-muted)]` — label + data + tempo restante |
| Cronograma | `//ol/li` — cada linha tem etapa + data |
| Link oficial | `//a[contains(text(), 'Site oficial')]/@href` |
| **Taxa** | `//span[normalize-space(text())='Taxa']/following-sibling::span[1]/text()` |

### Estrutura do cartão Teams (Adaptive Card v1.4)

```
┌─────────────────────────────────────────┐
│  🚨 NOVO EDITAL: {SIGLA} {ANO}         │  ← Container "Attention" (vermelho)
├─────────────────────────────────────────┤
│  {Título do edital (rewrittenTitle)}    │
├─────────────────────────────────────────┤
│  🏥 Instituição    │ {nome}             │  ← FactSet
│  📅 Publicado em  │ {data}             │
│  💰 Taxa          │ {valor ou Confirmar}│
├─────────────────────────────────────────┤
│  🚀 PRÓXIMO MARCO EM DESTAQUE          │  ← Container "accent" (azul)
│  {Etapa}    │ {Data} ({tempo restante}) │
├─────────────────────────────────────────┤
│  📅 Cronograma - Principais datas:     │
│  {Etapa 1}  │ {Data 1}                 │  ← FactSet (máx. 10 linhas)
│  ...                                    │
├─────────────────────────────────────────┤
│  [ 🌐 ACESSAR SITE OFICIAL ]           │  ← Botões de ação
│  [ 📋 VER NO EDITAL TRACKER ]          │
└─────────────────────────────────────────┘
```

### Regra de deduplicação

**Chave única = `"Título do Edital | Data de Publicação"`**

| Mudança no edital | Comportamento |
|---|---|
| `timeline`, `warningNote`, `officialUrl`, `fee`, `updatedAt` | Não dispara novo alerta |
| `rewrittenTitle` (título exibido no card) **ou** `publishedAt` (data de publicação) | Dispara novo alerta |

> Isso significa que atualizações de cronograma ou taxa não geram re-notificação. Apenas novos editais ou retificações formais (que mudam o título/data) disparam.

---

## 10. Configuração e variáveis de ambiente

### `edital-tracker`

Nenhuma variável necessária. `ANTHROPIC_API_KEY` **não está configurada e não deve ser configurada** sem antes ler a seção 13 ("Título sem IA").

### `alerta-editais` (repo separado)

| Secret GitHub | Obrigatório | Descrição |
|---|---|---|
| `TEAMS_WEBHOOK_URL` | Sim | URL do webhook gerado pelo Power Automate no Teams |

---

## 11. Como rodar localmente

### Pré-requisitos

- Node.js ≥ 20
- Python ≥ 3.13

### Setup inicial

```bash
# 1. Instalar dependências Node
npm install

# 2. Instalar dependências Python
pip install -r scraper/requirements.txt
```

### Rodar o scraper

```bash
python -m scraper              # popula/atualiza data/editals.json
python -m scraper --no-cache   # força re-fetch
python -m scraper --limit 3    # testa com poucos itens
```

### Rodar o frontend

```bash
npm run dev   # http://localhost:3000
```

---

## 12. Deploy (Vercel + GitHub Actions)

### Vercel (frontend) — ativo

- Repositório `cadeteafya/edital-tracker` conectado ao Vercel.
- URL de produção: `https://edital-tracker-woad.vercel.app/`
- Cada push para `master` redeploya automaticamente.
- Plano Hobby (gratuito). O scraper e a leitura de PDFs rodam no GitHub Actions, não na Vercel.

### GitHub Actions (scraper automático) — ativo

Arquivo: `.github/workflows/scrape.yml`

| Janela | Frequência |
|---|---|
| Seg–Sex, 07h–18h30 BRT | A cada 30 minutos |
| Sábado | Uma vez às 12h BRT |
| Domingo | Uma vez às 23h BRT |

O workflow roda `python -m scraper --no-cache`, commita `data/editals.json` se houver mudanças e faz push. Esse push dispara o redeploy da Vercel.

Repositório público → minutos do GitHub Actions ilimitados e gratuitos. Duração típica: ~20–60 s por execução (+2–3 s por PDF lido, só em editais novos).

### Autenticação Git no GitHub Actions

O scraper usa a identidade `github-actions[bot]` para commits. O push usa o token padrão `GITHUB_TOKEN` com permissão `contents: write` configurada no workflow.

---

## 13. Decisões de design e trade-offs

### JSON em vez de banco de dados

**Decisão:** `data/editals.json` como única fonte de verdade.

**Razão:** volume pequeno (dezenas de editais), acesso somente leitura no frontend, arquivo commitável — elimina banco externo no deploy inicial.

**Trade-off:** em escala precisaria migrar para SQLite ou PostgreSQL.

### SSR `force-dynamic` em vez de ISR

**Decisão:** `export const dynamic = "force-dynamic"` na página principal.

**Razão:** o JSON pode ser atualizado a qualquer momento pelo scraper. ISR introduziria staleness.

**Trade-off:** sem cache de página no CDN.

### `scrapedAt` imutável

**Decisão:** gravar `scrapedAt` apenas na primeira inserção.

**Razão:** o badge "SAIU O EDITAL" deve refletir quando *nós* vimos o edital pela primeira vez, não quando a Estratégia publicou.

### Classificação por regex (sem IA)

**Decisão:** classificar artigos com regex puro.

**Razão:** a classificação roda para 15+ artigos a cada execução. Regex são determinísticos e rápidos.

### Título sem IA

**Situação:** não há IA no projeto. `rewrite.py` contém uma chamada ao Claude que só seria ativada se `ANTHROPIC_API_KEY` existisse — ela não existe, então sempre roda a limpeza por regex.

**Por que importa:** o título (`rewrittenTitle`) faz parte da chave de dedup do Teams. Editais sem cronograma são reprocessados a cada execução; com regex, o título sai sempre igual e nada é reenviado.

**Se um dia ativar IA:** antes, travar o título na primeira gravação (não reescrever registros existentes). Caso contrário, títulos diferentes a cada execução gerariam alertas repetidos no Teams.

### Taxa via PDF só para editais novos

**Decisão:** o fallback de taxa pelo PDF roda apenas na inserção de um edital novo.

**Razão:** evita baixar PDFs a cada execução e garante que registros já notificados nunca mudem.

### `loadEditals.ts` com mapeamento explícito

**Decisão:** mapear campo a campo no `loadEditals.ts`, não usar spread (`...e`).

**Razão:** força que cada novo campo seja adicionado conscientemente, impedindo que dados sensíveis ou inesperados do JSON vazem para o frontend. **Consequência:** ao adicionar um campo novo no scraper, é obrigatório também adicioná-lo no mapeamento de `loadEditals.ts`.

---

## 14. Limitações conhecidas e próximos passos

### Limitações atuais

| # | Limitação | Impacto | Solução sugerida |
|---|---|---|---|
| L1 | Scraper não pagina a listagem (só 15 cards da página 1) | Editais antigos na página 2+ não são capturados | Implementar paginação: `?s=edital&paged=2` |
| L2 | Cronograma de artigos sem tabela HTML é `[]` | Card exibe aviso genérico | Extrair datas do corpo textual com regex |
| L3 | `accentColor` gerado por hash do shortName | Cor pode ter baixo contraste | Tabela manual de cores por instituição em `identify.py` |
| L4 | Sem testes automatizados | Regressões silenciosas | Adicionar pytest para `classify.py` e `extract.py` |
| L5 | Taxa não re-notificada no Teams se atualizada | Mudança de valor não chega ao Teams | Recapturar manualmente deletando o registro do JSON |
| L6 | Padrões de skip pendentes | Alguns artigos de "confira o edital", "abre seleção" ainda passam pelo classify | Adicionar novos SKIP_PATTERNS em `classify.py` |
| L7 | PDF escaneado (imagem) não é lido | Taxa fica "Confirmar" | Preencher manualmente (OCR não compensa) |
| L8 | Editais anteriores a v0.6 não passaram pelo fallback de PDF | Alguns antigos seguem "Confirmar" | Preencher manualmente, se necessário |
| L9 | `rewrite.py` e `anthropic` no requirements sem uso | Código morto | Remover, ou travar o título antes de ativar IA (seção 13) |
