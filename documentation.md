# Edital Tracker — Documentação Técnica

> Última atualização: 2026-05-25  
> Versão: 0.3  
> Repositório: monorepo local — frontend Next.js + scraper Python

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
9. [Configuração e variáveis de ambiente](#9-configuração-e-variáveis-de-ambiente)
10. [Como rodar localmente](#10-como-rodar-localmente)
11. [Plano de deploy (Vercel + GitHub Actions)](#11-plano-de-deploy-vercel--github-actions)
12. [Decisões de design e trade-offs](#12-decisões-de-design-e-trade-offs)
13. [Limitações conhecidas e próximos passos](#13-limitações-conhecidas-e-próximos-passos)

---

## 1. Visão geral

O **Edital Tracker** monitora continuamente o portal [med.estrategia.com](https://med.estrategia.com/portal/?s=edital) em busca de lançamentos de editais de **residência médica** e **provas de título**. Para cada edital detectado, o sistema:

1. Extrai o cronograma estruturado (tabela de datas).
2. Detecta o link para o site oficial do processo seletivo.
3. Reescreve o título de forma mais objetiva (via Claude API ou heurística).
4. Persiste tudo num banco JSON local (`data/editals.json`).
5. Exibe os dados em uma página web moderna com busca e paginação.

**O que é monitorado:**
- Notícias com padrão de lançamento de edital: "divulga edital", "publica edital", "abre inscrições", etc.
- Categorias WordPress: `category-noticias` e `category-provas-de-titulo-noticias`.
- Retificações/atualizações de editais já no banco (atualizam o registro existente).

**O que é excluído:**
- `category-concursos` — concursos públicos municipais/estaduais para cargos médicos (prefeituras, autarquias).
- Artigos classificados como `concurso_publico` pelo regex classifier (ex.: "X vagas para médicos", "Prefeitura de Y").
- Artigos sem padrão reconhecível que não se encaixam em nenhuma categoria.

---

## 2. Arquitetura

```
┌─────────────────────────────────────────┐
│           med.estrategia.com            │
│   WordPress — listagem + artigos        │
└──────────────────┬──────────────────────┘
                   │ HTTP (httpx + cache 30min)
                   ▼
┌─────────────────────────────────────────┐
│           scraper/  (Python)            │
│  fetch → classify → extract →           │
│  identify → rewrite → store             │
└──────────────────┬──────────────────────┘
                   │ grava
                   ▼
┌─────────────────────────────────────────┐
│         data/editals.json               │
│   { lastSyncedAt, editals: [...] }      │
└──────────────────┬──────────────────────┘
                   │ leitura em build/request
                   ▼
┌─────────────────────────────────────────┐
│      Next.js 16 (App Router, SSR)       │
│   page.tsx → loadEditals → cards        │
└─────────────────────────────────────────┘
```

A comunicação entre o scraper e o frontend é **desacoplada via arquivo JSON** — não há banco de dados, não há API. Isso simplifica o deploy (arquivo commitado no repo → Vercel redeploya automaticamente).

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
| anthropic SDK | >=0.40 | Reescrita de títulos via Claude Haiku (opcional) |
| python-slugify | >=8.0 | Geração de IDs (presente em requirements, não usado ativamente no momento) |

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
│   ├── extract.py            # Parseia HTML do artigo → timeline, URL oficial, data
│   ├── identify.py           # Detecta fonte (instituição) e ano do exame
│   ├── rewrite.py            # Reescreve título via Claude API ou heurística regex
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
│   │   ├── EditalCard.tsx    # Card individual — banner, cronograma, próximo marco, CTA
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
├── .claude/
│   └── launch.json           # Config do preview server (npm run dev, porta 3000)
│
├── .gitignore
├── documentation.md          # Este arquivo
├── CLAUDE.md → AGENTS.md     # Instrução para agentes de IA
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
  rewrittenTitle: string;        // Título reescrito (LLM ou heurística)
  examYear: number;              // Ano do processo (extraído do título)
  originalUrl: string;           // URL do artigo na Estratégia MED
  officialUrl?: string | null;   // URL do site oficial do processo seletivo
  scrapedAt?: string;            // ISO 8601 — quando o scraper viu pela 1ª vez (IMUTÁVEL)
  publishedAt: string;           // ISO date — data de publicação do artigo
  updatedAt: string;             // ISO date — data da última atualização
  timeline: TimelineEntry[];     // Cronograma. Pode ser [] se não extraível.
  warningNote?: string | null;   // Nota de atenção (obsoleto no card, mantido no JSON)
};
```

### `data/editals.json` (schema)

```json
{
  "lastSyncedAt": "2026-05-22T20:26:54+00:00",
  "editals": [
    {
      "id": "string (slug)",
      "source": { "name": "", "shortName": "", "accentColor": "#hex" },
      "originalTitle": "",
      "rewrittenTitle": "",
      "examYear": 2026,
      "originalUrl": "https://med.estrategia.com/...",
      "officialUrl": "https://...",
      "scrapedAt": "2026-05-22T20:26:00+00:00",
      "publishedAt": "2026-05-20",
      "updatedAt": "2026-05-20",
      "timeline": [
        { "label": "", "date": "", "isRange": false }
      ],
      "warningNote": null,
      "revisions": []
    }
  ]
}
```

> **`scrapedAt` é imutável** — gravado na primeira inserção pelo `store.merge()` e nunca sobrescrito em rodadas subsequentes. Usado para calcular se o badge "SAIU O EDITAL" deve aparecer (expira em 2 dias).

---

## 6. Scraper Python

### Entry point

```bash
python -m scraper              # usa cache (30 min TTL)
python -m scraper --no-cache   # força re-fetch de todas as páginas
python -m scraper --limit 5    # processa apenas os 5 primeiros cards da listagem
```

### Pipeline de execução (`__main__.py`)

```
1. fetch(LISTING_URL)
       ↓
2. parse_listing() → list[ListingItem]
       ↓
3. Para cada ListingItem:
   a. classify(title, excerpt, categories) → Classification
      ├── "concurso"      → skip
      ├── "skip"          → skip
      ├── "edital_launch" → processar artigo (passo 4)
      └── "update"        → processar artigo (passo 4) → aplicar como retificação
       ↓
4. fetch(item.url)
       ↓
5. parse_article() → ArticleData
   ├── extrai timeline (table > ul > fallback vazio)
   ├── extrai officialUrl (_is_official_candidate())
   └── extrai publishedAt (meta OG > li.meta-date)
       ↓
6. rewrite_title() → str
   ├── Se ANTHROPIC_API_KEY: chama Claude Haiku
   └── Senão: aplica regex heurísticos
       ↓
7. detect_source(), detect_exam_year()
       ↓
8. store.build_record() + store.merge(db, record)
       ↓
9. store.save(db) → data/editals.json

10. [purge] Remove do banco registros que o classificador atual rejeitaria
```

### Classificação (`classify.py`)

Ordem de avaliação (primeira regra que bate vence):

| Prioridade | Tipo | Exemplos de padrões |
|---|---|---|
| 1 | `concurso` | categoria `category-concursos` sem `category-noticias` |
| 2 | `concurso_publico` | "concurso público", "X vagas para médicos", "prefeitura de X", "perito médico", "auditor médico" |
| 3 | `update` | "retificação do edital", "edital retificado" |
| 4 | `edital_launch` | "divulga edital", "publica edital", "saiu o edital", "abre inscrições", "edital do/da/para 2026" |
| 5 | `update` (genérico) | "atualização", "adiamento", "confirma data", "previsão de edital" |
| 6 | `skip` | nenhum padrão reconhecido |

> **Importante:** `concurso_publico` foi adicionado para excluir concursos de prefeituras/autarquias que tinham `category-noticias` e passavam pelo classificador anterior.

### Extração de URL oficial (`extract.py — _is_official_candidate`)

Rejeita automaticamente:
- Domínios próprios: qualquer URL com "estrategia" no netloc
- Redes sociais: facebook.com, t.me, twitter.com, x.com, linkedin.com, instagram.com, etc.
- Padrões de path: `politica-de-privacidade`, `unsubscribe`, `sharer`, `shareArticle`

Prioriza (ordem):
1. Link no bloco "atenção" (`_find_warning_block`) com `_is_official_candidate`
2. Link em qualquer `<a>` com texto-âncora indicativo: "inscrição", "acesse", "edital", "portal", "candidato"
3. Primeiro link externo genérico válido no `entry-content`
4. PDF (`wp-content/uploads/*.pdf`) como último recurso

### Extração de cronograma (`extract.py`)

Tenta em ordem:
1. `<table>` com ≥ 3 linhas contendo tokens de data → `TimelineEntry[]`
2. `<ul><li>` com formato "Label: data" e ≥ 3 itens
3. Retorna `[]` — artigo é aceito mesmo sem cronograma (card mostra aviso)

### Detecção de fonte (`identify.py`)

Testa 15 instituições conhecidas por regex (ex.: `r"s[íi]rio[- ]liban[êe]s"`). Se nenhuma bater, extrai o primeiro bloco de palavras em maiúscula do título como `shortName`.

### Reescrita de título (`rewrite.py`)

- **Com `ANTHROPIC_API_KEY`**: chama `claude-haiku-4-5` com system prompt de reescrita objetiva (máx. 110 chars). Fallback para heurística se a chamada falhar.
- **Sem chave**: aplica regex sequencialmente — remove "confira o edital", "confira o documento", expande acrônimos comuns, limpa pontuação residual.

### Merge e retificações (`store.py`)

- **Nova inserção**: `scrapedAt` = agora (UTC ISO). Nunca mais alterado.
- **Atualização** (`merge`): se `timeline` ou `warningNote` mudarem, o estado anterior é arquivado em `revisions[]`. `scrapedAt` do registro original é **preservado**.
- **Retificação** (`apply_revision`): artigos classificados como `update` tentam encontrar um registro pai pelo `shortName` da fonte no título. Se encontrado, atualiza `timeline`, `warningNote`, `officialUrl` e arquiva o estado anterior em `revisions`.
- **Purga**: ao fim de cada execução, registros que o classificador atual rejeitaria (agora que `concurso_publico` existe) são removidos do banco.

---

## 7. Frontend Next.js

### `src/app/page.tsx` — Página principal

Server Component com `export const dynamic = "force-dynamic"` (re-renderiza a cada request para refletir o JSON atualizado sem rebuild).

Fluxo de dados:
```
await searchParams → query + page
loadEditalsSnapshot() → Edital[]
filter(query) → sort(updatedAt desc) → paginate(PAGE_SIZE=9)
render: SiteHeader + PageIntro + SearchBar + grid[EditalCard] + Pagination
```

### `src/components/EditalCard.tsx`

Props: `{ edital: Edital; isNew: boolean }`

Seções do card:
- **Banner** (altura 112px): gradiente `accentColor → accentColor + #0f172a`. Badges: "SAIU O EDITAL" (apenas se `isNew=true`) + nome curto + ano.
- **Título reescrito** + metadados (`source.name` · data publicação).
- **Próximo marco**: calculado por `findNextMilestone(timeline)` — próxima data futura na timeline. Exibe label, data e contagem relativa ("em 10 dias", "em 2 meses").
- **Cronograma**: `<ol>` com linhas zebradas. A linha do próximo marco recebe `bg` na cor do card (10% opacity). Se `timeline=[]`, exibe aviso com ícone de info.
- **CTA**: botão "Site oficial" (fullwidth, abre em nova aba). Se `officialUrl` for `null/""`, o botão ainda aparece com `href=""` — **limitação conhecida, ver seção 13**.

### `src/components/SearchBar.tsx` (Client Component)

- `useTransition` + `useRouter.push` — atualiza URL params sem bloquear a UI.
- Debounce: 300ms via `setTimeout`/`clearTimeout`.
- Ao digitar, reseta `page` para 1 no URL param.
- Busca por: `source.name`, `source.shortName`, `rewrittenTitle`, `originalTitle`.

### `src/components/Pagination.tsx`

Renderiza `<Link>` (Server Component-friendly). Mantém `q` no URL ao paginar. Exibe "anterior / próximo" + números. Não exibe se `totalPages = 1`.

### `src/lib/dates.ts`

| Função | Descrição |
|---|---|
| `findNextMilestone(timeline, today?)` | Retorna o próximo `TimelineEntry` com data futura e `daysUntil` |
| `isNewEdital(scrapedAt?, publishedAt?, days=2)` | `true` se `scrapedAt` (ou fallback `publishedAt`) ≤ 2 dias atrás |
| `formatRelativeDays(days)` | "hoje", "amanhã", "em N dias", "em N meses", "em mais de 1 ano" |

### `src/app/globals.css`

Tailwind v4 (CSS-first). Variáveis definidas em `:root` e `@theme inline`:

| Variável | Light | Dark |
|---|---|---|
| `--background` | `#f8fafc` | `#050912` |
| `--surface` | `#ffffff` | `#0c1322` |
| `--border` | `#e2e8f0` | `#1f2a44` |
| `--muted` | `#64748b` | `#94a3b8` |
| `--accent` | `#0ea5e9` | `#38bdf8` |

O `body` aplica dois gradientes radiais sutis (azul e teal no canto superior) para dar profundidade ao fundo.

---

## 8. Fluxo de dados completo

```
[Cron / manual]
      │
      ▼
python -m scraper --no-cache
      │
      ├── GET med.estrategia.com/portal/?s=edital
      │         (15 cards por página)
      │
      ├── Para cada card:
      │   ├── classify() → skip? continua.
      │   ├── GET {article_url}
      │   ├── parse_article() → timeline[], officialUrl, publishedAt
      │   ├── rewrite_title() → Claude Haiku ou regex
      │   ├── detect_source() / detect_exam_year()
      │   └── store.merge() → atualiza ou insere
      │
      └── store.save() → data/editals.json
                │
                ▼
          [git commit + push]  ←── GitHub Actions (futuro)
                │
                ▼
          Vercel auto-deploy
                │
                ▼
     Next.js page.tsx (SSR force-dynamic)
          │
          ├── loadEditalsSnapshot() → lê data/editals.json
          ├── filter(searchParams.q)
          ├── sort(updatedAt desc)
          ├── paginate(PAGE_SIZE=9)
          └── render EditalCard[]
```

---

## 9. Configuração e variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | Não | Habilita reescrita de título via Claude Haiku. Sem ela, usa heurística regex. |

Arquivo `.env.local` na raiz do projeto (não commitado):
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

O scraper lê via `os.environ.get("ANTHROPIC_API_KEY")`. O Next.js não precisa desta variável (o frontend não chama a API Claude diretamente).

### Cache do scraper

`scraper/.cache/` — arquivos HTML nomeados por SHA1 da URL. TTL: 30 minutos. Excluído do git via `.gitignore`.

Para limpar o cache manualmente:
```bash
rm -rf scraper/.cache/
```

---

## 10. Como rodar localmente

### Pré-requisitos

- Node.js ≥ 20
- Python ≥ 3.13
- `pip` (ou `pip3`)

### Setup inicial

```bash
# 1. Instalar dependências Node
npm install

# 2. Instalar dependências Python
pip install -r scraper/requirements.txt

# 3. (Opcional) Configurar API key para reescrita com LLM
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env.local
```

### Rodar o scraper

```bash
# Popula / atualiza data/editals.json
python -m scraper

# Forçar re-fetch (ignora cache)
python -m scraper --no-cache

# Testar com poucos cards
python -m scraper --limit 3
```

### Rodar o frontend

```bash
npm run dev
# Abre em http://localhost:3000
```

### Build de produção

```bash
npm run build
npm start
```

---

## 11. Plano de deploy (Vercel + GitHub Actions)

> **Status atual:** ainda não implementado. A seguir o plano definido.

### Vercel (frontend)

1. Conectar o repositório ao Vercel.
2. Framework: Next.js (detectado automaticamente).
3. `ANTHROPIC_API_KEY` não é necessária no ambiente Vercel (o scraper não roda lá).
4. Cada push para `master` redeploya automaticamente.

### GitHub Actions (scraper automático)

Workflow sugerido (`.github/workflows/scrape.yml`):

```yaml
name: Scrape editals
on:
  schedule:
    - cron: "0 8,20 * * *"   # 2x por dia: 08h e 20h UTC
  workflow_dispatch:           # trigger manual

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install -r scraper/requirements.txt
      - run: python -m scraper --no-cache
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore(data): scrape editals"
          file_pattern: data/editals.json
```

O commit do `editals.json` dispara o redeploy da Vercel automaticamente.

---

## 12. Decisões de design e trade-offs

### JSON em vez de banco de dados

**Decisão:** usar `data/editals.json` como única fonte de verdade.

**Razão:** o volume de dados é pequeno (dezenas de editais por vez), o acesso é somente leitura no frontend, e o arquivo pode ser commitado no repositório — eliminando a necessidade de banco externo para o deploy inicial na Vercel.

**Trade-off:** em escala (milhares de editais, múltiplos scrapers concorrentes) seria necessário migrar para SQLite ou PostgreSQL.

### SSR `force-dynamic` em vez de ISR

**Decisão:** `export const dynamic = "force-dynamic"` na página principal.

**Razão:** como o JSON pode ser atualizado a qualquer momento pelo scraper, ISR (Incremental Static Regeneration) introduziria staleness. Com `force-dynamic`, a página sempre reflete o estado atual do arquivo.

**Trade-off:** sem cache de página no CDN. Para mitigar em produção, pode-se combinar com `revalidate` quando o ciclo de atualização for mais previsível.

### Separação scraper/frontend via arquivo

O scraper não tem acesso à API do Next.js, e o frontend não executa código Python. A comunicação é feita pelo arquivo `data/editals.json`. Isso permite desenvolver e testar cada parte independentemente.

### `scrapedAt` imutável

**Decisão:** gravar `scrapedAt` apenas na primeira inserção e nunca atualizá-lo.

**Razão:** o badge "SAIU O EDITAL" deve refletir quando *nós* vimos o edital pela primeira vez (entrada no nosso sistema), não quando a Estratégia publicou o artigo. `publishedAt` pode ser dias antes do scraper ter detectado.

### Classificação por regex (sem LLM)

**Decisão:** classificar artigos com regex puro, não com LLM.

**Razão:** a classificação roda para cada card da listagem (15+/página) a cada execução. Usar LLM aqui seria lento e custoso. Regex são determinísticos, auditáveis e rápidos.

**LLM é usado apenas** para reescrever o título — uma operação por artigo novo, não repetida em re-execuções (o título já está no banco).

---

## 13. Limitações conhecidas e próximos passos

### Limitações atuais

| # | Limitação | Impacto | Solução sugerida |
|---|---|---|---|
| L1 | Botão "Site oficial" aparece mesmo quando `officialUrl` é `null/""` | UX — botão leva a lugar nenhum | Ocultar ou desabilitar o botão quando `!officialUrl` |
| L2 | Scraper não pagina a listagem (só pega os 15 cards da página 1) | Editais antigos na página 2+ não são capturados | Implementar paginação: `?s=edital&paged=2` |
| L3 | Cronograma de artigos sem tabela HTML é `[]` | Artigos como TPI-GO mostram aviso genérico | Extrair datas do corpo textual com regex |
| L4 | `accentColor` é gerado por hash do shortName | Cor pode não ter contraste adequado ou ser pouco representativa | Manter tabela manual de cores por instituição em `identify.py` |
| L5 | Sem testes automatizados | Regressões silenciosas | Adicionar pytest para `classify.py` e `extract.py` com fixtures HTML |
| L6 | Sem paginação no scraper | Editais históricos inacessíveis | Iterar `?paged=N` até não encontrar novos cards |

### Próximos passos planejados

1. **GitHub Actions cron** (ver seção 11) — automação do scraper 2× ao dia.
2. **Deploy Vercel** — conectar repositório.
3. **Ocultar botão "Site oficial"** quando URL ausente (L1).
4. **Paginação do scraper** para capturar histórico completo (L2).
5. **Ativar `ANTHROPIC_API_KEY`** para reescrita de títulos de qualidade.
6. **Notificações** — webhook/e-mail quando novo edital entrar no banco.
